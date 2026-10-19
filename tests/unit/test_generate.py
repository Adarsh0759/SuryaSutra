import json

from suryasutra.generation.generate import generate_triage_answer
from suryasutra.generation.llm.base import LLMAdapter, LLMResponse
from suryasutra.generation.prompts.triage_prompt import AlarmInfo
from suryasutra.generation.schema import AnsweredContract, InsufficientContract
from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import Answered
from suryasutra.usage.cost import ModelPricing, PricingTable


class FakeLLMAdapter(LLMAdapter):
    def __init__(self, texts: list[str]) -> None:
        self._texts = list(texts)
        self.call_count = 0

    def generate(
        self, system: str, user: str, temperature: float = 0.0, max_tokens: int | None = None
    ) -> LLMResponse:
        text = self._texts[self.call_count]
        self.call_count += 1
        return LLMResponse(
            text=text,
            input_tokens=100,
            output_tokens=50,
            model="fake-model",
            provider="fake",
            latency_ms=1.0,
        )


_PRICING = PricingTable(
    usd_to_inr=90.0,
    models={("fake", "fake-model"): ModelPricing(0.1, 0.5, 8192)},
)

_ALARM = AlarmInfo(code="370", message="Boost Capacitor Overvoltage Fault.")

_SELECTION = Answered(
    selected=(
        Chunk(
            text="Disconnect AC and DC switches.",
            page_start=103,
            page_end=103,
            tokens=50,
            doc_type="manual",
            covers=frozenset({"safety_x"}),
        ),
    ),
    tokens_used=50,
)

_VALID_RESPONSE = json.dumps(
    {
        "safety": [{"text": "Disconnect AC and DC switches.", "citations": ["c1"]}],
        "likely_causes": [{"cause": "Overvoltage", "confidence": "high", "citations": ["c1"]}],
        "steps": [
            {
                "n": 1,
                "action": "Disconnect switches.",
                "expected_result": "Fault clears.",
                "citations": ["c1"],
            }
        ],
        "escalate_if": ["Fault persists after restart."],
        "uncertainties": [],
    }
)

_UNCITED_RESPONSE = json.dumps(
    {
        "safety": [{"text": "Disconnect AC and DC switches.", "citations": []}],
        "likely_causes": [],
        "steps": [],
        "escalate_if": [],
        "uncertainties": [],
    }
)


def test_generate_triage_answer_succeeds_on_valid_first_response() -> None:
    llm = FakeLLMAdapter([_VALID_RESPONSE])

    result = generate_triage_answer(
        _ALARM, _SELECTION, llm, budget=500, method="requirement_complete", pricing=_PRICING
    )

    assert isinstance(result, AnsweredContract)
    assert result.status == "ANSWERED"
    assert result.alarm["code"] == "370"
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50
    assert result.usage.budget == 500
    assert llm.call_count == 1


def test_generate_triage_answer_retries_once_then_succeeds() -> None:
    llm = FakeLLMAdapter([_UNCITED_RESPONSE, _VALID_RESPONSE])

    result = generate_triage_answer(
        _ALARM, _SELECTION, llm, budget=500, method="requirement_complete", pricing=_PRICING
    )

    assert isinstance(result, AnsweredContract)
    assert llm.call_count == 2


def test_generate_triage_answer_returns_insufficient_after_exhausting_retries() -> None:
    llm = FakeLLMAdapter([_UNCITED_RESPONSE, _UNCITED_RESPONSE])

    result = generate_triage_answer(
        _ALARM, _SELECTION, llm, budget=500, method="requirement_complete", pricing=_PRICING
    )

    assert isinstance(result, InsufficientContract)
    assert result.reason == "citation_validation_failed"
    assert llm.call_count == 2


def test_generate_triage_answer_handles_malformed_json_as_validation_failure() -> None:
    llm = FakeLLMAdapter(["not json at all", _VALID_RESPONSE])

    result = generate_triage_answer(
        _ALARM, _SELECTION, llm, budget=500, method="requirement_complete", pricing=_PRICING
    )

    assert isinstance(result, AnsweredContract)
    assert llm.call_count == 2


def test_generate_triage_answer_computes_real_cost_from_pricing_table() -> None:
    llm = FakeLLMAdapter([_VALID_RESPONSE])

    result = generate_triage_answer(
        _ALARM, _SELECTION, llm, budget=500, method="requirement_complete", pricing=_PRICING
    )

    assert isinstance(result, AnsweredContract)
    expected_cost = (100 / 1_000_000 * 0.1 + 50 / 1_000_000 * 0.5) * 90.0
    assert result.usage.cost_inr == expected_cost
