"""FastAPI app: upload PDFs, list/delete them, and chat with a document."""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import FRONTEND_ORIGIN, MAX_UPLOAD_MB, TOP_K
from .db import get_conn, init_db
from .embeddings import embed_texts
from .ingest import ingest_pdf
from .rag import retrieve, stream_answer


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="DocuMind API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    document_id: int
    question: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_MB} MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "This file is not a valid PDF.")

    conn = get_conn()
    try:
        doc_id, pages, chunks = ingest_pdf(conn, file.filename, data)
    except ValueError as err:
        raise HTTPException(422, str(err))
    finally:
        conn.close()
    return {"id": doc_id, "filename": file.filename, "pages": pages, "chunks": chunks}


@app.get("/documents")
def list_documents():
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT d.id, d.filename, d.created_at, COUNT(c.id)
            FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id ORDER BY d.created_at DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "filename": r[1], "created_at": r[2].isoformat(), "chunks": r[3]}
        for r in rows
    ]


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int):
    conn = get_conn()
    try:
        deleted = conn.execute(
            "DELETE FROM documents WHERE id = %s RETURNING id", (document_id,)
        ).fetchone()
    finally:
        conn.close()
    if not deleted:
        raise HTTPException(404, "Document not found.")


@app.post("/chat")
def chat(req: ChatRequest):
    """Streams newline-delimited JSON:
    1st line: {"type": "sources", "sources": [...]}
    then many: {"type": "token", "text": "..."}
    last:     {"type": "done"}
    """
    conn = get_conn()
    try:
        exists = conn.execute(
            "SELECT 1 FROM documents WHERE id = %s", (req.document_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, "Document not found.")
        query_vec = embed_texts([req.question])[0]
        chunks = retrieve(conn, req.document_id, query_vec, TOP_K)
    finally:
        conn.close()

    def event_stream():
        sources = [
            {"id": i, "page": c["page"], "score": round(c["score"], 3), "text": c["content"]}
            for i, c in enumerate(chunks, start=1)
        ]
        yield json.dumps({"type": "sources", "sources": sources}) + "\n"
        try:
            for token in stream_answer(req.question, chunks):
                yield json.dumps({"type": "token", "text": token}) + "\n"
        except Exception as err:  # tell the UI instead of silently cutting the stream
            yield json.dumps({"type": "error", "message": str(err)}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
