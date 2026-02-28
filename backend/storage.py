"""
Storage layer - Supabase Storage for files.
Path structure: {user_id}/{notebook_id}/sources/, embeddings/, chats/, artifacts/
"""

import os
from pathlib import Path

from backend.db import supabase

BUCKET = os.getenv("SUPABASE_BUCKET", "notebooklm")


def _validate_segment(s: str) -> bool:
    """Reject path traversal and invalid chars."""
    if not s or ".." in s or "/" in s or "\\" in s:
        return False
    return True


def _base_path(user_id: str, notebook_id: str) -> str:
    """Return base path for notebook. Raises on invalid input."""
    if not _validate_segment(user_id) or not _validate_segment(notebook_id):
        raise ValueError("Invalid user_id or notebook_id (path safety)")
    return f"{user_id}/{notebook_id}"


def get_sources_path(user_id: str, notebook_id: str) -> str:
    """Path prefix for notebook sources. Ingestion saves uploads here."""
    return f"{_base_path(user_id, notebook_id)}/sources"


def get_embeddings_path(user_id: str, notebook_id: str) -> str:
    """Path prefix for embeddings."""
    return f"{_base_path(user_id, notebook_id)}/embeddings"


def get_chats_path(user_id: str, notebook_id: str) -> str:
    """Path prefix for chat files."""
    return f"{_base_path(user_id, notebook_id)}/chats"


def get_artifacts_path(user_id: str, notebook_id: str) -> str:
    """Path prefix for artifacts."""
    return f"{_base_path(user_id, notebook_id)}/artifacts"


def ensure_notebook_dirs(user_id: str, notebook_id: str) -> None:
    """No-op for Supabase Storage - paths are created on first upload."""
    _base_path(user_id, notebook_id)


def save_file(storage_path: str, content: bytes | str) -> None:
    """Save content to Supabase Storage. Path must be within bucket (no leading /)."""
    if ".." in storage_path or storage_path.startswith("/"):
        raise ValueError("Invalid storage path")
    data = content.encode("utf-8") if isinstance(content, str) else content
    supabase.storage.from_(BUCKET).upload(
        path=storage_path,
        file=data,
        file_options={"upsert": "true"},
    )


def load_file(storage_path: str) -> bytes:
    """Load file from Supabase Storage. Returns bytes."""
    if ".." in storage_path or storage_path.startswith("/"):
        raise ValueError("Invalid storage path")
    return supabase.storage.from_(BUCKET).download(storage_path)


def list_files(prefix: str) -> list[str]:
    """List file paths under prefix."""
    try:
        result = supabase.storage.from_(BUCKET).list(prefix.rstrip("/"))
        paths = []
        for item in result:
            name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
            if not name or name == ".emptyFolderPlaceholder":
                continue
            path = f"{prefix.rstrip('/')}/{name}"
            if isinstance(item, dict) and item.get("id") is None:  # folder
                paths.extend(list_files(path + "/"))
            else:
                paths.append(path)
        return paths
    except Exception:
        return []
