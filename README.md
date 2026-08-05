# CategoryRAG

Category-scoped document RAG with a Flask admin API, SQLite metadata, Gemini embeddings, Qdrant, and S3.

## Setup

```bash
uv sync
cp .env.example .env
```

Fill in Gemini, Qdrant, and AWS/S3 values in `.env`.

### S3 bucket (Terraform)

```bash
cd infra
terraform init
terraform apply
```

Use outputs `bucket_name` and `aws_region` in `.env` as `S3_BUCKET` and `AWS_REGION`.

## Run

```bash
uv run categoryrag
```

API: `http://127.0.0.1:5000`

## Ingest flow

```text
upload → temp → DB (pending)
      → background:
           S3 upload + save s3_key
           Qdrant embed/index
           status indexed | failed (+ error)
      → delete temp
```
