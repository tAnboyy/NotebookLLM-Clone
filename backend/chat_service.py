"""Chat persistence - save/load messages via Supabase messages table."""

from backend.db import supabase


def save_message(notebook_id: str, role: str, content: str) -> None:
    """Append a message to the messages table."""
    supabase.table("messages").insert({
        "notebook_id": notebook_id,
        "role": role,
        "content": content,
    }).execute()


def load_chat(notebook_id: str) -> list[dict]:
    """Load chat history. Returns [{role, content, created_at}, ...]."""
    result = (
        supabase.table("messages")
        .select("role, content, created_at")
        .eq("notebook_id", notebook_id)
        .order("created_at")
        .execute()
    )
    rows = result.data or []
    return [{"role": r["role"], "content": r["content"], "timestamp": r["created_at"]} for r in rows]
