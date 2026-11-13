"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import Chat from "@/components/Chat";
import {
  DocumentItem,
  deleteDocument,
  listDocuments,
  uploadDocument,
} from "@/lib/api";

export default function Home() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const items = await listDocuments();
      setDocs(items);
      setSelectedId((current) =>
        current !== null && items.some((d) => d.id === current)
          ? current
          : items[0]?.id ?? null
      );
    } catch (err) {
      setError(`Cannot reach the API. Is the backend running? (${(err as Error).message})`);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow uploading the same file again
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await uploadDocument(file);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(id: number) {
    if (!confirm("Delete this document and its chunks?")) return;
    try {
      await deleteDocument(id);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className="layout">
      <aside className="sidebar">
        <h1>DocuMind</h1>
        <p className="subtitle">Chat with your PDFs</p>

        <label className={`upload ${uploading ? "disabled" : ""}`}>
          {uploading ? "Processing PDF…" : "+ Upload PDF"}
          <input type="file" accept="application/pdf" onChange={onUpload} disabled={uploading} hidden />
        </label>

        {error && <div className="error">{error}</div>}

        <ul className="doc-list">
          {docs.map((d) => (
            <li key={d.id} className={d.id === selectedId ? "active" : ""}>
              <button className="doc" onClick={() => setSelectedId(d.id)}>
                <span className="doc-name">{d.filename}</span>
                <span className="doc-meta">{d.chunks} chunks</span>
              </button>
              <button className="delete" onClick={() => onDelete(d.id)} aria-label={`Delete ${d.filename}`}>
                ×
              </button>
            </li>
          ))}
        </ul>
        {docs.length === 0 && !error && <p className="hint">No documents yet. Upload a PDF to start.</p>}
      </aside>

      <section className="content">
        {selectedId !== null ? (
          <Chat key={selectedId} documentId={selectedId} />
        ) : (
          <div className="empty">Upload a PDF to start chatting.</div>
        )}
      </section>
    </main>
  );
}
