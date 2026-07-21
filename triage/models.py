"""The structured triage schema Claude is constrained to return.

Using a Pydantic model with the Messages API structured-output feature guarantees
the response is valid, parseable JSON that matches this shape every time.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class TriageResult(BaseModel):
    """A single incident triage."""

    summary: str = Field(
        description="One-sentence summary of the most likely problem."
    )
    root_cause: str = Field(
        description="The probable root cause, explained in one to three sentences."
    )
    confidence: Confidence = Field(
        description="How well the evidence matches a known failure mode."
    )
    severity: Severity = Field(
        description="Impact-based severity of the incident."
    )
    remediation_steps: list[str] = Field(
        description="Ordered, concrete steps to remediate, first to last."
    )
    commands: list[str] = Field(
        description=(
            "Shell / kubectl / SQL commands to run, in order. "
            "Empty list if no command applies."
        )
    )
    relevant_runbooks: list[str] = Field(
        description="Titles of the runbooks that informed this triage."
    )
    escalation: str = Field(
        description="When and to whom to escalate if the steps do not resolve it."
    )
