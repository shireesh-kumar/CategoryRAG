from __future__ import annotations

import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from categoryrag.config import INGEST_WORKERS
from categoryrag.models import DocumentStatus
from categoryrag.services.document_service import DocumentService, document_service
from categoryrag.services.retriever_registry import RetrieverRegistry, retriever_registry

logger = logging.getLogger(__name__)


class IngestWorker:
    def __init__(
        self,
        documents: DocumentService = document_service,
        registry: RetrieverRegistry = retriever_registry,
        max_workers: int = INGEST_WORKERS,
    ) -> None:
        self.documents = documents
        self.registry = registry
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ingest")

    def enqueue_batch(
        self,
        category_id: str,
        document_ids: list[str],
        batch_dir: Path,
    ) -> None:
        self._executor.submit(self._run_batch, category_id, document_ids, batch_dir)

    def _run_batch(
        self,
        category_id: str,
        document_ids: list[str],
        batch_dir: Path,
    ) -> None:
        try:
            for document_id in document_ids:
                self._ingest_one(category_id, document_id, batch_dir)
        finally:
            if batch_dir.exists():
                shutil.rmtree(batch_dir, ignore_errors=True)
    def _ingest_one(
        self,
        category_id: str,
        document_id: str,
        batch_dir: Path,
    ) -> None:
        document = self.documents.get(document_id)
        if not document:
            logger.warning("Ingest skipped; document missing: %s", document_id)
            return

        self.documents.set_status(document_id, DocumentStatus.PROCESSING)
        try:
            file_path = self.documents.path_in_batch(document, batch_dir)
            if not file_path.exists():
                raise FileNotFoundError(f"Temp file missing: {file_path}")

            chunk_count = self.registry.ingest_document(
                category_id=category_id,
                document_id=document.id,
                filename=document.filename,
                stored_name=document.stored_name,
                file_path=file_path,
            )
            self.documents.set_status(document_id, DocumentStatus.INDEXED)
            logger.info(
                "Indexed document %s (%s chunks) in category %s",
                document_id,
                chunk_count,
                category_id,
            )
        except Exception as exc:
            logger.exception("Ingest failed for %s", document_id)
            self.documents.set_status(document_id, DocumentStatus.FAILED, error=str(exc))

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


ingest_worker = IngestWorker()
