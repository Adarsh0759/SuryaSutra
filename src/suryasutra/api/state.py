"""Builds the in-memory corpus, retriever, selectors and pricing once per process.

No DB yet for this slice (M4's first increment) — alarms come straight from
data/synthetic/alarms.json. Persisting runs/usage is a focused follow-up, not needed
for a first end-to-end alarm -> triage round trip to work.
"""

import json
from pathlib import Path
from typing import Any

from config.settings import settings

from suryasutra.generation.llm.base import LLMAdapter
from suryasutra.generation.llm.groq_adapter import GroqAdapter
from suryasutra.ingest.build_index import build_corpus
from suryasutra.ingest.tag import (
    FaultCategory,
    Requirement,
    load_fault_categories,
    load_requirements,
)
from suryasutra.retrieval.bm25 import BM25Index
from suryasutra.retrieval.dense import DenseIndex
from suryasutra.retrieval.hybrid import HybridRetriever
from suryasutra.selection.base import Selector
from suryasutra.selection.baselines import (
    KnapsackSelector,
    MMRSelector,
    SafetySlotSelector,
    TopKSelector,
)
from suryasutra.selection.requirement_complete import RequirementCompleteSelector
from suryasutra.usage.cost import PricingTable, load_pricing

REPO_ROOT = Path(__file__).resolve().parents[3]
MANUAL_PATH = REPO_ROOT / "data" / "raw" / "sungrow_sg150cx_user_manual.pdf"
REQUIREMENTS_PATH = REPO_ROOT / "config" / "requirements.yaml"
PRICING_PATH = REPO_ROOT / "config" / "pricing.yaml"
ALARMS_PATH = REPO_ROOT / "data" / "synthetic" / "alarms.json"

SELECTORS: dict[str, Selector] = {
    "topk": TopKSelector(),
    "knapsack": KnapsackSelector(),
    "mmr": MMRSelector(),
    "safety_slot": SafetySlotSelector(),
    "requirement_complete": RequirementCompleteSelector(),
}


class AppState:
    requirements: dict[str, Requirement]
    fault_categories: dict[str, FaultCategory]
    retriever: HybridRetriever
    pricing: PricingTable
    alarms: dict[int, dict[str, Any]]
    llm: LLMAdapter | None

    def __init__(self) -> None:
        self.requirements = load_requirements(REQUIREMENTS_PATH)
        self.fault_categories = load_fault_categories(REQUIREMENTS_PATH)
        chunks = build_corpus(MANUAL_PATH, doc_type="manual", requirements=self.requirements)
        self.retriever = HybridRetriever(BM25Index(chunks), DenseIndex(chunks))
        self.pricing = load_pricing(PRICING_PATH)
        alarm_list = json.loads(ALARMS_PATH.read_text(encoding="utf-8"))["alarms"]
        self.alarms = {alarm["id"]: alarm for alarm in alarm_list}
        self.llm = (
            GroqAdapter(api_key=settings.groq_api_key, model=settings.llm_model)
            if settings.groq_api_key
            else None
        )

    def selector(self, method: str) -> Selector:
        if method not in SELECTORS:
            raise KeyError(method)
        return SELECTORS[method]
