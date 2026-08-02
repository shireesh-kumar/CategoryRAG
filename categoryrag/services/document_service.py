from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from categoryrag.config import UPLOADS_DIR, ensure_data_dirs
from categoryrag.database.db import get_session
from categoryrag.models import Document, DocumentStatus, new_id, utc_now
from categoryrag.services.category_service import CategoryService, category_service


class DocumentService:
    def __init__(self, categories: CategoryService = category_service) -> None:
        self.categories = categories
        ensure_data_dirs()

    def list(self, category_id: str) -> list[Document]:
        if not self.categories.get(category_id):
            raise KeyError(f"Category not found: {category_id}")
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

    def upload(self, category_id: str, file: FileStorage) -> Document:
        if not self.categories.get(category_id):
            raise KeyError(f"Category not found: {category_id}")
        if not file or not file.filename:
            raise ValueError("No file provided")

        doc_id = new_id()
        original = secure_filename(file.filename) or "upload.bin"
        stored_name = f"{doc_id}_{original}"
        dest_dir = UPLOADS_DIR / category_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        file.save(dest_dir / stored_name)

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

    def path_for(self, document: Document) -> Path:
        return UPLOADS_DIR / document.category_id / document.stored_name

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

    def delete(self, category_id: str, document_id: str) -> bool:
        with get_session() as session:
            document = session.get(Document, document_id)
            if not document or document.category_id != category_id:
                return False

            path = self.path_for(document)
            if path.exists():
                path.unlink()

            session.delete(document)
            session.commit()
            return True

    def delete_category_files(self, category_id: str) -> None:
        category_dir = UPLOADS_DIR / category_id
        if category_dir.exists():
            shutil.rmtree(category_dir)


document_service = DocumentService()
