"""Orchestrates generation: prompt -> LLM -> parse -> validate citations -> retry once
-> else INSUFFICIENT (CLAUDE.md §10, D-23)."""

import json

from pydantic import ValidationError

from suryasutra.generation.llm.base import LLMAdapter
from suryasutra.generation.prompts.triage_prompt import AlarmInfo, build_prompt
from suryasutra.generation.schema import (
    AnsweredContract,
    InsufficientContract,
    LLMAnswerPayload,
    Usage,
)
from suryasutra.generation.validate import CitationError, validate_citations
from suryasutra.selection.base import Answered
from suryasutra.usage.cost import PricingTable, compute_cost_inr


def generate_triage_answer(
    alarm: AlarmInfo,
    selection: Answered,
    llm: LLMAdapter,
    budget: int,
    method: str,
    pricing: PricingTable,
    max_retries: int = 1,
) -> AnsweredContract | InsufficientContract:
    system, user, citation_map = build_prompt(alarm, selection.selected)
    valid_ids = set(citation_map.keys())

    for _attempt in range(max_retries + 1):
        response = llm.generate(system=system, user=user, temperature=0.0)
        try:
            payload = LLMAnswerPayload.model_validate(json.loads(response.text))
            validate_citations(payload, valid_ids)
        except (json.JSONDecodeError, ValidationError, CitationError):
            continue

        cost_inr = compute_cost_inr(
            pricing,
            response.provider,
            response.model,
            response.input_tokens,
            response.output_tokens,
        )
        usage = Usage(
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_inr=cost_inr,
            budget=budget,
            method=method,
        )
        return AnsweredContract(
            alarm={"code": alarm.code, "summary": alarm.message},
            safety=payload.safety,
            likely_causes=payload.likely_causes,
            steps=payload.steps,
            escalate_if=payload.escalate_if,
            uncertainties=payload.uncertainties,
            usage=usage,
        )

    return InsufficientContract(
        reason="citation_validation_failed",
        missing_requirements=[],
        suggested_next=(
            "The model's answer could not be validated against the selected evidence "
            "after retrying; escalate to a senior technician or try again."
        ),
    )
