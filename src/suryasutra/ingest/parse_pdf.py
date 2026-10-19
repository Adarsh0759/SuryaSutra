"""Extract page-level text from a PDF, preserving page numbers for citation provenance (D-23)."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class Page:
    number: int  # 1-indexed, matches what a human cites when reading the PDF
    text: str


def parse_pdf(path: Path) -> list[Page]:
    """Return one Page per PDF page, in reading order, with 1-indexed page numbers."""
    if not path.exists():
        raise FileNotFoundError(path)

    pages: list[Page] = []
    with pymupdf.open(path) as doc:  # type: ignore[no-untyped-call]  # pymupdf ships no stubs
        for index, page in enumerate(doc):
            pages.append(Page(number=index + 1, text=page.get_text()))
    return pages
