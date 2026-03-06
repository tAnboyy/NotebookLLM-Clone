"""Chat persistence - save/load messages via Supabase messages table."""

from backend.db import supabase


def _notebook_belongs_to_user(notebook_id: str, user_id: str | None) -> bool:
    """Verify the notebook is owned by the user. Returns False if user_id is None."""
    if not user_id or not notebook_id:
        return False
    try:
        result = (
            supabase.table("notebooks")
            .select("id")
            .eq("id", notebook_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return len(result.data or []) > 0
    except Exception:
        return False


def save_message(notebook_id: str, user_id: str | None, role: str, content: str) -> None:
    """Append a message only if the notebook belongs to the user."""
    if not _notebook_belongs_to_user(notebook_id, user_id):
        return
    supabase.table("messages").insert({
        "notebook_id": notebook_id,
        "role": role,
        "content": content,
    }).execute()


def load_chat(notebook_id: str, user_id: str | None) -> list[dict]:
    """Load chat history only if the notebook belongs to the user. Returns [] if not owned."""
    if not _notebook_belongs_to_user(notebook_id, user_id):
        return []
    result = (
        supabase.table("messages")
        .select("role, content, created_at")
        .eq("notebook_id", notebook_id)
        .order("created_at")
        .execute()
    )
    rows = result.data or []
    return [{"role": r["role"], "content": r["content"], "timestamp": r["created_at"]} for r in rows]
