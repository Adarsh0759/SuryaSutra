"""Hybrid retrieval: fuse BM25 and dense rankings (D-20).

Uses Reciprocal Rank Fusion (RRF), not raw score blending — BM25 scores and cosine
similarities live on different, incomparable scales, so adding them directly would let
whichever happens to have larger magnitude dominate. RRF only looks at rank position,
which is scale-free by construction.
"""

from dataclasses import dataclass

from suryasutra.ingest.chunk import Chunk
from suryasutra.retrieval.bm25 import BM25Index
from suryasutra.retrieval.dense import DenseIndex


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float
    embedding: tuple[float, ...] | None = None


def reciprocal_rank_fusion(rankings: list[list[Chunk]], k: int = 60) -> list[ScoredChunk]:
    """Combine multiple rankings of (possibly overlapping) chunks by rank position only."""
    scores: dict[Chunk, float] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank)
    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [ScoredChunk(chunk=c, score=s) for c, s in ranked]


class HybridRetriever:
    def __init__(self, bm25: BM25Index, dense: DenseIndex) -> None:
        self._bm25 = bm25
        self._dense = dense

    def query(self, text: str, top_k: int = 10, candidate_k: int = 40) -> list[ScoredChunk]:
        bm25_chunks = [r.chunk for r in self._bm25.query(text, top_k=candidate_k)]
        dense_chunks = [r.chunk for r in self._dense.query(text, top_k=candidate_k)]
        fused = reciprocal_rank_fusion([bm25_chunks, dense_chunks])[:top_k]
        # Every chunk in the corpus has a dense embedding regardless of which
        # ranking(s) it came from — attach it so selectors that need it (MMR's
        # diversity penalty, RequirementCompleteSelector's near-duplicate dedup)
        # actually have one (D-20 gap found during the M5 eval run: this was
        # previously always None, silently disabling both).
        return [
            ScoredChunk(
                chunk=sc.chunk, score=sc.score, embedding=self._dense.embedding_for(sc.chunk)
            )
            for sc in fused
        ]
