# SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
#
# SPDX-License-Identifier: MPL-2.0

"""Socket.IO handlers for ICCI deliberative classroom activities.

This module deliberately reuses ClassQuiz authentication/session identity,
Socket.IO rooms and Redis. It does not replace the normal ``submit_answer``
flow and therefore keeps standard ClassQuiz games isolated from the pilot.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from pydantic import ValidationError
from socketio import AsyncServer

from classquiz.config import redis
from classquiz.db.models import PlayGame, QuizQuestionType, VotingQuizAnswer
from classquiz.socket_server.activity_models import (
    ActivityPhase,
    ActivityResponse,
    ActivityState,
    GetActivityResultsData,
    GetActivityStateData,
    InteractionMode,
    RESPONSE_PHASES,
    SetActivityPhaseData,
    StartDeliberationQuestionData,
    SubmitActivityResponseData,
)
from classquiz.socket_server.models import ReturnQuestion
from classquiz.socket_server.session import get_session

ACTIVITY_TTL_SECONDS = 7200

_PHASE_ORDER = {
    ActivityPhase.INITIAL_RESPONSE: ActivityPhase.DISCUSSION,
    ActivityPhase.DISCUSSION: ActivityPhase.SECOND_RESPONSE,
    ActivityPhase.SECOND_RESPONSE: ActivityPhase.REFLECTION,
    ActivityPhase.REFLECTION: ActivityPhase.RESULTS,
}


def _state_key(game_pin: str, question_index: int) -> str:
    return f"activity:{game_pin}:{question_index}:state"


def _responses_key(game_pin: str, question_index: int) -> str:
    return f"activity:{game_pin}:{question_index}:responses"


def _response_field(phase: ActivityPhase, username: str) -> str:
    return f"{phase.value}:{username}"


async def _load_state(game_pin: str, question_index: int) -> ActivityState | None:
    data = await redis.get(_state_key(game_pin, question_index))
    if data is None:
        return None
    return ActivityState.model_validate_json(data)


async def _save_state(game_pin: str, state: ActivityState) -> None:
    await redis.set(
        _state_key(game_pin, state.question_index),
        state.model_dump_json(),
        ex=ACTIVITY_TTL_SECONDS,
    )


async def _validate_voting_question(
    game_pin: str,
    question_index: int,
    *,
    require_active: bool = True,
) -> PlayGame:
    game_data = await PlayGame.get_from_redis(game_pin)
    if question_index >= len(game_data.questions):
        raise ValueError("question_not_found")
    if require_active and game_data.current_question != question_index:
        raise ValueError("question_not_active")
    if game_data.questions[question_index].type != QuizQuestionType.VOTING:
        raise ValueError("activity_requires_voting_question")
    return game_data


def _public_deliberation_question(game_data: PlayGame, question_index: int) -> dict:
    temp_return = game_data.model_dump(include={"questions"})["questions"][question_index]
    for i in range(len(temp_return["answers"])):
        temp_return["answers"][i] = VotingQuizAnswer(**temp_return["answers"][i])
    temp_return["type"] = game_data.questions[question_index].type
    question = ReturnQuestion(**temp_return).model_dump()
    question["interaction_mode"] = InteractionMode.PEER_DELIBERATION.value
    return question


def _group_responses(
    responses: Iterable[ActivityResponse],
) -> dict[ActivityPhase, dict[str, ActivityResponse]]:
    grouped: dict[ActivityPhase, dict[str, ActivityResponse]] = {}
    for response in responses:
        grouped.setdefault(response.phase, {})[response.username] = response
    return grouped


def build_activity_results(responses: Iterable[ActivityResponse]) -> dict:
    """Build anonymous, descriptive and non-evaluative R1/R2 analytics."""

    grouped = _group_responses(responses)
    initial = grouped.get(ActivityPhase.INITIAL_RESPONSE, {})
    second = grouped.get(ActivityPhase.SECOND_RESPONSE, {})
    reflections = grouped.get(ActivityPhase.REFLECTION, {})

    initial_counts: dict[str, int] = {}
    second_counts: dict[str, int] = {}
    confidence_change = {"increased": 0, "decreased": 0, "unchanged": 0}
    maintained = 0
    changed = 0

    for response in initial.values():
        if response.choice is not None:
            initial_counts[response.choice] = initial_counts.get(response.choice, 0) + 1

    for response in second.values():
        if response.choice is not None:
            second_counts[response.choice] = second_counts.get(response.choice, 0) + 1

    choices = sorted(set(initial_counts).union(second_counts))
    transitions: dict[str, dict[str, int]] = {
        before: {after: 0 for after in choices} for before in choices
    }

    shared_participants = sorted(set(initial).intersection(second))
    for username in shared_participants:
        before = initial[username]
        after = second[username]
        if before.choice is None or after.choice is None:
            continue

        transitions.setdefault(
            before.choice,
            {choice: 0 for choice in choices},
        )
        transitions[before.choice].setdefault(after.choice, 0)
        transitions[before.choice][after.choice] += 1

        if before.choice == after.choice:
            maintained += 1
        else:
            changed += 1

        if before.confidence is not None and after.confidence is not None:
            if after.confidence > before.confidence:
                confidence_change["increased"] += 1
            elif after.confidence < before.confidence:
                confidence_change["decreased"] += 1
            else:
                confidence_change["unchanged"] += 1

    return {
        "initial_counts": initial_counts,
        "second_counts": second_counts,
        "transitions": transitions,
        "stance": {"maintained": maintained, "changed": changed},
        "confidence_change": confidence_change,
        "matched_participants": len(shared_participants),
        "reflection_count": len(reflections),
    }


async def _read_responses(game_pin: str, question_index: int) -> list[ActivityResponse]:
    raw = await redis.hgetall(_responses_key(game_pin, question_index))
    responses: list[ActivityResponse] = []
    for value in raw.values():
        responses.append(ActivityResponse.model_validate_json(value))
    return responses


def _phase_response_count(
    responses: Iterable[ActivityResponse],
    phase: ActivityPhase,
) -> int:
    if phase not in RESPONSE_PHASES:
        return 0
    return sum(1 for response in responses if response.phase == phase)


def _own_response_snapshot(
    responses: Iterable[ActivityResponse],
    username: str | None,
) -> dict[str, dict]:
    if not username:
        return {}

    snapshot: dict[str, dict] = {}
    for response in responses:
        if response.username != username:
            continue
        snapshot[response.phase.value] = {
            "choice": response.choice,
            "confidence": response.confidence,
            "justification": response.justification,
            "reflection": response.reflection,
        }
    return snapshot


async def _player_count(game_pin: str) -> int:
    return await redis.scard(f"game_session:{game_pin}:players")


def _is_n3_mode(player_count: int) -> bool:
    """Use the microgroup facilitation mode when one to three students are present."""

    return 1 <= player_count <= 3


async def _emit_progress(
    sio: AsyncServer,
    game_pin: str,
    state: ActivityState,
    responses: Iterable[ActivityResponse],
) -> None:
    player_count = await _player_count(game_pin)
    await sio.emit(
        "activity_progress",
        {
            "question_index": state.question_index,
            "phase": state.phase.value,
            "response_count": _phase_response_count(responses, state.phase),
            "player_count": player_count,
            "n3_mode": _is_n3_mode(player_count),
        },
        room=f"admin:{game_pin}",
    )


async def _emit_error(sio: AsyncServer, sid: str, code: str) -> None:
    await sio.emit("activity_error", {"code": code}, room=sid)


def register_activity_handlers(sio: AsyncServer) -> None:
    """Register ICCI activity events on the existing ClassQuiz Socket.IO server."""

    @sio.event
    async def start_deliberation_question(sid: str, data: dict):
        try:
            payload = StartDeliberationQuestionData(**data)
        except ValidationError:
            await _emit_error(sio, sid, "invalid_payload")
            return

        session = await get_session(sid, sio)
        if not session.get("admin"):
            await _emit_error(sio, sid, "admin_required")
            return

        game_pin = session["game_pin"]
        try:
            game_data = await _validate_voting_question(
                game_pin,
                payload.question_index,
                require_active=False,
            )
        except ValueError as exc:
            await _emit_error(sio, sid, str(exc))
            return

        if not game_data.started:
            await _emit_error(sio, sid, "game_not_started")
            return

        await redis.delete(_state_key(game_pin, payload.question_index))
        await redis.delete(_responses_key(game_pin, payload.question_index))
        await redis.delete(f"game_session:{game_pin}:{payload.question_index}")

        game_data.current_question = payload.question_index
        game_data.question_show = True
        await game_data.save(game_pin)
        await redis.set(
            f"game:{game_pin}:current_time",
            datetime.now().isoformat(),
            ex=ACTIVITY_TTL_SECONDS,
        )

        now = datetime.now()
        state = ActivityState(
            question_index=payload.question_index,
            phase=ActivityPhase.INITIAL_RESPONSE,
            phase_started_at=now,
        )
        await _save_state(game_pin, state)

        await sio.emit(
            "set_question_number",
            {
                "question_index": payload.question_index,
                "question": _public_deliberation_question(game_data, payload.question_index),
            },
            room=game_pin,
        )
        await sio.emit(
            "activity_phase_changed",
            state.model_dump(mode="json"),
            room=game_pin,
        )
        await _emit_progress(sio, game_pin, state, [])

    @sio.event
    async def set_activity_phase(sid: str, data: dict):
        try:
            payload = SetActivityPhaseData(**data)
        except ValidationError:
            await _emit_error(sio, sid, "invalid_payload")
            return

        session = await get_session(sid, sio)
        if not session.get("admin"):
            await _emit_error(sio, sid, "admin_required")
            return

        game_pin = session["game_pin"]
        try:
            await _validate_voting_question(game_pin, payload.question_index)
        except ValueError as exc:
            await _emit_error(sio, sid, str(exc))
            return

        current = await _load_state(game_pin, payload.question_index)
        if current is None:
            if payload.phase != ActivityPhase.INITIAL_RESPONSE:
                await _emit_error(sio, sid, "activity_must_start_with_initial_response")
                return
        else:
            expected = _PHASE_ORDER.get(current.phase)
            if expected != payload.phase:
                await _emit_error(sio, sid, "invalid_phase_transition")
                return

        now = datetime.now()
        deadline = None
        if payload.duration_seconds is not None:
            deadline = now + timedelta(seconds=payload.duration_seconds)

        state = ActivityState(
            question_index=payload.question_index,
            phase=payload.phase,
            phase_started_at=now,
            phase_deadline=deadline,
        )
        await _save_state(game_pin, state)
        await sio.emit(
            "activity_phase_changed",
            state.model_dump(mode="json"),
            room=game_pin,
        )
        responses = await _read_responses(game_pin, payload.question_index)
        await _emit_progress(sio, game_pin, state, responses)

    @sio.event
    async def submit_activity_response(sid: str, data: dict):
        try:
            payload = SubmitActivityResponseData(**data)
        except ValidationError:
            await _emit_error(sio, sid, "invalid_payload")
            return

        session = await get_session(sid, sio)
        if session.get("admin"):
            await _emit_error(sio, sid, "participant_required")
            return

        game_pin = session["game_pin"]
        username = session["username"]
        try:
            await _validate_voting_question(game_pin, payload.question_index)
        except ValueError as exc:
            await _emit_error(sio, sid, str(exc))
            return

        state = await _load_state(game_pin, payload.question_index)
        if state is None:
            await _emit_error(sio, sid, "activity_not_started")
            return
        if state.phase != payload.phase:
            await _emit_error(sio, sid, "phase_not_active")
            return
        if state.phase_deadline is not None and datetime.now() > state.phase_deadline:
            await _emit_error(sio, sid, "phase_closed")
            return

        responses_key = _responses_key(game_pin, payload.question_index)
        field = _response_field(payload.phase, username)
        if await redis.hexists(responses_key, field):
            await _emit_error(sio, sid, "already_submitted_for_phase")
            return

        response = ActivityResponse(
            username=username,
            question_index=payload.question_index,
            phase=payload.phase,
            choice=payload.choice,
            confidence=payload.confidence,
            justification=payload.justification,
            reflection=payload.reflection,
            submitted_at=datetime.now(),
        )
        await redis.hset(responses_key, field, response.model_dump_json())
        await redis.expire(responses_key, ACTIVITY_TTL_SECONDS)

        await sio.emit(
            "activity_response_saved",
            {"question_index": payload.question_index, "phase": payload.phase.value},
            room=sid,
        )

        all_responses = await _read_responses(game_pin, payload.question_index)
        await _emit_progress(sio, game_pin, state, all_responses)

    @sio.event
    async def get_activity_state(sid: str, data: dict):
        try:
            payload = GetActivityStateData(**data)
        except ValidationError:
            await _emit_error(sio, sid, "invalid_payload")
            return

        session = await get_session(sid, sio)
        game_pin = session["game_pin"]
        state = await _load_state(game_pin, payload.question_index)
        responses = await _read_responses(game_pin, payload.question_index)
        player_count = await _player_count(game_pin)

        submitted_phases: list[str] = []
        own_responses: dict[str, dict] = {}
        if not session.get("admin") and state is not None:
            username = session.get("username")
            submitted_phases = [
                response.phase.value
                for response in responses
                if response.username == username
            ]
            own_responses = _own_response_snapshot(responses, username)

        await sio.emit(
            "activity_state",
            {
                "state": state.model_dump(mode="json") if state else None,
                "submitted_phases": submitted_phases,
                "my_responses": own_responses,
                "response_count": (
                    _phase_response_count(responses, state.phase) if state is not None else 0
                ),
                "player_count": player_count,
                "n3_mode": _is_n3_mode(player_count),
            },
            room=sid,
        )

    @sio.event
    async def get_activity_results(sid: str, data: dict):
        try:
            payload = GetActivityResultsData(**data)
        except ValidationError:
            await _emit_error(sio, sid, "invalid_payload")
            return

        session = await get_session(sid, sio)
        if not session.get("admin"):
            await _emit_error(sio, sid, "admin_required")
            return

        game_pin = session["game_pin"]
        try:
            await _validate_voting_question(game_pin, payload.question_index)
        except ValueError as exc:
            await _emit_error(sio, sid, str(exc))
            return

        responses = await _read_responses(game_pin, payload.question_index)
        player_count = await _player_count(game_pin)
        await sio.emit(
            "activity_results",
            {
                "question_index": payload.question_index,
                "player_count": player_count,
                "n3_mode": _is_n3_mode(player_count),
                **build_activity_results(responses),
            },
            room=sid,
        )
