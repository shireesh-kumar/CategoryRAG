from __future__ import annotations

import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from categoryrag.config import INGEST_WORKERS
from categoryrag.models import Document, DocumentStatus
from categoryrag.services.document_service import DocumentService, document_service
from categoryrag.services.retriever_registry import RetrieverRegistry, retriever_registry
from categoryrag.services.s3_storage import S3Storage, get_s3_storage

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
        documents: list[Document],
        batch_dir: Path,
    ) -> None:
        self._executor.submit(self._run_batch, category_id, documents, batch_dir)

    def _run_batch(
        self,
        category_id: str,
        documents: list[Document],
        batch_dir: Path,
    ) -> None:
        try:
            for document in documents:
                self._ingest_one(category_id, document.id, batch_dir)
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

        file_path = self.documents.path_in_batch(document, batch_dir)
        if not file_path.exists():
            self.documents.set_status(
                document_id,
                DocumentStatus.FAILED,
                error=f"Internal error: Temp file missing: {file_path}",
            )
            return

        if document.status == DocumentStatus.FAILED.value:
            self._store_pre_failed_in_s3(category_id, document_id, document, file_path)
            return

        self.documents.set_status(document_id, DocumentStatus.PROCESSING)

        errors: list[str] = []

        inject_error = self._run_injection(category_id, document, file_path)
        if inject_error:
            errors.append(inject_error)

        s3_error = self._store_in_s3(category_id, document_id, document, file_path)
        if s3_error:
            errors.append(s3_error)

        if errors:
            if inject_error is None:
                self.registry.delete_document(category_id, document_id)
            self.documents.set_status(
                document_id,
                DocumentStatus.FAILED,
                error="; ".join(errors),
            )
            return

        self.documents.set_status(document_id, DocumentStatus.INDEXED)

    def _run_injection(
        self,
        category_id: str,
        document: Document,
        file_path: Path,
    ) -> str | None:
        try:
            self.registry.ingest_document(
                category_id=category_id,
                document_id=document.id,
                filename=document.filename,
                stored_name=document.stored_name,
                file_path=file_path,
            )
            return None
        except Exception as exc:
            logger.exception(
                "Ingest failed for document %s (%s)",
                document.id,
                document.filename,
            )
            return f"Ingest failed: {exc}"

    def _store_in_s3(
        self,
        category_id: str,
        document_id: str,
        document: Document,
        file_path: Path,
    ) -> str | None:
        try:
            key = S3Storage.object_key(category_id, document.id, document.filename)
            get_s3_storage().upload_file(file_path, key)
            self.documents.set_s3_key(document_id, key)
            return None
        except Exception as exc:
            logger.exception(
                "S3 upload failed for document %s (%s)",
                document.id,
                document.filename,
            )
            return f"S3 upload failed: {exc}"

    def _store_pre_failed_in_s3(
        self,
        category_id: str,
        document_id: str,
        document: Document,
        file_path: Path,
    ) -> None:
        try:
            key = S3Storage.object_key(category_id, document.id, document.filename)
            get_s3_storage().upload_file(file_path, key)
            self.documents.set_s3_key(document_id, key)
        except Exception as exc:
            logger.exception(
                "S3 upload failed for pre-failed document %s (%s)",
                document.id,
                document.filename,
            )
            original_error = document.error or "Upload rejected"
            self.documents.set_status(
                document_id,
                DocumentStatus.FAILED,
                error=f"{original_error}; S3 upload failed: {exc}",
            )

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


ingest_worker = IngestWorker()
