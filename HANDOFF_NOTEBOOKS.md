# NotebookLM Clone - Handoff Document

## Stack

- **Auth:** Hugging Face OAuth (`gr.LoginButton`, `user_id` = HF username)
- **Metadata:** Supabase (notebooks, messages, artifacts)
- **Files:** Supabase Storage bucket `notebooklm`
- **Vectors:** Supabase pgvector (chunks table)

## Setup

### 1. Supabase

- Run `db/schema.sql` in SQL Editor
- Create Storage bucket: **Storage** → **New bucket** → name `notebooklm`, set public/private as needed
- Add RLS policies for the bucket if using private access

### 2. HF Space

- Add `hf_oauth: true` in README (already done)
- Add `SUPABASE_URL`, `SUPABASE_KEY` (service role) as Space secrets
- Optional: `SUPABASE_BUCKET` (default: notebooklm)

### 3. Local

- `HF_TOKEN` env var or `huggingface-cli login` (required for OAuth mock)
- `.env` with `SUPABASE_URL`, `SUPABASE_KEY`
- `pip install gradio[oauth]` (or `itsdangerous`) for LoginButton

## Storage (Supabase Storage)

```python
from backend.storage import get_sources_path, save_file, load_file

# Ingestion: save uploaded PDF
prefix = get_sources_path(user_id, notebook_id)  # "user_id/notebook_id/sources"
path = f"{prefix}/document.pdf"
save_file(path, file_bytes)

# Load
data = load_file(path)
```

Paths: `{user_id}/{notebook_id}/sources|embeddings|chats|artifacts}/{filename}`

## Notebook API

- `create_notebook(user_id, name)` 
- `list_notebooks(user_id)`
- `rename_notebook(user_id, notebook_id, new_name)`
- `delete_notebook(user_id, notebook_id)`

## Chat (Supabase messages table)

- `save_message(notebook_id, role, content)`
- `load_chat(notebook_id)`

## Embeddings (pgvector)

Table `chunks`: id, notebook_id, source_id, content, embedding vector(1536), metadata, created_at.

Ingestion team: embed chunks, insert into `chunks`, filter by `notebook_id` for retrieval.

---

## Handover: Ingestion & RAG Builders

### Where to Write Your Code

| Responsibility | File / Location | Purpose |
|----------------|-----------------|---------|
| **Ingestion**  | `backend/ingestion_service.py` (create this) | Parse uploaded files, chunk text, compute embeddings, insert into `chunks` |
| **RAG**        | `backend/rag_service.py` (create this)      | Embed query → similarity search → build context → call LLM → return answer |
| **Storage**    | `backend/storage.py` (existing)             | Save/load files in Supabase Storage; do not modify |
| **Chat**       | `backend/chat_service.py` (existing)        | Save/load messages; RAG calls `save_message` and `load_chat` |
| **UI**         | `app.py`                                   | Add upload component + chat interface; wire to ingestion and RAG |

---

### Ingestion Builder

**Write your code in:** `backend/ingestion_service.py`

**Flow:**
1. Receive: `user_id`, `notebook_id`, uploaded file bytes, and filename.
2. Save raw file via storage:
   ```python
   from backend.storage import get_sources_path, save_file
   prefix = get_sources_path(user_id, notebook_id)  # → "user_id/notebook_id/sources"
   path = f"{prefix}/{filename}"
   save_file(path, file_bytes)
   ```
3. Parse file (PDF, DOCX, TXT, etc.) and extract text.
4. Chunk text (e.g., 512–1024 tokens with overlap).
5. Compute embeddings (e.g., OpenAI `text-embedding-3-small` → 1536 dims, or compatible).
6. Insert rows into `chunks`:
   ```python
   supabase.table("chunks").insert({
       "notebook_id": notebook_id,
       "source_id": path,  # or your source identifier
       "content": chunk_text,
       "embedding": embedding_list,  # list of 1536 floats
       "metadata": {"page": 1, "chunk_idx": 0}  # optional
   }).execute()
   ```

**Integrate in app:**
- Add `gr.File` or `gr.Upload` in `app.py` for the selected notebook.
- On upload, call `ingest_file(user_id, notebook_id, file_bytes, filename)` from your new service.

**Existing helpers:** `backend/storage` (save_file, load_file, list_files, get_sources_path).

---

### RAG Builder

**Write your code in:** `backend/rag_service.py`

**Flow:**
1. Receive: `notebook_id`, user query.
2. Embed the query (same model/dims as ingestion, e.g. 1536).
3. Similarity search in `chunks`:
   ```python
   # Supabase pgvector example (cosine similarity)
   result = supabase.rpc(
       "match_chunks",
       {"query_embedding": embedding, "match_count": 5, "p_notebook_id": notebook_id}
   ).execute()
   ```
   - You must add a Supabase function `match_chunks` that filters by `notebook_id` and runs vector similarity (or use raw SQL).
   - Alternative: use `supabase.table("chunks").select("*").eq("notebook_id", notebook_id)` and do similarity in Python (less efficient).
4. Build context from top-k chunks.
5. Call LLM (Hugging Face Inference API, OpenAI, etc.) with context + history.
6. Persist messages via `chat_service`:
   ```python
   from backend.chat_service import save_message, load_chat
   save_message(notebook_id, "user", query)
   save_message(notebook_id, "assistant", answer)
   ```

**Integrate in app:**
- Add a chat block in `app.py` (Chatbot component) tied to `selected_notebook_id`.
- On submit: call `rag_chat(notebook_id, query, chat_history)` → returns assistant reply; update history using `load_chat(notebook_id)` or append locally.

**Existing helpers:** `backend/chat_service` (save_message, load_chat), `backend/db` (supabase).

---

### Schema Reference (for both)

```sql
-- chunks table (db/schema.sql)
chunks (
  id uuid,
  notebook_id uuid,
  source_id text,
  content text,
  embedding vector(1536),
  metadata jsonb,
  created_at timestamptz
)
```

**Required:** `embedding` must be 1536 dimensions (or update schema if using a different model).

---

### Suggested RPC for RAG (optional)

Add this in Supabase SQL Editor if you prefer server-side similarity:

```sql
create or replace function match_chunks(
  query_embedding vector(1536),
  match_count int,
  p_notebook_id uuid
)
returns table (id uuid, content text, metadata jsonb, similarity float)
language plpgsql as $$
begin
  return query
  select c.id, c.content, c.metadata,
         1 - (c.embedding <=> query_embedding) as similarity
  from chunks c
  where c.notebook_id = p_notebook_id
  order by c.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

Ingestion writes to `chunks`; RAG reads via `match_chunks` or equivalent.
