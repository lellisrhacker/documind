"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Source, streamChat } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
  error?: string;
};

export default function Chat({ documentId }: { documentId: number }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // stop any running answer when the user switches document or leaves the page
  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function updateLast(change: (m: Message) => Message) {
    setMessages((prev) => {
      const copy = [...prev];
      copy[copy.length - 1] = change(copy[copy.length - 1]);
      return copy;
    });
  }

  async function ask(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;

    setInput("");
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", text: question },
      { role: "assistant", text: "" },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      for await (const event of streamChat(documentId, question, controller.signal)) {
        if (event.type === "sources") {
          updateLast((m) => ({ ...m, sources: event.sources }));
        } else if (event.type === "token") {
          updateLast((m) => ({ ...m, text: m.text + event.text }));
        } else if (event.type === "error") {
          updateLast((m) => ({ ...m, error: event.message }));
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        updateLast((m) => ({ ...m, error: (err as Error).message }));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <p className="hint">Ask anything about this document. Answers cite the pages they came from.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <div className="text">
              {m.text || (m.role === "assistant" && !m.error ? "Thinking…" : "")}
            </div>
            {m.error && <div className="error">{m.error}</div>}
            {m.sources && m.sources.length > 0 && m.text && (
              <details className="sources">
                <summary>Sources ({m.sources.length})</summary>
                {m.sources.map((s) => (
                  <div key={s.id} className="source">
                    <div className="source-head">
                      [{s.id}] Page {s.page} · match {(s.score * 100).toFixed(0)}%
                    </div>
                    <div className="source-text">{s.text}</div>
                  </div>
                ))}
              </details>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form className="composer" onSubmit={ask}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this PDF…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
