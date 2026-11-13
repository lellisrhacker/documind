import pytest

from app.chunking import chunk_text
from app.rag import build_messages


def test_empty_text_gives_no_chunks():
    assert chunk_text("   \n  ") == []


def test_short_text_is_one_chunk():
    assert chunk_text("hello world", size=100, overlap=10) == ["hello world"]


def test_chunks_respect_size_and_cover_all_words():
    words = [f"word{i}" for i in range(500)]
    text = " ".join(words)
    chunks = chunk_text(text, size=200, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    joined = " ".join(chunks)
    assert all(w in joined for w in words)


def test_neighbouring_chunks_overlap():
    text = " ".join(f"w{i}" for i in range(300))
    chunks = chunk_text(text, size=200, overlap=60)
    for a, b in zip(chunks, chunks[1:]):
        tail_words = set(a.split()[-5:])
        assert tail_words & set(b.split())  # shared words at the boundary


def test_words_are_not_split():
    text = " ".join(["abcdefghij"] * 100)
    for c in chunk_text(text, size=95, overlap=20):
        assert all(w == "abcdefghij" for w in c.split())


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("text", size=10, overlap=10)


def test_prompt_contains_numbered_context_and_question():
    chunks = [{"page": 3, "content": "Cats sleep a lot."}, {"page": 7, "content": "Dogs bark."}]
    messages = build_messages("What do cats do?", chunks)
    user = messages[1]["content"]
    assert "[1] (page 3)" in user and "[2] (page 7)" in user
    assert "What do cats do?" in user
