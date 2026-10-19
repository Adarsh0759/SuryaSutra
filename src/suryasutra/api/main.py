"""FastAPI app wiring the triage pipeline (retrieval -> selection -> generation) over
HTTP (M4; CLAUDE.md §10). Application code may import research code (D-28) — never
the other way around.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from suryasutra.api.schemas import TriageRequest
from suryasutra.api.state import AppState
from suryasutra.generation.generate import generate_triage_answer
from suryasutra.generation.prompts.triage_prompt import AlarmInfo
from suryasutra.generation.schema import InsufficientContract
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
def list_alarms(request: Request) -> list[dict[str, Any]]:
    state: AppState = request.app.state.suryasutra
    return list(state.alarms.values())


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
    candidates = [Candidate(chunk=r.chunk, relevance=r.score) for r in results]
    selection = selector.select(
        candidates, must=category.must, optional=category.optional, budget=req.budget
    )

    if isinstance(selection, Insufficient):
        return InsufficientContract(
            reason=selection.reason,
            missing_requirements=sorted(selection.missing),
            suggested_next="Add more evidence sources, or increase the token budget.",
        ).model_dump()

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
    return result.model_dump()
