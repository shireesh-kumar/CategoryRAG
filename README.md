# CategoryRAG

Category-scoped document RAG with a Flask UI, PostgreSQL, MinIO, Qdrant, and Gemini embeddings.

## Setup

```bash
uv sync
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`.

**Local:** `docker compose up -d` then `uv run categoryrag`. Docker endpoints are used automatically — you do not need Qdrant/S3/Postgres vars in `.env`.

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

Open: http://127.0.0.1:5000/dashboard

## UI flow

1. Create a category
2. Select it in the sidebar
3. Upload `.txt`, `.pdf`, or `.docx` files
4. Watch status move `pending` → `processing` → `indexed` / `failed`
5. Search indexed content in that category

## MCP server (Claude)

```bash
uv run categoryrag-mcp
```

Tools: `list_categories`, `create_category`, `list_documents`, `search_category`.

## Ingest flow

```text
upload → temp → DB (pending)
      → background:
           MinIO upload + save s3_key
           Qdrant embed/index
           status indexed | failed (+ error)
      → delete temp
```
