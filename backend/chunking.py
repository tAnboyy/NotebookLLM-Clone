"""Shared chunking utilities for RAG ingestion."""

import re

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 80
MIN_CHUNK_SIZE = 100


def _split_into_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries (rough heuristic)."""
    text = re.sub(r"\n+", "\n", text.strip())
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text_semantic(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Semantic chunking: split on paragraphs first, then sentences.
    Preserves context better than blind character splits.
    """
    text = " ".join(text.split())
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 1:
        sentences = _split_into_sentences(text)
        if not sentences:
            sentences = [text]
        if len(sentences) == 1 and len(sentences[0]) > chunk_size * 2:
            return chunk_text_fallback(text, chunk_size, overlap)
        paragraphs = sentences

    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 1
        if current_len + para_len > chunk_size and current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= MIN_CHUNK_SIZE:
                chunks.append(chunk_text)
            overlap_len = 0
            overlap_items = []
            for item in reversed(current_chunk):
                if overlap_len + len(item) + 1 <= overlap:
                    overlap_items.insert(0, item)
                    overlap_len += len(item) + 1
                else:
                    break
            current_chunk = overlap_items
            current_len = overlap_len
        current_chunk.append(para)
        current_len += para_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


def chunk_text_fallback(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Character-based chunking when semantic splitting fails."""
    clean = " ".join(text.split())
    if not clean:
        return []
    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end])
        start += step
    return chunks
