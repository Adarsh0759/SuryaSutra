import pytest
from sentence_transformers import SentenceTransformer

from suryasutra.ingest.chunk import Chunk
from suryasutra.retrieval.dense import EMBEDDING_MODEL_NAME, DenseIndex


@pytest.fixture(scope="module")
def model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _chunk(text: str, page: int = 1) -> Chunk:
    return Chunk(text=text, page_start=page, page_end=page, tokens=10, doc_type="manual")


def test_paraphrased_query_ranks_semantically_relevant_chunk_first(
    model: SentenceTransformer,
) -> None:
    chunks = [
        _chunk("Measure the resistance to ground of the PV string and DC cable.", page=99),
        _chunk("Replace the cooling fan if it makes unusual noise.", page=108),
        _chunk("The inverter display shows the fault code when a fault occurs.", page=96),
    ]
    index = DenseIndex(chunks, model=model)

    # No shared keywords with the target chunk's exact wording — tests the dense,
    # not lexical, path.
    results = index.query("how do I check for a leakage path to earth on the array", top_k=1)

    assert results[0].chunk.page_start == 99


def test_top_k_limits_number_of_results(model: SentenceTransformer) -> None:
    chunks = [_chunk(f"Fault code {i} corrective measure text.", page=i) for i in range(5)]
    index = DenseIndex(chunks, model=model)

    results = index.query("fault code corrective", top_k=2)

    assert len(results) == 2


def test_empty_index_returns_no_results(model: SentenceTransformer) -> None:
    index = DenseIndex([], model=model)

    assert index.query("anything") == []
