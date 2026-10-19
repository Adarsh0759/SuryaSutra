"""Dense (embedding) retrieval over chunks (D-20, D-19).

Catches paraphrased symptoms that BM25 misses (e.g. a technician's "inverter won't
restart" vs. the manual's "once a fault occurs ... fault information is displayed").
FAISS flat index for the prototype; swapped for Qdrant at pilot scale behind the same
shape of interface (D-19) — this module stays a plain in-memory index for now.
"""

from dataclasses import dataclass

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from suryasutra.ingest.chunk import Chunk

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class DenseIndex:
    def __init__(self, chunks: list[Chunk], model: SentenceTransformer | None = None) -> None:
        self._chunks = chunks
        self._model = model or SentenceTransformer(EMBEDDING_MODEL_NAME)
        self._index: faiss.IndexFlatIP | None = None

        if chunks:
            embeddings = self._embed([c.text for c in chunks])
            self._index = faiss.IndexFlatIP(embeddings.shape[1])
            self._index.add(embeddings)

    def _embed(self, texts: list[str]) -> np.ndarray:
        # normalize_embeddings=True turns inner product into cosine similarity.
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)

    def query(self, text: str, top_k: int = 10) -> list[ScoredChunk]:
        if self._index is None:
            return []
        query_vec = self._embed([text])
        k = min(top_k, len(self._chunks))
        scores, indices = self._index.search(query_vec, k)
        return [
            ScoredChunk(chunk=self._chunks[idx], score=float(score))
            for idx, score in zip(indices[0], scores[0])
            if idx != -1
        ]
