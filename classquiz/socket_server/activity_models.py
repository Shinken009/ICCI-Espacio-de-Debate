# SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
#
# SPDX-License-Identifier: MPL-2.0

"""Pydantic contracts for ICCI deliberative classroom activities.

The activity layer is intentionally separate from ``QuizQuestionType``. A
question describes the content/answer shape (for example ``VOTING``), while an
activity describes how participants interact with that question over time.

This module is deliberately transport-agnostic: it defines state, payloads,
round semantics and the Redis key contract, but it does not register Socket.IO
handlers.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


ACTIVITY_TTL_SECONDS = 7200
ACTIVITY_KEY_PREFIX = "activity"


class InteractionMode(str, Enum):
    """Interaction modes understood by the ICCI activity layer."""

    PEER_DELIBERATION = "PEER_DELIBERATION"


class ActivityPhase(str, Enum):
    """Server-authoritative phases for the first deliberation workflow."""

    INITIAL_RESPONSE = "INITIAL_RESPONSE"
    DISCUSSION = "DISCUSSION"
    SECOND_RESPONSE = "SECOND_RESPONSE"
    REFLECTION = "REFLECTION"
    RESULTS = "RESULTS"


class ActivityRound(int, Enum):
    """Response rounds used to compare a participant's position over time."""

    R1 = 1
    R2 = 2


RESPONSE_PHASES = frozenset(
    {
        ActivityPhase.INITIAL_RESPONSE,
        ActivityPhase.SECOND_RESPONSE,
        ActivityPhase.REFLECTION,
    }
)

ROUND_BY_PHASE = {
    ActivityPhase.INITIAL_RESPONSE: ActivityRound.R1,
    ActivityPhase.SECOND_RESPONSE: ActivityRound.R2,
}


def activity_round_for_phase(phase: ActivityPhase) -> ActivityRound | None:
    """Return the deliberation round represented by a phase, if any."""

    return ROUND_BY_PHASE.get(phase)


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _validate_response_payload(
    *,
    phase: ActivityPhase,
    choice: str | None,
    confidence: int | None,
    justification: str | None,
    reflection: str | None,
) -> None:
    if phase in {
        ActivityPhase.INITIAL_RESPONSE,
        ActivityPhase.SECOND_RESPONSE,
    }:
        if choice is None:
            raise ValueError("choice is required for response phases")
        if confidence is None:
            raise ValueError("confidence is required for response phases")

    if phase == ActivityPhase.INITIAL_RESPONSE and justification is None:
        raise ValueError("justification is required for the initial response")

    if phase == ActivityPhase.REFLECTION and reflection is None:
        raise ValueError("reflection is required for the reflection phase")

    if phase not in RESPONSE_PHASES:
        raise ValueError("responses are not accepted during this phase")


class ActivityState(BaseModel):
    """Ephemeral state for one question inside an active game session."""

    question_index: int = Field(ge=0)
    interaction_mode: InteractionMode = InteractionMode.PEER_DELIBERATION
    phase: ActivityPhase = ActivityPhase.INITIAL_RESPONSE
    phase_started_at: datetime
    phase_deadline: datetime | None = None

    @model_validator(mode="after")
    def validate_deadline(self) -> "ActivityState":
        if self.phase_deadline is not None and self.phase_deadline <= self.phase_started_at:
            raise ValueError("phase_deadline must be later than phase_started_at")
        return self

    @property
    def round(self) -> ActivityRound | None:
        """Derive the round from the phase instead of storing redundant state."""

        return activity_round_for_phase(self.phase)


class StartDeliberationQuestionData(BaseModel):
    """Admin request to atomically show a VOTING question and open round one."""

    question_index: int = Field(ge=0)


class SetActivityPhaseData(BaseModel):
    """Admin request to move an activity to a new phase."""

    question_index: int = Field(ge=0)
    phase: ActivityPhase
    duration_seconds: int | None = Field(default=None, ge=1, le=3600)


class SubmitActivityResponseData(BaseModel):
    """Participant submission for a response-bearing activity phase."""

    question_index: int = Field(ge=0)
    phase: ActivityPhase
    choice: str | None = Field(default=None, max_length=500)
    confidence: int | None = Field(default=None, ge=1, le=5)
    justification: str | None = Field(default=None, max_length=1000)
    reflection: str | None = Field(default=None, max_length=1000)

    @field_validator("choice", "justification", "reflection", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @model_validator(mode="after")
    def validate_phase_payload(self) -> "SubmitActivityResponseData":
        _validate_response_payload(
            phase=self.phase,
            choice=self.choice,
            confidence=self.confidence,
            justification=self.justification,
            reflection=self.reflection,
        )
        return self


class ActivityResponse(BaseModel):
    """Stored response associated with a participant and a specific phase."""

    username: str = Field(min_length=1, max_length=100)
    question_index: int = Field(ge=0)
    phase: ActivityPhase
    choice: str | None = Field(default=None, max_length=500)
    confidence: int | None = Field(default=None, ge=1, le=5)
    justification: str | None = Field(default=None, max_length=1000)
    reflection: str | None = Field(default=None, max_length=1000)
    submitted_at: datetime

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()

    @field_validator("choice", "justification", "reflection", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @model_validator(mode="after")
    def validate_phase_payload(self) -> "ActivityResponse":
        _validate_response_payload(
            phase=self.phase,
            choice=self.choice,
            confidence=self.confidence,
            justification=self.justification,
            reflection=self.reflection,
        )
        return self


class GetActivityStateData(BaseModel):
    question_index: int = Field(ge=0)


class GetActivityResultsData(BaseModel):
    question_index: int = Field(ge=0)


def _validated_game_pin(game_pin: str) -> str:
    normalized = game_pin.strip()
    if not normalized:
        raise ValueError("game_pin cannot be blank")
    if ":" in normalized:
        raise ValueError("game_pin cannot contain ':'")
    return normalized


def _validated_question_index(question_index: int) -> int:
    if question_index < 0:
        raise ValueError("question_index must be non-negative")
    return question_index


def activity_state_key(game_pin: str, question_index: int) -> str:
    """Redis key containing the authoritative state for one activity question."""

    pin = _validated_game_pin(game_pin)
    index = _validated_question_index(question_index)
    return f"{ACTIVITY_KEY_PREFIX}:{pin}:{index}:state"


def activity_responses_key(game_pin: str, question_index: int) -> str:
    """Redis hash key containing participant responses for one activity question."""

    pin = _validated_game_pin(game_pin)
    index = _validated_question_index(question_index)
    return f"{ACTIVITY_KEY_PREFIX}:{pin}:{index}:responses"


def activity_response_field(phase: ActivityPhase, username: str) -> str:
    """Redis hash field guaranteeing one response per participant and phase."""

    if phase not in RESPONSE_PHASES:
        raise ValueError("phase does not accept participant responses")
    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("username cannot be blank")
    return f"{phase.value}:{normalized_username}"
