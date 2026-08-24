from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from categoryrag.config import INGEST_WORKERS
from categoryrag.models import Document, DocumentStatus
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

        already_failed = document.status == DocumentStatus.FAILED.value
        if not already_failed:
            self.documents.set_status(document_id, DocumentStatus.PROCESSING)

        s3_key: str | None = None
        embedded = False

        try:
            file_path = self.documents.path_in_batch(document, batch_dir)
            if not file_path.exists():
                raise FileNotFoundError(f"Internal error: Temp file missing: {file_path}")

            key = S3Storage.object_key(category_id, document.id, document.filename)
            get_s3_storage().upload_file(file_path, key)
            s3_key = key
            self.documents.set_s3_key(document_id, s3_key)

            # Unsupported / pre-failed docs: keep in S3, skip embedding.
            if already_failed:
                return

            self.registry.ingest_document(
                category_id=category_id,
                document_id=document.id,
                filename=document.filename,
                stored_name=document.stored_name,
                file_path=file_path,
            )
            embedded = True

            self.documents.set_status(document_id, DocumentStatus.INDEXED)
        except Exception as exc:
            if embedded:
                self.registry.delete_document(category_id, document_id)
            if s3_key and not already_failed:
                try:
                    get_s3_storage().delete_object(s3_key)
                except Exception:
                    pass
                self.documents.set_s3_key(document_id, None)

            if already_failed:
                # Keep the original unsupported-type error; note S3 failure if upload never completed.
                error = document.error or str(exc)
                if s3_key is None and document.error:
                    error = f"{document.error}; S3 upload failed: {exc}"
                self.documents.set_status(document_id, DocumentStatus.FAILED, error=error)
            else:
                self.documents.set_status(document_id, DocumentStatus.FAILED, error=str(exc))

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


ingest_worker = IngestWorker()
