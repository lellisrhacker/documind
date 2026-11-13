"""PDF -> pages of text -> chunks -> embeddings -> stored in Postgres."""
import pymupdf  # PyMuPDF

from .chunking import chunk_text
from .config import CHUNK_OVERLAP, CHUNK_SIZE
from .embeddings import embed_texts


def extract_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text), ...] starting at page 1."""
    pages: list[tuple[int, str]] = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for index, page in enumerate(pdf, start=1):
            text = page.get_text().strip()
            if text:
                pages.append((index, text))
    return pages


def build_chunks(pages: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    """Chunk every page separately so each chunk knows its page number.

    Returns [(page, chunk_index, content), ...].
    """
    rows: list[tuple[int, int, str]] = []
    chunk_index = 0
    for page_no, text in pages:
        for piece in chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP):
            rows.append((page_no, chunk_index, piece))
            chunk_index += 1
    return rows


def ingest_pdf(conn, filename: str, pdf_bytes: bytes) -> tuple[int, int, int]:
    """Process a PDF and store it. Returns (document_id, pages, chunks)."""
    pages = extract_pages(pdf_bytes)
    rows = build_chunks(pages)
    if not rows:
        raise ValueError("No text found in this PDF (it may be a scanned image).")

    vectors = embed_texts([content for _, _, content in rows])

    # one transaction: either the whole document is saved or nothing is
    with conn.transaction():
        doc_id = conn.execute(
            "INSERT INTO documents (filename) VALUES (%s) RETURNING id", (filename,)
        ).fetchone()[0]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, page, chunk_index, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    (doc_id, page, idx, content, vec)
                    for (page, idx, content), vec in zip(rows, vectors)
                ],
            )
    return doc_id, len(pages), len(rows)
