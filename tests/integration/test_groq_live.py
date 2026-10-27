"""Live call against the real Groq API (D-21). Skipped unless GROQ_API_KEY is set —
add it to a .env file at the repo root (see .env.example) to run this for real."""

from pathlib import Path

import pytest
from config.settings import settings

from suryasutra.generation.generate import generate_triage_answer
from suryasutra.generation.llm.groq_adapter import GroqAdapter
from suryasutra.generation.prompts.triage_prompt import AlarmInfo
from suryasutra.generation.schema import AnsweredContract, InsufficientContract
from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import Answered
from suryasutra.usage.cost import load_pricing

pytestmark = pytest.mark.skipif(
    not settings.groq_api_key, reason="GROQ_API_KEY not set in .env; live Groq test skipped"
)

PRICING_PATH = Path(__file__).parents[2] / "config" / "pricing.yaml"


def test_groq_adapter_live_call_returns_valid_cited_answer() -> None:
    llm = GroqAdapter(api_key=settings.groq_api_key, model=settings.llm_model)
    pricing = load_pricing(PRICING_PATH)

    alarm = AlarmInfo(
        code="370", message="Inverter raised fault code 370, Boost Capacitor Overvoltage Fault."
    )
    selection = Answered(
        selected=(
            Chunk(
                text=(
                    "364-395 Boost Capacitor Overvoltage Fault: 1. Disconnect the AC and DC "
                    "switches, and disconnect the battery side switches if there are "
                    "batteries. Close the AC and DC switches in turn 15 minutes later and "
                    "restart the system. 2. If the fault persists, contact Sungrow Customer "
                    "Service."
                ),
                page_start=103,
                page_end=103,
                tokens=80,
                doc_type="manual",
                covers=frozenset(
                    {"safety_dc_isolation_sequence", "corrective_measures_boost_capacitor"}
                ),
            ),
        ),
        tokens_used=80,
    )

    result = generate_triage_answer(
        alarm, selection, llm, budget=1000, method="requirement_complete", pricing=pricing
    )

    assert isinstance(result, AnsweredContract | InsufficientContract)
    if isinstance(result, AnsweredContract):
        assert result.usage.input_tokens > 0
        assert result.usage.output_tokens > 0
        assert result.usage.cost_inr > 0
        for item in result.safety:
            assert item.citations
        for step in result.steps:
            assert step.citations
        print(
            "LIVE GROQ ANSWER:",
            result.model_dump_json(indent=2).encode("ascii", "backslashreplace").decode("ascii"),
        )
    else:
        print("LIVE GROQ RETURNED INSUFFICIENT:", result)
