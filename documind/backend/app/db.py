"""Postgres + pgvector setup.

Two tables:
  documents(id, filename, created_at)
  chunks(id, document_id, page, chunk_index, content, embedding vector(1536))

The HNSW index makes "find the nearest embeddings" fast (cosine distance).
"""
import psycopg
from pgvector.psycopg import register_vector

from .config import DATABASE_URL, EMBEDDING_DIM

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    filename    TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           SERIAL PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page         INTEGER NOT NULL,
    chunk_index  INTEGER NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector({EMBEDDING_DIM}) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks (document_id);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
"""


def init_db() -> None:
    """Create the extension and tables if they do not exist. Runs on startup."""
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(SCHEMA)


def get_conn() -> psycopg.Connection:
    """New connection per request (simple and fine for a small project)."""
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    register_vector(conn)  # lets us pass numpy arrays as vector values
    return conn
