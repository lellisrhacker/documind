"""Split page text into overlapping chunks.

Why chunk? An LLM prompt has limited space, and one embedding for a whole PDF
would be too vague. Small chunks give precise search matches.

Why overlap? A sentence may fall on the boundary of two chunks. Sharing some
text between neighbours keeps that sentence whole in at least one chunk.
"""


def chunk_text(text: str, size: int = 1000, overlap: int = 200) -> list[str]:
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    text = " ".join(text.split())  # collapse newlines and repeated spaces
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # try not to cut a word in half: step back to the last space
            space = text.rfind(" ", start + size // 2, end)
            if space != -1:
                end = space
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        next_start = max(end - overlap, start + 1)  # always move forward
        # the overlap point may land inside a word: move to the start of the next word
        if text[next_start - 1] != " ":
            space = text.find(" ", next_start)
            next_start = space + 1 if space != -1 else end
        start = min(next_start, end)  # never skip text
    return chunks
