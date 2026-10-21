"""FastAPI app wiring the triage pipeline (retrieval -> selection -> generation) over
HTTP (M4; CLAUDE.md §10). Application code may import research code (D-28) — never
the other way around.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from config.settings import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from suryasutra.api.schemas import TriageRequest
from suryasutra.api.state import AppState
from suryasutra.db.models import Alarm, TriageRun
from suryasutra.db.models import Usage as UsageRow
from suryasutra.db.session import get_session
from suryasutra.generation.generate import generate_triage_answer
from suryasutra.generation.prompts.triage_prompt import AlarmInfo
from suryasutra.generation.schema import AnsweredContract, InsufficientContract
from suryasutra.retrieval.dense import EMBEDDING_MODEL_NAME
from suryasutra.selection.base import Candidate, Insufficient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.suryasutra = AppState()
    yield


app = FastAPI(title="SuryaSutra API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/alarms")
def list_alarms() -> list[dict[str, Any]]:
    with get_session() as session:
        rows = session.query(Alarm).order_by(Alarm.id).all()
        return [
            {
                "id": a.id,
                "site_id": a.site_id,
                "inverter_id": a.inverter_id,
                "brand": a.brand,
                "model": a.model,
                "code": a.code,
                "category": a.category,
                "message": a.message,
                "raised_at": a.raised_at.isoformat(),
                "is_synthetic": a.is_synthetic,
                "answerable": a.answerable,
            }
            for a in rows
        ]


@app.post("/triage")
def triage(req: TriageRequest, request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.suryasutra

    alarm = state.alarms.get(req.alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail=f"alarm {req.alarm_id} not found")

    try:
        selector = state.selector(req.method)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"unknown method: {req.method}") from exc

    category = state.fault_categories.get(alarm["category"])
    if category is None:
        raise HTTPException(status_code=500, detail=f"unknown fault category: {alarm['category']}")

    results = state.retriever.query(alarm["message"], top_k=40)
    candidates = [
        Candidate(chunk=r.chunk, relevance=r.score, embedding=r.embedding) for r in results
    ]
    selection = selector.select(
        candidates, must=category.must, optional=category.optional, budget=req.budget
    )

    if isinstance(selection, Insufficient):
        contract = InsufficientContract(
            reason=selection.reason,
            missing_requirements=sorted(selection.missing),
            suggested_next="Add more evidence sources, or increase the token budget.",
        )
        _persist_run(req, alarm["id"], contract, selected_chunk_ids=[])
        return contract.model_dump()

    if state.llm is None:
        raise HTTPException(status_code=503, detail="LLM not configured (GROQ_API_KEY missing)")

    alarm_info = AlarmInfo(code=alarm["code"], message=alarm["message"])
    result = generate_triage_answer(
        alarm_info,
        selection,
        state.llm,
        budget=req.budget,
        method=req.method,
        pricing=state.pricing,
    )
    selected_ids = list(result.sources.keys()) if isinstance(result, AnsweredContract) else []
    _persist_run(req, alarm["id"], result, selected_chunk_ids=selected_ids)
    return result.model_dump()


def _persist_run(
    req: TriageRequest,
    alarm_id: int,
    contract: AnsweredContract | InsufficientContract,
    selected_chunk_ids: list[str],
) -> None:
    """Writes one triage_runs row (+ a usage row when the LLM was actually called).
    An INSUFFICIENT contract from the selector phase never reaches generation, so it
    naturally has no usage row — nothing was spent."""
    with get_session() as session:
        run = TriageRun(
            alarm_id=alarm_id,
            method=req.method,
            budget=req.budget,
            selected_chunk_ids=selected_chunk_ids,
            status=contract.status,
            missing_requirements=(
                contract.missing_requirements if isinstance(contract, InsufficientContract) else []
            ),
            answer_json=contract.model_dump(),
            model=settings.llm_model if isinstance(contract, AnsweredContract) else None,
            embedding_model=EMBEDDING_MODEL_NAME
            if isinstance(contract, AnsweredContract)
            else None,
            created_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()  # populates run.id before the Usage row needs it

        if isinstance(contract, AnsweredContract):
            session.add(
                UsageRow(
                    run_id=run.id,
                    input_tokens=contract.usage.input_tokens,
                    output_tokens=contract.usage.output_tokens,
                    token_source="provider",  # D-22: provider-reported usage, ground truth
                    cost_inr=contract.usage.cost_inr,
                )
            )


@app.get("/runs/{run_id}")
def get_run(run_id: int) -> dict[str, Any]:
    with get_session() as session:
        run = session.get(TriageRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"run {run_id} not found")
        usage = run.usage
        return {
            "id": run.id,
            "alarm_id": run.alarm_id,
            "method": run.method,
            "budget": run.budget,
            "selected_chunk_ids": run.selected_chunk_ids,
            "status": run.status,
            "missing_requirements": run.missing_requirements,
            "answer": run.answer_json,
            "created_at": run.created_at.isoformat(),
            "usage": (
                {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cost_inr": usage.cost_inr,
                    "token_source": usage.token_source,
                }
                if usage is not None
                else None
            ),
        }
