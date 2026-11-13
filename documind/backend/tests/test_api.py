"""API tests that do not need Postgres or OpenAI: those parts are replaced by fakes."""
import json

import numpy as np
from fastapi.testclient import TestClient

from app import main


class FakeConn:
    def execute(self, *args, **kwargs):
        class Result:
            def fetchone(self_inner):
                return (1,)

        return Result()

    def close(self):
        pass


def make_client(monkeypatch):
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "get_conn", lambda: FakeConn())
    monkeypatch.setattr(main, "embed_texts", lambda texts: [np.zeros(3, dtype=np.float32)])
    monkeypatch.setattr(
        main,
        "retrieve",
        lambda conn, doc_id, vec, k: [{"id": 10, "page": 2, "content": "Cats sleep.", "score": 0.91234}],
    )
    monkeypatch.setattr(main, "stream_answer", lambda q, chunks: iter(["Cats ", "sleep [1]."]))
    return TestClient(main.app)


def test_health(monkeypatch):
    with make_client(monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_chat_streams_sources_then_tokens_then_done(monkeypatch):
    with make_client(monkeypatch) as client:
        res = client.post("/chat", json={"document_id": 1, "question": "What do cats do?"})
    assert res.status_code == 200
    events = [json.loads(line) for line in res.text.strip().split("\n")]
    assert events[0]["type"] == "sources"
    assert events[0]["sources"][0] == {"id": 1, "page": 2, "score": 0.912, "text": "Cats sleep."}
    assert "".join(e["text"] for e in events if e["type"] == "token") == "Cats sleep [1]."
    assert events[-1] == {"type": "done"}


def test_chat_rejects_empty_question(monkeypatch):
    with make_client(monkeypatch) as client:
        res = client.post("/chat", json={"document_id": 1, "question": ""})
    assert res.status_code == 422


def test_upload_rejects_non_pdf(monkeypatch):
    with make_client(monkeypatch) as client:
        res = client.post("/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert res.status_code == 400
