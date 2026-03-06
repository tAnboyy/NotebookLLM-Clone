"""Shared embedding service - 384-dim vectors for RAG (ingestion + retrieval)."""

import os

from sentence_transformers import SentenceTransformer

# all-MiniLM-L6-v2 (default) or BAAI/bge-small-en-v1.5 for better quality (both 384 dims)
_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_model = None

# BGE models: add prefix only to queries, not to documents
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _is_bge_model() -> bool:
    return "bge" in _MODEL_NAME.lower()


def encode(texts: list[str], task: str = "search_document") -> list[list[float]]:
    """
    Embed texts. Returns list of 384-dim vectors.

    Args:
        texts: List of strings to embed.
        task: "search_query" for queries, "search_document" for documents. BGE uses prefixes.
    """
    if not texts:
        return []

    model = _get_model()
    if _is_bge_model() and task == "search_query":
        texts = [_BGE_QUERY_PREFIX + t for t in texts]
    embeddings = model.encode(texts, show_progress_bar=False)
    return [e.tolist() for e in embeddings]
