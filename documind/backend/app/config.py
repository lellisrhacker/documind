"""All settings in one place. Values come from environment variables (.env file)."""
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/documind"
)
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# text-embedding-3-small returns 1536 numbers per text
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

# Chunking: ~1000 characters per chunk, 200 characters shared with the previous chunk
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# How many chunks we retrieve for each question
TOP_K = int(os.getenv("TOP_K", "5"))

MAX_UPLOAD_MB = 20
