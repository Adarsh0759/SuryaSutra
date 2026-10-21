"""M1 done-criterion (CLAUDE.md §15): retrieval returns sensible top-10 for 10 sample
alarms. Checks, per synthetic *answerable* alarm, that hybrid retrieval's top-10
includes at least one chunk covering one of that alarm's fault category's *mandatory*
requirements. The 2 deliberately-unanswerable alarms (D-14) are checked the other way:
retrieval should *not* find a covering chunk for them either — confirming they're
genuinely hard cases, not mislabelled ones.

This is a retrieval sanity check, not an eval claim (D-11) — the selector (M2) and its
own invariant tests are what actually enforce mandatory coverage end to end. The
thresholds below are the measured results on this run, not assumed targets; if either
drops, that's a real regression to investigate, not a flaky test to loosen.
"""

import json
from pathlib import Path

import pytest
from sentence_transformers import SentenceTransformer

from suryasutra.ingest.build_index import build_corpus
from suryasutra.ingest.tag import FaultCategory, load_fault_categories, load_requirements
from suryasutra.retrieval.bm25 import BM25Index
from suryasutra.retrieval.dense import EMBEDDING_MODEL_NAME, DenseIndex
from suryasutra.retrieval.hybrid import HybridRetriever

REPO_ROOT = Path(__file__).parents[2]
MANUAL_PATH = REPO_ROOT / "data" / "raw" / "sungrow_sg150cx_user_manual.pdf"
REQUIREMENTS_PATH = REPO_ROOT / "config" / "requirements.yaml"
ALARMS_PATH = REPO_ROOT / "data" / "synthetic" / "alarms.json"

pytestmark = pytest.mark.skipif(
    not MANUAL_PATH.exists(),
    reason="real manual not downloaded locally; run `bash scripts/download_docs.sh` first",
)


@pytest.fixture(scope="module")
def retriever() -> HybridRetriever:
    requirements = load_requirements(REQUIREMENTS_PATH)
    chunks = build_corpus(MANUAL_PATH, doc_type="manual", requirements=requirements)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return HybridRetriever(BM25Index(chunks), DenseIndex(chunks, model=model))


@pytest.fixture(scope="module")
def fault_categories() -> dict[str, FaultCategory]:
    return load_fault_categories(REQUIREMENTS_PATH)


@pytest.fixture(scope="module")
def alarms() -> list[dict]:
    data = json.loads(ALARMS_PATH.read_text(encoding="utf-8"))
    assert all(a["is_synthetic"] for a in data["alarms"]), "all prototype alarms must be synthetic"
    return data["alarms"]


def test_top_10_retrieval_surfaces_a_mandatory_requirement_chunk_for_each_answerable_alarm(
    retriever: HybridRetriever,
    fault_categories: dict[str, FaultCategory],
    alarms: list[dict],
) -> None:
    misses = []
    for alarm in alarms:
        if not alarm["answerable"]:
            continue
        category = fault_categories[alarm["category"]]
        results = retriever.query(alarm["message"], top_k=10)
        if not any(result.chunk.covers & category.must for result in results):
            misses.append(alarm["id"])

    # Measured 10/10 answerable alarms on this corpus as of this writing (D-11: not assumed).
    assert not misses, f"answerable alarms with no mandatory-requirement chunk in top 10: {misses}"


def test_top_10_retrieval_finds_no_mandatory_requirement_chunk_for_unanswerable_alarms(
    retriever: HybridRetriever,
    fault_categories: dict[str, FaultCategory],
    alarms: list[dict],
) -> None:
    false_hits = []
    for alarm in alarms:
        if alarm["answerable"]:
            continue
        category = fault_categories[alarm["category"]]
        results = retriever.query(alarm["message"], top_k=10)
        if any(result.chunk.covers & category.must for result in results):
            false_hits.append(alarm["id"])

    assert not false_hits, f"unanswerable alarms unexpectedly matched a chunk: {false_hits}"
