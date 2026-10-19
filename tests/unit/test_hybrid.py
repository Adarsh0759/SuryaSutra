import pytest
from sentence_transformers import SentenceTransformer

from suryasutra.ingest.chunk import Chunk
from suryasutra.retrieval.bm25 import BM25Index
from suryasutra.retrieval.dense import EMBEDDING_MODEL_NAME, DenseIndex
from suryasutra.retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion


def _chunk(text: str, page: int = 1) -> Chunk:
    return Chunk(text=text, page_start=page, page_end=page, tokens=10, doc_type="manual")


def test_rrf_boosts_chunk_ranked_well_in_both_lists() -> None:
    a = _chunk("appears in both lists", page=1)
    b = _chunk("appears only in list two, but ranked first there", page=2)
    c = _chunk("appears only in list one, ranked second there", page=3)

    list_one = [a, c]
    list_two = [b, a]

    fused = reciprocal_rank_fusion([list_one, list_two])

    assert fused[0].chunk == a


def test_rrf_single_ranking_preserves_relative_order() -> None:
    a = _chunk("first", page=1)
    b = _chunk("second", page=2)

    fused = reciprocal_rank_fusion([[a, b]])

    assert [sc.chunk for sc in fused] == [a, b]


def test_rrf_empty_rankings_returns_empty() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


@pytest.fixture(scope="module")
def model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def test_hybrid_retriever_combines_exact_and_paraphrased_matches(
    model: SentenceTransformer,
) -> None:
    chunks = [
        _chunk(
            "364-395 Boost Capacitor Overvoltage Fault: disconnect AC and DC switches.", page=103
        ),
        _chunk("Measure the resistance to ground of the PV string and DC cable.", page=99),
        _chunk("Replace the cooling fan if it makes unusual noise.", page=108),
    ]
    retriever = HybridRetriever(BM25Index(chunks), DenseIndex(chunks, model=model))

    exact_results = retriever.query("364-395", top_k=1)
    paraphrase_results = retriever.query("earth leakage check on the array wiring", top_k=1)

    assert exact_results[0].chunk.page_start == 103
    assert paraphrase_results[0].chunk.page_start == 99


def test_hybrid_retriever_respects_top_k(model: SentenceTransformer) -> None:
    chunks = [_chunk(f"Fault code {i} corrective measure text.", page=i) for i in range(5)]
    retriever = HybridRetriever(BM25Index(chunks), DenseIndex(chunks, model=model))

    results = retriever.query("fault code corrective", top_k=2)

    assert len(results) == 2
