from suryasutra.ingest.chunk import Chunk
from suryasutra.retrieval.bm25 import BM25Index, _tokenize


def _chunk(text: str, page: int = 1) -> Chunk:
    return Chunk(text=text, page_start=page, page_end=page, tokens=10, doc_type="manual")


def test_tokenize_keeps_hyphenated_fault_code_as_one_token() -> None:
    tokens = _tokenize("Fault code 364-395 indicates Boost Capacitor Overvoltage.")
    assert "364-395" in tokens
    assert "364" not in tokens
    assert "395" not in tokens


def test_exact_fault_code_query_ranks_matching_chunk_first() -> None:
    chunks = [
        _chunk("1600-1615 PV Grounding Fault: disconnect the DC switch below 0.5 A.", page=103),
        _chunk(
            "364-395 Boost Capacitor Overvoltage Fault: disconnect AC and DC switches.", page=104
        ),
        _chunk("8 Grid Overfrequency: wait for the grid to return to normal.", page=97),
    ]
    index = BM25Index(chunks)

    results = index.query("364-395", top_k=1)

    assert results[0].chunk.page_start == 104


def test_topical_query_ranks_relevant_chunk_first() -> None:
    chunks = [
        _chunk("Check insulation resistance between PV positive and ground.", page=50),
        _chunk("Replace the cooling fan if it makes unusual noise.", page=108),
        _chunk(
            "Grid overfrequency: inverter reconnects automatically once grid normalizes.", page=97
        ),
    ]
    index = BM25Index(chunks)

    results = index.query("insulation resistance ground", top_k=1)

    assert results[0].chunk.page_start == 50


def test_top_k_limits_number_of_results() -> None:
    chunks = [_chunk(f"Fault code {i} corrective measure text.", page=i) for i in range(5)]
    index = BM25Index(chunks)

    results = index.query("fault code corrective", top_k=2)

    assert len(results) == 2


def test_empty_index_returns_no_results() -> None:
    index = BM25Index([])

    assert index.query("anything") == []
