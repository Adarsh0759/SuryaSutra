"""API request schemas (CLAUDE.md §10). Response bodies reuse the contract types
already defined in `generation.schema` — no separate response schema to drift from
the one actually produced by the generation pipeline."""

from typing import Literal

from pydantic import BaseModel


class TriageRequest(BaseModel):
    alarm_id: int
    method: str = "requirement_complete"
    budget: int = 1000


class FeedbackRequest(BaseModel):
    run_id: int
    user_role: str
    outcome: Literal["fixed", "not_fixed", "wrong_step", "unsafe"]
    note: str | None = None
