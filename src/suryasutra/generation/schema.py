"""Structured answer contract (CLAUDE.md §10, D-23).

`LLMAnswerPayload` is deliberately narrow — it's what we ask the model to produce.
`alarm` (code, summary) and `status` are not part of it: we already know the alarm's
own data, so asking the model to restate it just invites it to misquote the alarm it's
supposed to be diagnosing. The model's only job is the clinical content that actually
needs grounding and citation.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CitedItem(BaseModel):
    text: str
    citations: list[str]


class Cause(BaseModel):
    cause: str
    confidence: Literal["high", "medium", "low"]
    citations: list[str]


class Step(BaseModel):
    n: int
    action: str
    expected_result: str
    citations: list[str]


class LLMAnswerPayload(BaseModel):
    safety: list[CitedItem] = Field(default_factory=list)
    likely_causes: list[Cause] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    escalate_if: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_inr: float
    budget: int
    method: str


class AnsweredContract(BaseModel):
    status: Literal["ANSWERED"] = "ANSWERED"
    alarm: dict[str, str]
    safety: list[CitedItem]
    likely_causes: list[Cause]
    steps: list[Step]
    escalate_if: list[str]
    uncertainties: list[str]
    usage: Usage


class InsufficientContract(BaseModel):
    status: Literal["INSUFFICIENT"] = "INSUFFICIENT"
    # "citation_validation_failed" is not in CLAUDE.md §10's original two-value
    # enum — added here because it's a materially different situation (evidence
    # existed and fit budget; the model just failed to cite properly) and lumping it
    # under the other two reasons would mislead whoever reads the response.
    reason: Literal["no_evidence", "over_budget", "citation_validation_failed"]
    missing_requirements: list[str]
    suggested_next: str
