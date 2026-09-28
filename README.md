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

**Auth:** Auth0 Universal Login → `/callback` → httpOnly `cr_id_token` cookie (`SameSite=Lax`). Categories are scoped per user. MCP checks an Auth0 access token; it does not use that cookie.

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

## MCP server

HTTP MCP. Auth0 issues the access token. This server only verifies it.

1. In Auth0, create an API whose identifier is `http://127.0.0.1:8000/mcp` and a Native app. Put that app's Client ID in `.cursor/mcp.json` as `auth.CLIENT_ID`.
2. On the Native app, allow callbacks `http://localhost:8787/callback` and `https://www.cursor.com/agents/mcp/oauth/callback`.
3. Start MCP: `uv run categoryrag-mcp` (listens on `http://127.0.0.1:8000/mcp`)
4. In Cursor, connect that URL and sign in when asked.

Tools: `list_categories`, `create_category`, `list_documents`, `search_category` (scoped to the signed-in user).

```bash
uv run categoryrag-mcp
```

## Ingest flow

```text
upload → temp → DB (pending)
      → background:
           MinIO upload + save s3_key
           Qdrant embed/index
           status indexed | failed (+ error)
      → delete temp
```
