"""The RAG part: retrieve the best chunks, then ask the LLM to answer from them."""
from collections.abc import Iterator

import numpy as np

from .config import CHAT_MODEL
from .embeddings import get_client

SYSTEM_PROMPT = (
    "You answer questions about a PDF document using ONLY the numbered context "
    "passages provided. Cite the passages you used like [1] or [2]. "
    "If the answer is not in the context, say you could not find it in the "
    "document. Do not make things up."
)


def retrieve(conn, document_id: int, query_vec: np.ndarray, k: int) -> list[dict]:
    """Find the k chunks whose embeddings are closest to the question's embedding.

    `<=>` is pgvector's cosine distance operator (0 = identical direction).
    Similarity score = 1 - distance.
    """
    rows = conn.execute(
        """
        SELECT id, page, content, 1 - (embedding <=> %s) AS score
        FROM chunks
        WHERE document_id = %s
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (query_vec, document_id, query_vec, k),
    ).fetchall()
    return [
        {"id": r[0], "page": r[1], "content": r[2], "score": float(r[3])} for r in rows
    ]


def build_messages(question: str, chunks: list[dict]) -> list[dict]:
    context = "\n\n".join(
        f"[{i}] (page {c['page']})\n{c['content']}" for i, c in enumerate(chunks, start=1)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        },
    ]


def stream_answer(question: str, chunks: list[dict]) -> Iterator[str]:
    """Yield the answer token by token so the UI can show it as it is written."""
    stream = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=build_messages(question, chunks),
        temperature=0.2,
        stream=True,
    )
    for event in stream:
        if not event.choices:
            continue
        token = event.choices[0].delta.content
        if token:
            yield token
