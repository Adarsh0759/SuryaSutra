from pathlib import Path

import pymupdf
import pytest

from suryasutra.ingest.parse_pdf import parse_pdf


def _make_pdf(path: Path, texts: list[str]) -> None:
    doc = pymupdf.open()
    for text in texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_parse_pdf_preserves_page_order_and_1_indexed_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, ["Isolate DC side before opening.", "Check insulation resistance."])

    pages = parse_pdf(pdf_path)

    assert [p.number for p in pages] == [1, 2]
    assert "Isolate DC side" in pages[0].text
    assert "insulation resistance" in pages[1].text


def test_parse_pdf_raises_on_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(FileNotFoundError):
        parse_pdf(missing)
