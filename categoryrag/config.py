from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "database"
TEMP_ROOT = Path(tempfile.gettempdir()) / "categoryrag"
UPLOADS_DIR = TEMP_ROOT

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}
INGEST_WORKERS = 2

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

# Local dev always uses Docker Compose — ignore these in .env when not in production.
_DOCKER_DEFAULTS: dict[str, str] = {
    "DATABASE_URL": "postgresql+psycopg://categoryrag:categoryrag@localhost:5432/categoryrag",
    "QDRANT_URL": "http://localhost:6333",
    "QDRANT_API_KEY": "",
    "S3_BUCKET": "categoryrag-local",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "AWS_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "minioadmin",
    "AWS_SECRET_ACCESS_KEY": "minioadmin",
}


def _is_production() -> bool:
    if os.getenv("CATEGORYRAG_ENV") == "production":
        return True
    if os.getenv("FLASK_ENV") == "production":
        return True
    if os.getenv("ENV") == "production":
        return True
    if os.getenv("K_SERVICE"):
        return True
    if os.getenv("AWS_EXECUTION_ENV"):
        return True
    if os.getenv("WEBSITE_SITE_NAME"):
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") == "production":
        return True
    if os.getenv("RENDER"):
        return True
    return False


IS_PRODUCTION = _is_production()


def _env(name: str) -> str:
    if not IS_PRODUCTION and name in _DOCKER_DEFAULTS:
        return _DOCKER_DEFAULTS[name]
    if name in os.environ:
        return os.environ[name]
    return ""


GEMINI_API_KEY = _env("GEMINI_API_KEY")
DATABASE_URL = _env("DATABASE_URL")
QDRANT_URL = _env("QDRANT_URL")
QDRANT_API_KEY = _env("QDRANT_API_KEY")
AWS_REGION = _env("AWS_REGION")
S3_BUCKET = _env("S3_BUCKET")
S3_ENDPOINT_URL = _env("S3_ENDPOINT_URL")
AWS_ACCESS_KEY_ID = _env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _env("AWS_SECRET_ACCESS_KEY")


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
