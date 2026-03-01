"""Artifacts - store references to generated reports, quizzes, podcasts, etc."""

from backend.db import supabase


def create_artifact(notebook_id: str, type: str, storage_path: str) -> dict | None:
    """Create artifact record. Returns {id, notebook_id, type, storage_path, created_at} or None."""
    try:
        result = supabase.table("artifacts").insert({
            "notebook_id": notebook_id,
            "type": type,
            "storage_path": storage_path,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def list_artifacts(notebook_id: str) -> list[dict]:
    """List artifacts for notebook. Returns [{id, type, storage_path, created_at}, ...]."""
    try:
        result = (
            supabase.table("artifacts")
            .select("id, type, storage_path, created_at")
            .eq("notebook_id", notebook_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []
