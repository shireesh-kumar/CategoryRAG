from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from categoryrag.config import INGEST_WORKERS
from categoryrag.models import DocumentStatus
from categoryrag.services.document_service import DocumentService, document_service
from categoryrag.services.retriever_registry import RetrieverRegistry, retriever_registry
from categoryrag.services.s3_storage import S3Storage, get_s3_storage


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
            return

        self.documents.set_status(document_id, DocumentStatus.PROCESSING)
        try:
            file_path = self.documents.path_in_batch(document, batch_dir)
            if not file_path.exists():
                raise FileNotFoundError(f"Temp file missing: {file_path}")

            s3 = get_s3_storage()
            s3_key = S3Storage.object_key(category_id, document.id, document.filename)
            s3.upload_file(file_path, s3_key)
            self.documents.set_s3_key(document_id, s3_key)

            self.registry.ingest_document(
                category_id=category_id,
                document_id=document.id,
                filename=document.filename,
                stored_name=document.stored_name,
                file_path=file_path,
            )
            self.documents.set_status(document_id, DocumentStatus.INDEXED)
        except Exception as exc:
            self.documents.set_status(document_id, DocumentStatus.FAILED, error=str(exc))

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


ingest_worker = IngestWorker()
