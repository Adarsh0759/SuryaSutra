"""Common selector interface and result types (D-06, D-08, CLAUDE.md §5/§6).

Every selector takes the same inputs and returns the same result shape so experiments
and the UI toggle can swap methods without touching callers. Mandatory requirement
coverage is a hard constraint for the research selector, never a weight (D-06) —
`Insufficient` is a first-class result, not an exception. Baselines (TopK, MMR,
knapsack) are free to never check feasibility at all; that's the comparison point.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from suryasutra.ingest.chunk import Chunk


@dataclass(frozen=True)
class Candidate:
    chunk: Chunk
    relevance: float  # normalized hybrid retrieval score, higher = more relevant
    # Normalized embedding, as a plain tuple (not numpy) so Candidate stays a safely
    # comparable/hashable dataclass. Used only for the fill-phase dedup check.
    embedding: tuple[float, ...] | None = None


@dataclass(frozen=True)
class Answered:
    selected: tuple[Chunk, ...]
    tokens_used: int


@dataclass(frozen=True)
class Insufficient:
    reason: Literal["no_evidence", "over_budget"]
    missing: frozenset[str]  # mandatory requirement ids not in the (non-)answer
    needed_tokens: int | None = None  # set only for "over_budget"


SelectionResult = Answered | Insufficient


def cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class Selector(ABC):
    @abstractmethod
    def select(
        self,
        candidates: list[Candidate],
        must: frozenset[str],
        optional: frozenset[str],
        budget: int,
    ) -> SelectionResult:
        """Pick chunks from `candidates` to answer within `budget` tokens."""
