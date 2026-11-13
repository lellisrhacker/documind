"""Turn text into embeddings (lists of numbers that capture meaning).

Texts with similar meaning get vectors that point in similar directions, which
is what lets us search by meaning instead of exact keywords.
"""
import numpy as np
from openai import OpenAI

from .config import EMBEDDING_MODEL, OPENAI_API_KEY

BATCH_SIZE = 100  # the API accepts many texts per request; batching is much faster

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to backend/.env")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    vectors: list[np.ndarray] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = get_client().embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(np.array(item.embedding, dtype=np.float32) for item in response.data)
    return vectors
