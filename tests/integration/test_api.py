"""API-level tests (M4). Needs the real manual on disk (startup builds the real
corpus + dense index) — skipped if it hasn't been downloaded. The LLM is monkeypatched
to a scripted fake so these don't cost real API calls; the live Groq call itself is
already covered by tests/integration/test_groq_live.py.
"""

import json

import pytest
from fastapi.testclient import TestClient

from suryasutra.api.main import app
from suryasutra.api.state import MANUAL_PATH, AppState
from suryasutra.generation.llm.base import LLMAdapter, LLMResponse

pytestmark = pytest.mark.skipif(
    not MANUAL_PATH.exists(),
    reason="real manual not downloaded locally; run `bash scripts/download_docs.sh` first",
)


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
            input_tokens=50,
            output_tokens=30,
            model="fake",
            provider="fake",
            latency_ms=1.0,
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


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _fake_pricing_entry(state: AppState) -> None:
    """Point pricing at the fake model so /triage's cost computation doesn't KeyError."""
    from suryasutra.usage.cost import ModelPricing

    state.pricing.models[("fake", "fake")] = ModelPricing(0.1, 0.5, 8192)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_alarms_returns_ten_synthetic_alarms(client: TestClient) -> None:
    response = client.get("/alarms")

    assert response.status_code == 200
    alarms = response.json()
    assert len(alarms) == 10
    assert all(a["is_synthetic"] for a in alarms)


def test_triage_unknown_alarm_returns_404(client: TestClient) -> None:
    response = client.post("/triage", json={"alarm_id": 9999})

    assert response.status_code == 404


def test_triage_unknown_method_returns_400(client: TestClient) -> None:
    response = client.post("/triage", json={"alarm_id": 1, "method": "not_a_real_method"})

    assert response.status_code == 400


def test_triage_returns_insufficient_when_budget_too_small(client: TestClient) -> None:
    response = client.post(
        "/triage", json={"alarm_id": 1, "method": "requirement_complete", "budget": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INSUFFICIENT"


def test_triage_returns_answered_with_citations(client: TestClient) -> None:
    state: AppState = client.app.state.suryasutra
    original_llm = state.llm
    state.llm = FakeLLMAdapter([_VALID_RESPONSE])
    _fake_pricing_entry(state)
    try:
        response = client.post(
            "/triage", json={"alarm_id": 1, "method": "requirement_complete", "budget": 1000}
        )
    finally:
        state.llm = original_llm

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ANSWERED"
    assert body["safety"][0]["citations"] == ["c1"]
    assert body["usage"]["input_tokens"] == 50
