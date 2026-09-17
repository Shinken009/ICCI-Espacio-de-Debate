# SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
#
# SPDX-License-Identifier: MPL-2.0

from datetime import datetime

import pytest
from pydantic import ValidationError

from classquiz.socket_server.activity import build_activity_results
from classquiz.socket_server.activity_models import (
    ActivityPhase,
    ActivityResponse,
    SubmitActivityResponseData,
)


def _response(
    username: str,
    phase: ActivityPhase,
    choice: str | None = None,
    confidence: int | None = None,
    justification: str | None = None,
    reflection: str | None = None,
) -> ActivityResponse:
    return ActivityResponse(
        username=username,
        question_index=0,
        phase=phase,
        choice=choice,
        confidence=confidence,
        justification=justification,
        reflection=reflection,
        submitted_at=datetime(2026, 9, 17, 12, 0, 0),
    )


def test_initial_response_requires_choice_confidence_and_justification():
    with pytest.raises(ValidationError):
        SubmitActivityResponseData(
            question_index=0,
            phase=ActivityPhase.INITIAL_RESPONSE,
            choice="A",
            confidence=3,
        )


def test_second_response_requires_choice_confidence_and_justification():
    with pytest.raises(ValidationError):
        SubmitActivityResponseData(
            question_index=0,
            phase=ActivityPhase.SECOND_RESPONSE,
            choice="B",
            confidence=4,
        )

    data = SubmitActivityResponseData(
        question_index=0,
        phase=ActivityPhase.SECOND_RESPONSE,
        choice="B",
        confidence=4,
        justification="Mantengo esta alternativa por la evidencia discutida.",
    )
    assert data.choice == "B"
    assert data.confidence == 4
    assert data.justification == "Mantengo esta alternativa por la evidencia discutida."


def test_reflection_requires_reflection_text():
    with pytest.raises(ValidationError):
        SubmitActivityResponseData(
            question_index=0,
            phase=ActivityPhase.REFLECTION,
        )


def test_non_response_phases_reject_participant_submission():
    with pytest.raises(ValidationError):
        SubmitActivityResponseData(
            question_index=0,
            phase=ActivityPhase.DISCUSSION,
            choice="A",
            confidence=3,
            justification="Argumento",
        )


def test_activity_results_are_descriptive_neutral_and_anonymous():
    responses = [
        _response("alice", ActivityPhase.INITIAL_RESPONSE, "A", 3, "Argument A"),
        _response("bob", ActivityPhase.INITIAL_RESPONSE, "A", 3, "Otro argumento"),
        _response("carol", ActivityPhase.INITIAL_RESPONSE, "B", 5, "Argument B"),
        _response("alice", ActivityPhase.SECOND_RESPONSE, "A", 4, "Razon R2 A"),
        _response("bob", ActivityPhase.SECOND_RESPONSE, "B", 4, "Razon R2 B"),
        _response("carol", ActivityPhase.SECOND_RESPONSE, "A", 4, "Razon R2 A"),
        _response(
            "alice",
            ActivityPhase.REFLECTION,
            reflection="Escuche una objecion util",
        ),
    ]

    results = build_activity_results(responses)

    assert results["initial_counts"] == {"A": 2, "B": 1}
    assert results["second_counts"] == {"A": 2, "B": 1}
    assert results["transitions"] == {
        "A": {"A": 1, "B": 1},
        "B": {"A": 1, "B": 0},
    }
    assert results["stance"] == {"maintained": 1, "changed": 2}
    assert results["confidence_change"] == {
        "increased": 2,
        "decreased": 1,
        "unchanged": 0,
    }
    assert results["matched_participants"] == 3
    assert results["reflection_count"] == 1
    assert "justifications" not in results
    assert "reflections" not in results
    assert "alice" not in str(results)
    assert "bob" not in str(results)
    assert "carol" not in str(results)
    assert "success" not in results
    assert "correct" not in results


def test_unmatched_participant_is_not_counted_as_changed_or_maintained():
    responses = [
        _response("alice", ActivityPhase.INITIAL_RESPONSE, "A", 3, "Argument"),
        _response("bob", ActivityPhase.INITIAL_RESPONSE, "B", 4, "Argument"),
        _response("alice", ActivityPhase.SECOND_RESPONSE, "B", 4, "Razon R2"),
    ]

    results = build_activity_results(responses)

    assert results["matched_participants"] == 1
    assert results["stance"] == {"maintained": 0, "changed": 1}
    assert results["transitions"] == {
        "A": {"A": 0, "B": 1},
        "B": {"A": 0, "B": 0},
    }
