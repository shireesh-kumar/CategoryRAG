from __future__ import annotations

from sqlalchemy import select

from categoryrag.database.db import get_session
from categoryrag.exceptions import NotFoundError, ValidationError
from categoryrag.models import Category, new_id, utc_now
from categoryrag.services.s3_storage import S3Storage


class CategoryService:
    def list(self) -> list[Category]:
        with get_session() as session:
            return list(session.scalars(select(Category).order_by(Category.created_at)).all())

    def get(self, category_id: str) -> Category | None:
        with get_session() as session:
            return session.get(Category, category_id)

    def get_detail(self, category_id: str) -> dict:
        category = self.get(category_id)
        if not category:
            raise NotFoundError(
                "not_found",
                {"resource": "category", "id": category_id},
            )

        from categoryrag.services.document_service import document_service

        documents = document_service.list(category_id)
        return {
            "category": category.to_dict(),
            "documents": [d.to_dict() for d in documents],
        }

    def create(self, name: str, description: str = "") -> Category:
        name = name.strip()
        if not name:
            raise ValidationError(
                "validation_error",
                {"message": "Category name is required"},
            )

        category_id = new_id()
        now = utc_now()
        category = Category(
            id=category_id,
            name=name,
            description=description.strip(),
            s3_prefix=S3Storage.category_prefix(category_id),
            created_at=now,
            updated_at=now,
        )
        with get_session() as session:
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    def delete(self, category_id: str) -> None:
        category = self.get(category_id)
        if not category:
            raise NotFoundError(
                "not_found",
                {"resource": "category", "id": category_id},
            )

        from categoryrag.services.document_service import document_service
        from categoryrag.services.retriever_registry import retriever_registry

        document_service.delete_category_storage(
            category_id,
            s3_prefix=category.s3_prefix or S3Storage.category_prefix(category_id),
        )
        retriever_registry.delete_category(category_id)

        with get_session() as session:
            category = session.get(Category, category_id)
            if not category:
                raise NotFoundError(
                    "not_found",
                    {"resource": "category", "id": category_id},
                )
            session.delete(category)
            session.commit()

    def search(self, category_id: str, query: str, top_k: int = 5) -> list[dict]:
        if not self.get(category_id):
            raise NotFoundError(
                "not_found",
                {"resource": "category", "id": category_id},
            )
        query = query.strip()
        if not query:
            raise ValidationError(
                "validation_error",
                {"message": "query is required"},
            )
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            raise ValidationError(
                "validation_error",
                {"message": "top_k must be an integer"},
            )
        if top_k < 1:
            raise ValidationError(
                "validation_error",
                {"message": "top_k must be at least 1"},
            )

        from categoryrag.services.retriever_registry import retriever_registry

        return retriever_registry.search(category_id, query, top_k=top_k)


category_service = CategoryService()
