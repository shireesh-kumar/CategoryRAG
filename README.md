# CategoryRAG

Category-scoped document RAG with a Flask UI, PostgreSQL, MinIO, Qdrant, and Gemini embeddings.

## Setup

```bash
uv sync
cp .env.example .env
```

Set `GEMINI_API_KEY` and Auth0 vars in `.env` (see `.env.example`).

**Local:** `docker compose up -d` then `uv run categoryrag`.  
Open **http://localhost:5000** (must match `APP_BASE_URL` and Auth0 callback URLs — not `127.0.0.1`).

**Auth:** Auth0 Universal Login → `/callback` → httpOnly `cr_id_token` cookie (`SameSite=Strict`). Categories are scoped per user.

**Cloud:** Deploy with `ENV=production` and set service credentials as environment variables on the platform.

## Start dependencies (Docker)

```bash
docker compose up -d
```

This starts:

| Service | URL |
|---------|-----|
| PostgreSQL | `localhost:5432` |
| MinIO API | http://localhost:9000 |
| MinIO console | http://localhost:9001 (`minioadmin` / `minioadmin`) |
| Qdrant | http://localhost:6333 |

## Run

```bash
uv run categoryrag
```

Open: http://localhost:5000/login-page

## UI flow

1. Sign in with Auth0 (register or login)
2. Create a category
3. Select it in the sidebar
4. Upload `.txt`, `.pdf`, or `.docx` files
5. Watch status move `pending` → `processing` → `indexed` / `failed`
6. Search indexed content in that category
7. Sign out when done

## MCP server (Claude)

```bash
uv run categoryrag-mcp
```

MCP category tools are temporarily gated until API-key auth is added (browser cookies do not apply to MCP).
## Ingest flow

```text
upload → temp → DB (pending)
      → background:
           MinIO upload + save s3_key
           Qdrant embed/index
           status indexed | failed (+ error)
      → delete temp
```
