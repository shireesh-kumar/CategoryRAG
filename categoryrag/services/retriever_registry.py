from __future__ import annotations

import logging
from pathlib import Path

from categoryrag.config import INDEXES_DIR, ensure_data_dirs

logger = logging.getLogger(__name__)


class RetrieverRegistry:
    def __init__(self) -> None:
        ensure_data_dirs()
        self._ready: set[str] = set()

    def ensure_category(self, category_id: str) -> None:
        index_dir = INDEXES_DIR / category_id
        index_dir.mkdir(parents=True, exist_ok=True)
        self._ready.add(category_id)

    def ingest_document(self, category_id: str, document_id: str, file_path: Path) -> None:
        self.ensure_category(category_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Missing upload: {file_path}")
        marker = INDEXES_DIR / category_id / f"{document_id}.stub"
        marker.write_text(f"source={file_path.name}\n", encoding="utf-8")
        logger.info("Stub-indexed %s for category %s", document_id, category_id)

    def delete_document(self, category_id: str, document_id: str) -> None:
        marker = INDEXES_DIR / category_id / f"{document_id}.stub"
        if marker.exists():
            marker.unlink()

    def delete_category(self, category_id: str) -> None:
        index_dir = INDEXES_DIR / category_id
        if index_dir.exists():
            for path in index_dir.iterdir():
                path.unlink()
            index_dir.rmdir()
        self._ready.discard(category_id)

    def search(self, category_id: str, query: str, top_k: int = 5) -> list[dict]:
        if category_id not in self._ready:
            self.ensure_category(category_id)
        logger.debug("Stub search category=%s query=%r top_k=%s", category_id, query, top_k)
        return []

retriever_registry = RetrieverRegistry()
