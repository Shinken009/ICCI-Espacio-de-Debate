# SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
#
# SPDX-License-Identifier: MPL-2.0

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from classquiz.socket_server.activity_models import (
    ActivityPhase,
    ActivityResponse,
    ActivityRound,
    ActivityState,
    SubmitActivityResponseData,
    activity_response_field,
    activity_responses_key,
    activity_round_for_phase,
    activity_state_key,
)


def test_round_is_derived_from_phase_without_redundant_state():
    assert activity_round_for_phase(ActivityPhase.INITIAL_RESPONSE) == ActivityRound.R1
    assert activity_round_for_phase(ActivityPhase.SECOND_RESPONSE) == ActivityRound.R2
    assert activity_round_for_phase(ActivityPhase.DISCUSSION) is None
    assert activity_round_for_phase(ActivityPhase.REFLECTION) is None
    assert activity_round_for_phase(ActivityPhase.RESULTS) is None


def test_activity_state_exposes_derived_round():
    state = ActivityState(
        question_index=1,
        phase=ActivityPhase.SECOND_RESPONSE,
        phase_started_at=datetime(2026, 9, 17, 12, 0, 0),
    )
    assert state.round == ActivityRound.R2
    assert "round" not in state.model_dump()


def test_activity_state_requires_deadline_after_phase_start():
    started = datetime(2026, 9, 17, 12, 0, 0)
    with pytest.raises(ValidationError):
        ActivityState(
            question_index=0,
            phase_started_at=started,
            phase_deadline=started,
        )

    with pytest.raises(ValidationError):
        ActivityState(
            question_index=0,
            phase_started_at=started,
            phase_deadline=started - timedelta(seconds=1),
        )


def test_submission_normalizes_text_before_validation():
    payload = SubmitActivityResponseData(
        question_index=0,
        phase=ActivityPhase.INITIAL_RESPONSE,
        choice="  A  ",
        confidence=3,
        justification="  La supervisión humana reduce el riesgo.  ",
    )
    assert payload.choice == "A"
    assert payload.justification == "La supervisión humana reduce el riesgo."


@pytest.mark.parametrize(
    "phase",
    [ActivityPhase.INITIAL_RESPONSE, ActivityPhase.SECOND_RESPONSE],
)
def test_blank_response_text_is_rejected_after_normalization(phase):
    with pytest.raises(ValidationError):
        SubmitActivityResponseData(
            question_index=0,
            phase=phase,
            choice="   ",
            confidence=3,
            justification="argumento",
        )

    with pytest.raises(ValidationError):
        SubmitActivityResponseData(
            question_index=0,
            phase=phase,
            choice="A",
            confidence=3,
            justification="   ",
        )


def test_stored_response_enforces_same_phase_contract_as_submission():
    with pytest.raises(ValidationError):
        ActivityResponse(
            username="alice",
            question_index=0,
            phase=ActivityPhase.DISCUSSION,
            choice="A",
            confidence=3,
            justification="Argumento",
            submitted_at=datetime(2026, 9, 17, 12, 0, 0),
        )

    with pytest.raises(ValidationError):
        ActivityResponse(
            username="alice",
            question_index=0,
            phase=ActivityPhase.SECOND_RESPONSE,
            choice="A",
            confidence=3,
            submitted_at=datetime(2026, 9, 17, 12, 0, 0),
        )


def test_stored_response_normalizes_identity_and_text():
    response = ActivityResponse(
        username="  alice  ",
        question_index=0,
        phase=ActivityPhase.SECOND_RESPONSE,
        choice="  B ",
        confidence=4,
        justification="  Razon revisada  ",
        submitted_at=datetime(2026, 9, 17, 12, 0, 0),
    )
    assert response.username == "alice"
    assert response.choice == "B"
    assert response.justification == "Razon revisada"


def test_redis_keys_separate_state_from_responses_and_rounds_by_field():
    assert activity_state_key("123456", 2) == "activity:123456:2:state"
    assert activity_responses_key("123456", 2) == "activity:123456:2:responses"

    r1 = activity_response_field(ActivityPhase.INITIAL_RESPONSE, "alice")
    r2 = activity_response_field(ActivityPhase.SECOND_RESPONSE, "alice")
    assert r1 == "INITIAL_RESPONSE:alice"
    assert r2 == "SECOND_RESPONSE:alice"
    assert r1 != r2


@pytest.mark.parametrize("game_pin", ["", "   ", "12:34"])
def test_redis_keys_reject_invalid_game_pin(game_pin):
    with pytest.raises(ValueError):
        activity_state_key(game_pin, 0)


def test_redis_keys_reject_negative_question_index():
    with pytest.raises(ValueError):
        activity_responses_key("123456", -1)


@pytest.mark.parametrize("phase", [ActivityPhase.DISCUSSION, ActivityPhase.RESULTS])
def test_response_field_rejects_non_response_phases(phase):
    with pytest.raises(ValueError):
        activity_response_field(phase, "alice")


def test_response_field_rejects_blank_username():
    with pytest.raises(ValueError):
        activity_response_field(ActivityPhase.INITIAL_RESPONSE, "   ")
