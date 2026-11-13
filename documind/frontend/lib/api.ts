export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DocumentItem = {
  id: number;
  filename: string;
  created_at: string;
  chunks: number;
};

export type Source = {
  id: number;
  page: number;
  score: number;
  text: string;
};

export type ChatEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "token"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // body was not JSON
  }
  return `Request failed (${res.status})`;
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_URL}/documents`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function uploadDocument(file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res));
}

export async function deleteDocument(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/documents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await errorMessage(res));
}

/**
 * Calls /chat and yields events as they arrive.
 * The server sends one JSON object per line (NDJSON), so we read the response
 * body as a stream, split it on newlines and parse each complete line.
 */
export async function* streamChat(
  documentId: number,
  question: string,
  signal?: AbortSignal
): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, question }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(await errorMessage(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // last piece may be an incomplete line
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line) as ChatEvent;
    }
  }
  if (buffer.trim()) yield JSON.parse(buffer) as ChatEvent;
}
