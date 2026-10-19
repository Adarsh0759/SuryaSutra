"""Turn parsed pages into token-counted chunks with page-range provenance (D-23).

Chunking strategy: split each page into paragraphs (blank-line separated), then greedily
pack consecutive paragraphs into a chunk until adding the next one would exceed
`max_tokens`. A paragraph that alone exceeds `max_tokens` becomes its own oversized
chunk rather than being silently split mid-sentence — correctness of citation text
matters more than hitting the budget exactly at this stage; the selector (not the
chunker) is responsible for respecting the overall token budget B.
"""

import re
from dataclasses import dataclass

from suryasutra.ingest.parse_pdf import Page
from suryasutra.usage.tokens import count_tokens

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class Chunk:
    text: str
    page_start: int
    page_end: int
    tokens: int
    doc_type: str
    covers: frozenset[str] = frozenset()  # requirement ids; populated by ingest.tag.tag_chunks


def _paragraphs(page: Page) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(page.text) if p.strip()]


def chunk_pages(pages: list[Page], doc_type: str, max_tokens: int = 300) -> list[Chunk]:
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_tokens = 0
    buffer_page_start: int | None = None
    buffer_page_end: int | None = None

    def flush() -> None:
        nonlocal buffer, buffer_tokens, buffer_page_start, buffer_page_end
        if buffer:
            assert buffer_page_start is not None and buffer_page_end is not None
            chunks.append(
                Chunk(
                    text="\n\n".join(buffer),
                    page_start=buffer_page_start,
                    page_end=buffer_page_end,
                    tokens=buffer_tokens,
                    doc_type=doc_type,
                )
            )
        buffer = []
        buffer_tokens = 0
        buffer_page_start = None
        buffer_page_end = None

    for page in pages:
        for paragraph in _paragraphs(page):
            paragraph_tokens = count_tokens(paragraph)

            if buffer and buffer_tokens + paragraph_tokens > max_tokens:
                flush()

            buffer.append(paragraph)
            buffer_tokens += paragraph_tokens
            buffer_page_start = page.number if buffer_page_start is None else buffer_page_start
            buffer_page_end = page.number

            if buffer_tokens >= max_tokens:
                flush()

    flush()
    return chunks
