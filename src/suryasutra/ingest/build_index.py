"""Wire parse -> chunk -> tag into one call to build a document's corpus of chunks.

Kept separate from any retrieval/DB concerns (D-28): this module only produces
`Chunk` objects with `.covers` populated. Building a BM25/dense index over them, or
persisting them, is the caller's job.
"""

from pathlib import Path

from suryasutra.ingest.chunk import Chunk, chunk_pages
from suryasutra.ingest.parse_pdf import parse_pdf
from suryasutra.ingest.tag import Requirement, tag_chunks


def build_corpus(
    pdf_path: Path,
    doc_type: str,
    requirements: dict[str, Requirement],
    max_tokens: int = 300,
) -> list[Chunk]:
    pages = parse_pdf(pdf_path)
    chunks = chunk_pages(pages, doc_type=doc_type, max_tokens=max_tokens)
    return tag_chunks(chunks, requirements)
