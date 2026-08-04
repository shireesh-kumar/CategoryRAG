from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from categoryrag.config import ALLOWED_EXTENSIONS, TEMP_ROOT, ensure_data_dirs
from categoryrag.database.db import get_session
from categoryrag.exceptions import NotFoundError, ValidationError
from categoryrag.models import Document, DocumentStatus, new_id, utc_now
from categoryrag.services.category_service import CategoryService, category_service


class DocumentService:
    def __init__(self, categories: CategoryService = category_service) -> None:
        self.categories = categories
        ensure_data_dirs()

    def list(self, category_id: str) -> list[Document]:
        if not self.categories.get(category_id):
            raise NotFoundError(
                "not_found",
                {"resource": "category", "id": category_id},
            )
        with get_session() as session:
            stmt = (
                select(Document)
                .where(Document.category_id == category_id)
                .order_by(Document.created_at)
            )
            return list(session.scalars(stmt).all())

    def get(self, document_id: str) -> Document | None:
        with get_session() as session:
            return session.get(Document, document_id)

    def upload_many(self, category_id: str, files: list[FileStorage]) -> list[Document]:
        if not self.categories.get(category_id):
            raise NotFoundError(
                "not_found",
                {"resource": "category", "id": category_id},
            )

        files = [f for f in files if f and f.filename]
        if not files:
            raise ValidationError(
                "validation_error",
                {"message": "Expected multipart form field 'file'"},
            )

        self._validate_file_types(files)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        batch_dir = TEMP_ROOT / f"tmp_{stamp}" / category_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        documents: list[Document] = []
        for file in files:
            documents.append(self._save_upload(category_id, file, batch_dir))

        from categoryrag.services.ingest import ingest_worker

        ingest_worker.enqueue_batch(
            category_id=category_id,
            document_ids=[document.id for document in documents],
            batch_dir=batch_dir,
        )
        return documents

    def _validate_file_types(self, files: list[FileStorage]) -> None:
        invalid: list[dict] = []
        for file in files:
            original = secure_filename(file.filename or "") or ""
            ext = Path(original).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                invalid.append({
                    "filename": file.filename,
                    "extension": ext or "(none)",
                })
        if invalid:
            raise ValidationError(
                "validation_error",
                {
                    "message": "Unsupported file type",
                    "allowed": sorted(ALLOWED_EXTENSIONS),
                    "invalid": invalid,
                },
            )

    def _save_upload(
        self,
        category_id: str,
        file: FileStorage,
        batch_dir: Path,
    ) -> Document:
        doc_id = new_id()
        original = secure_filename(file.filename) or "upload.bin"
        stored_name = f"{doc_id}_{original}"
        file.save(batch_dir / stored_name)

        now = utc_now()
        document = Document(
            id=doc_id,
            category_id=category_id,
            filename=original,
            stored_name=stored_name,
            status=DocumentStatus.PENDING.value,
            created_at=now,
            updated_at=now,
        )
        with get_session() as session:
            session.add(document)
            session.commit()
            session.refresh(document)
            return document

    def path_in_batch(self, document: Document, batch_dir: Path) -> Path:
        return batch_dir / document.stored_name

    def set_status(
        self,
        document_id: str,
        status: DocumentStatus,
        error: str | None = None,
    ) -> Document | None:
        with get_session() as session:
            document = session.get(Document, document_id)
            if not document:
                return None
            document.status = status.value
            document.error = error
            document.updated_at = utc_now()
            session.commit()
            session.refresh(document)
            return document

    def delete(self, category_id: str, document_id: str) -> None:
        document = self.get(document_id)
        if not document or document.category_id != category_id:
            raise NotFoundError(
                "not_found",
                {"resource": "document", "id": document_id},
            )

        from categoryrag.services.retriever_registry import retriever_registry

        retriever_registry.delete_document(category_id, document_id)

        with get_session() as session:
            document = session.get(Document, document_id)
            if not document or document.category_id != category_id:
                raise NotFoundError(
                    "not_found",
                    {"resource": "document", "id": document_id},
                )
            session.delete(document)
            session.commit()

    def delete_category_files(self, category_id: str) -> None:
        if not TEMP_ROOT.exists():
            return
        for batch_dir in TEMP_ROOT.glob("tmp_*"):
            category_dir = batch_dir / category_id
            if category_dir.exists():
                shutil.rmtree(category_dir, ignore_errors=True)


document_service = DocumentService()
