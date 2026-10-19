from suryasutra.ingest.chunk import chunk_pages
from suryasutra.ingest.parse_pdf import Page


def test_small_paragraphs_on_one_page_merge_into_one_chunk() -> None:
    page = Page(number=1, text="First paragraph.\n\nSecond paragraph.")

    chunks = chunk_pages([page], doc_type="manual", max_tokens=300)

    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert "First paragraph." in chunks[0].text
    assert "Second paragraph." in chunks[0].text
    assert chunks[0].doc_type == "manual"


def test_chunk_can_span_consecutive_pages() -> None:
    pages = [
        Page(number=1, text="Isolate the DC side before opening."),
        Page(number=2, text="Wait for capacitors to discharge."),
    ]

    chunks = chunk_pages(pages, doc_type="safety", max_tokens=300)

    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2


def test_no_data_loss_across_many_small_paragraphs() -> None:
    page = Page(
        number=1,
        text="\n\n".join(f"Paragraph number {i}." for i in range(20)),
    )

    chunks = chunk_pages([page], doc_type="manual", max_tokens=15)

    all_text = " ".join(c.text for c in chunks)
    for i in range(20):
        assert f"Paragraph number {i}." in all_text


def test_oversized_single_paragraph_is_its_own_chunk_not_dropped() -> None:
    huge_paragraph = "word " * 500
    page = Page(number=1, text=huge_paragraph)

    chunks = chunk_pages([page], doc_type="manual", max_tokens=5)

    assert len(chunks) == 1
    assert chunks[0].tokens > 5
    assert chunks[0].text.strip() == huge_paragraph.strip()


def test_no_chunk_exceeds_max_tokens_when_paragraphs_are_individually_small() -> None:
    page = Page(
        number=1,
        text="\n\n".join(f"Short paragraph {i}." for i in range(30)),
    )

    chunks = chunk_pages([page], doc_type="manual", max_tokens=20)

    for c in chunks[:-1]:
        assert c.tokens <= 20 or len(c.text.split("\n\n")) == 1


def test_empty_page_produces_no_chunks() -> None:
    page = Page(number=1, text="   \n\n   ")

    chunks = chunk_pages([page], doc_type="manual", max_tokens=300)

    assert chunks == []
