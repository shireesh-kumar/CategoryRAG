"""Background ingest: chunk → embed → store (stubbed for boilerplate)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

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

    def enqueue(self, document_id: str) -> None:
        self._executor.submit(self._run, document_id)

    def _run(self, document_id: str) -> None:
        document = self.documents.get(document_id)
        if not document:
            logger.warning("Ingest skipped; document missing: %s", document_id)
            return

        self.documents.set_status(document_id, DocumentStatus.PROCESSING)
        try:
            path = self.documents.path_for(document)
            # TODO: replace with real chunk → embed → upsert
            # For now we only register the category and mark success.
            self.registry.ensure_category(document.category_id)
            self.registry.ingest_document(
                category_id=document.category_id,
                document_id=document.id,
                file_path=path,
            )
            self.documents.set_status(document_id, DocumentStatus.INDEXED)
            logger.info("Indexed document %s in category %s", document_id, document.category_id)
        except Exception as exc:
            logger.exception("Ingest failed for %s", document_id)
            self.documents.set_status(document_id, DocumentStatus.FAILED, error=str(exc))

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


ingest_worker = IngestWorker()
