# SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
#
# SPDX-License-Identifier: MPL-2.0

"""Pydantic models for ICCI deliberative classroom activities.

The activity layer is intentionally separate from ``QuizQuestionType``. A
question describes the content/answer shape (for example ``VOTING``), while an
activity describes how participants interact with that question over time.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


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


RESPONSE_PHASES = {
    ActivityPhase.INITIAL_RESPONSE,
    ActivityPhase.SECOND_RESPONSE,
    ActivityPhase.REFLECTION,
}


class ActivityState(BaseModel):
    """Ephemeral state for one question inside an active game session."""

    question_index: int = Field(ge=0)
    interaction_mode: InteractionMode = InteractionMode.PEER_DELIBERATION
    phase: ActivityPhase = ActivityPhase.INITIAL_RESPONSE
    phase_started_at: datetime
    phase_deadline: datetime | None = None


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

    @model_validator(mode="after")
    def validate_phase_payload(self) -> "SubmitActivityResponseData":
        if self.phase in {
            ActivityPhase.INITIAL_RESPONSE,
            ActivityPhase.SECOND_RESPONSE,
        }:
            if not self.choice or not self.choice.strip():
                raise ValueError("choice is required for response phases")
            if self.confidence is None:
                raise ValueError("confidence is required for response phases")

        if self.phase == ActivityPhase.INITIAL_RESPONSE:
            if not self.justification or not self.justification.strip():
                raise ValueError("justification is required for the initial response")

        if self.phase == ActivityPhase.REFLECTION:
            if not self.reflection or not self.reflection.strip():
                raise ValueError("reflection is required for the reflection phase")

        if self.phase not in RESPONSE_PHASES:
            raise ValueError("responses are not accepted during this phase")

        return self


class ActivityResponse(BaseModel):
    """Stored response associated with a participant and a specific phase."""

    username: str = Field(min_length=1, max_length=100)
    question_index: int = Field(ge=0)
    phase: ActivityPhase
    choice: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    justification: str | None = None
    reflection: str | None = None
    submitted_at: datetime


class GetActivityStateData(BaseModel):
    question_index: int = Field(ge=0)


class GetActivityResultsData(BaseModel):
    question_index: int = Field(ge=0)
