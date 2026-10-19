"""Lexical retrieval over chunks (D-20).

BM25's strength here is exact strings — fault codes ("364-395"), part numbers — which
dense embeddings tend to blur. The tokenizer keeps hyphenated codes as single tokens
so a query for "364-395" doesn't get split into "364" and "395" and matched loosely.
"""

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from suryasutra.ingest.chunk import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class BM25Index:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self._bm25 = BM25Okapi([_tokenize(c.text) for c in chunks]) if chunks else None

    def query(self, text: str, top_k: int = 10) -> list[ScoredChunk]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(text))
        ranked = sorted(zip(self._chunks, scores), key=lambda pair: pair[1], reverse=True)
        return [ScoredChunk(chunk=c, score=float(s)) for c, s in ranked[:top_k]]
