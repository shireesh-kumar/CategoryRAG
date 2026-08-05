# CategoryRAG

Category-scoped document RAG with a Flask admin API, SQLite metadata, Gemini embeddings, and Qdrant.

## Setup

```bash
uv sync
cp .env.example .env
```

Fill in `GEMINI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY` in `.env`.

## Run

```bash
uv run categoryrag
```

API: `http://127.0.0.1:5000`
