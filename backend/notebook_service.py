"""Notebook CRUD service - spec-aligned API, Supabase + storage."""

import logging
from datetime import datetime, timezone

from backend.db import supabase
from backend.storage import ensure_notebook_dirs

log = logging.getLogger(__name__)


def _to_spec(row: dict) -> dict:
    """Map DB row to spec format."""
    return {
        "notebook_id": str(row["id"]),
        "name": row["name"],
        "created_at": row.get("created_at"),
    }


def create_notebook(user_id: str, name: str = "Untitled Notebook") -> dict | None:
    """Create notebook. Returns {notebook_id, name, created_at} or None on error."""
    try:
        data = {"user_id": user_id, "name": name}
        result = supabase.table("notebooks").insert(data).execute()
        rows = result.data
        if not rows:
            return None
        row = rows[0]
        nb_id = str(row["id"])
        ensure_notebook_dirs(user_id, nb_id)
        return _to_spec(row)
    except Exception as e:
        log.exception("create_notebook failed")
        return None


def list_notebooks(user_id: str) -> list[dict]:
    """List notebooks for user. Returns [{notebook_id, name, created_at}, ...]."""
    try:
        result = (
            supabase.table("notebooks")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [_to_spec(r) for r in (result.data or [])]
    except Exception as e:
        log.exception("list_notebooks failed")
        return []


def rename_notebook(user_id: str, notebook_id: str, new_name: str) -> bool:
    """Rename notebook. Returns success."""
    try:
        result = (
            supabase.table("notebooks")
            .update({"name": new_name, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", notebook_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(result.data or []) > 0
    except Exception:
        return False


def delete_notebook(user_id: str, notebook_id: str) -> bool:
    """Delete notebook. Returns success."""
    try:
        supabase.table("notebooks").delete().eq("id", notebook_id).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False
