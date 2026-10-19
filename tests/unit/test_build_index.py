from pathlib import Path

import pymupdf

from suryasutra.ingest.build_index import build_corpus
from suryasutra.ingest.tag import Requirement


def _make_pdf(path: Path, texts: list[str]) -> None:
    doc = pymupdf.open()
    for text in texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_build_corpus_produces_tagged_chunks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, ["Isolate the DC side before opening the enclosure."])
    requirements = {
        "safety_isolation": Requirement(
            id="safety_isolation",
            description="x",
            review_status="unreviewed",
            doc_types=frozenset({"manual"}),
            keywords_any=("isolate the dc side",),
        ),
    }

    chunks = build_corpus(pdf_path, doc_type="manual", requirements=requirements)

    assert len(chunks) == 1
    assert chunks[0].doc_type == "manual"
    assert chunks[0].page_start == 1
    assert chunks[0].covers == frozenset({"safety_isolation"})
