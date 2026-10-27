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


def test_list_alarms_returns_synthetic_alarms(client: TestClient) -> None:
    response = client.get("/alarms")

    assert response.status_code == 200
    alarms = response.json()
    assert len(alarms) == 32  # 24 answerable + 8 deliberately-unanswerable (D-14, D-40)
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
    assert "c1" in body["sources"]
    assert "page_start" in body["sources"]["c1"]


def test_triage_persists_a_run_retrievable_via_get_runs(client: TestClient) -> None:
    state: AppState = client.app.state.suryasutra
    original_llm = state.llm
    state.llm = FakeLLMAdapter([_VALID_RESPONSE])
    _fake_pricing_entry(state)
    try:
        triage_response = client.post(
            "/triage", json={"alarm_id": 1, "method": "requirement_complete", "budget": 1000}
        )
    finally:
        state.llm = original_llm

    assert triage_response.status_code == 200

    # Not knowing the exact run id (other tests also write rows against the same
    # test DB), query the DB directly for the one this call just created.
    from suryasutra.db.models import TriageRun
    from suryasutra.db.session import get_session

    with get_session() as session:
        run = (
            session.query(TriageRun)
            .filter_by(alarm_id=1, method="requirement_complete", budget=1000)
            .order_by(TriageRun.id.desc())
            .first()
        )
        assert run is not None
        run_id = run.id

    run_response = client.get(f"/runs/{run_id}")

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "ANSWERED"
    assert body["method"] == "requirement_complete"
    assert "c1" in body["selected_chunk_ids"]  # real selector may pick more than one
    assert body["usage"]["input_tokens"] == 50
    assert body["answer"]["safety"][0]["citations"] == ["c1"]


def test_get_run_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get("/runs/999999")

    assert response.status_code == 404


def test_persisted_run_flags_mandatory_coverage_gap_even_when_status_is_answered(
    client: TestClient,
) -> None:
    """Regression for a real gap: an ANSWERED result can still have silently dropped
    a mandatory requirement (H1's exact failure mode) — this must be visible in what
    gets persisted, not just in the selector-level INSUFFICIENT case. Alarm 2 with
    topk at budget 500 is a known real case of this (measured in the M5 eval run,
    eval/results/*_topk_500.json), not a contrived fixture."""
    state: AppState = client.app.state.suryasutra
    original_llm = state.llm
    state.llm = FakeLLMAdapter([_VALID_RESPONSE])
    _fake_pricing_entry(state)
    try:
        triage_response = client.post(
            "/triage", json={"alarm_id": 2, "method": "topk", "budget": 500}
        )
    finally:
        state.llm = original_llm

    assert triage_response.status_code == 200
    assert triage_response.json()["status"] == "ANSWERED"

    from suryasutra.db.models import TriageRun
    from suryasutra.db.session import get_session

    with get_session() as session:
        run = (
            session.query(TriageRun)
            .filter_by(alarm_id=2, method="topk", budget=500)
            .order_by(TriageRun.id.desc())
            .first()
        )
        assert run is not None
        assert run.status == "ANSWERED"
        assert run.missing_requirements != []  # the gap, now visible despite ANSWERED


def test_stats_usage_invalid_group_by_returns_400(client: TestClient) -> None:
    response = client.get("/stats/usage?group_by=not_a_real_field")

    assert response.status_code == 400


def test_stats_usage_groups_real_run_by_method_and_budget(client: TestClient) -> None:
    # budget=777 is distinctive enough that no other test in this module touches it,
    # so this group's counts can be asserted exactly despite the shared test DB.
    state: AppState = client.app.state.suryasutra
    original_llm = state.llm
    state.llm = FakeLLMAdapter([_VALID_RESPONSE])
    _fake_pricing_entry(state)
    try:
        triage_response = client.post(
            "/triage", json={"alarm_id": 1, "method": "requirement_complete", "budget": 777}
        )
    finally:
        state.llm = original_llm
    assert triage_response.status_code == 200

    stats_response = client.get("/stats/usage?group_by=method,budget")

    assert stats_response.status_code == 200
    rows = stats_response.json()
    row = next(r for r in rows if r["method"] == "requirement_complete" and r["budget"] == 777)
    assert row["run_count"] == 1
    assert row["answered_count"] == 1
    assert row["insufficient_count"] == 0
    assert row["full_mandatory_coverage_rate"] == 1.0
    assert row["mean_cost_inr"] is not None and row["mean_cost_inr"] > 0
    assert row["mean_input_tokens"] == 50


def test_feedback_unknown_run_returns_404(client: TestClient) -> None:
    response = client.post(
        "/feedback",
        json={"run_id": 999999, "user_role": "technician", "outcome": "fixed"},
    )

    assert response.status_code == 404


def test_feedback_invalid_outcome_returns_422(client: TestClient) -> None:
    response = client.post(
        "/feedback",
        json={"run_id": 1, "user_role": "technician", "outcome": "not_a_real_outcome"},
    )

    assert response.status_code == 422


def test_feedback_persists_against_a_real_run(client: TestClient) -> None:
    state: AppState = client.app.state.suryasutra
    original_llm = state.llm
    state.llm = FakeLLMAdapter([_VALID_RESPONSE])
    _fake_pricing_entry(state)
    try:
        triage_response = client.post(
            "/triage", json={"alarm_id": 1, "method": "requirement_complete", "budget": 888}
        )
    finally:
        state.llm = original_llm
    assert triage_response.status_code == 200

    from suryasutra.db.models import TriageRun
    from suryasutra.db.session import get_session

    with get_session() as session:
        run = (
            session.query(TriageRun)
            .filter_by(alarm_id=1, method="requirement_complete", budget=888)
            .order_by(TriageRun.id.desc())
            .first()
        )
        assert run is not None
        run_id = run.id

    feedback_response = client.post(
        "/feedback",
        json={
            "run_id": run_id,
            "user_role": "technician",
            "outcome": "wrong_step",
            "note": "Step 2 referenced the wrong switch.",
        },
    )

    assert feedback_response.status_code == 200
    body = feedback_response.json()
    assert body["run_id"] == run_id
    assert body["outcome"] == "wrong_step"
    assert body["note"] == "Step 2 referenced the wrong switch."

    from suryasutra.db.models import Feedback

    with get_session() as session:
        stored = session.query(Feedback).filter_by(run_id=run_id).one()
        assert stored.outcome == "wrong_step"
        assert stored.user_role == "technician"


def test_feedback_allows_multiple_entries_per_run(client: TestClient) -> None:
    state: AppState = client.app.state.suryasutra
    original_llm = state.llm
    state.llm = FakeLLMAdapter([_VALID_RESPONSE])
    _fake_pricing_entry(state)
    try:
        triage_response = client.post(
            "/triage", json={"alarm_id": 1, "method": "requirement_complete", "budget": 889}
        )
    finally:
        state.llm = original_llm
    assert triage_response.status_code == 200

    from suryasutra.db.models import Feedback, TriageRun
    from suryasutra.db.session import get_session

    with get_session() as session:
        run = (
            session.query(TriageRun)
            .filter_by(alarm_id=1, method="requirement_complete", budget=889)
            .order_by(TriageRun.id.desc())
            .first()
        )
        assert run is not None
        run_id = run.id

    client.post("/feedback", json={"run_id": run_id, "user_role": "technician", "outcome": "fixed"})
    client.post(
        "/feedback", json={"run_id": run_id, "user_role": "supervisor", "outcome": "not_fixed"}
    )

    with get_session() as session:
        count = session.query(Feedback).filter_by(run_id=run_id).count()
        assert count == 2
