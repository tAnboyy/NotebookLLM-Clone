"""Retrieval service - vector similarity search for RAG with optional reranking."""

import os

from backend.db import supabase
from backend.embedding_service import encode

# Retrieve more candidates for reranking; final count after rerank/filter
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "12"))
FINAL_TOP_K = int(os.getenv("FINAL_TOP_K", "5"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.2"))
USE_RERANKER = os.getenv("USE_RERANKER", "true").lower() in ("true", "1", "yes")

_reranker = None


def _get_reranker():
    """Lazy-load cross-encoder reranker."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")
        except Exception:
            _reranker = False  # Disabled on failure
    return _reranker if _reranker else None


def _rerank_chunks(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    """Rerank chunks using cross-encoder; return top_k."""
    model = _get_reranker()
    if not model or not chunks:
        return chunks[:top_k]

    pairs = [(query, c["content"]) for c in chunks]
    scores = model.predict(pairs)
    scored = list(zip(chunks, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    reranked = [c for c, _ in scored[:top_k]]
    return reranked


def retrieve_chunks(notebook_id: str, query: str, top_k: int = None) -> list[dict]:
    """
    Retrieve top-k chunks for a query, filtered by notebook_id.
    Uses two-stage retrieval: vector search -> optional rerank -> similarity filter.

    Returns list of dicts with keys: id, content, metadata, similarity.
    """
    if not query or not query.strip():
        return []

    top_k = top_k or FINAL_TOP_K
    query_clean = query.strip()

    query_embedding = encode([query_clean], task="search_query")[0]

    try:
        result = supabase.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": RETRIEVE_TOP_K,
                "p_notebook_id": notebook_id,
            },
        ).execute()

        rows = result.data or []
        chunks = [
            {
                "id": str(r["id"]),
                "content": r["content"],
                "metadata": r.get("metadata") or {},
                "similarity": float(r.get("similarity", 0)),
            }
            for r in rows
        ]

        # Filter by similarity threshold
        chunks = [c for c in chunks if c["similarity"] >= SIMILARITY_THRESHOLD]

        # Rerank for better precision
        if USE_RERANKER and len(chunks) > top_k:
            chunks = _rerank_chunks(query_clean, chunks, top_k)
        else:
            chunks = chunks[:top_k]

        return chunks
    except Exception:
        return []
