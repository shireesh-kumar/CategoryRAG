from __future__ import annotations

from sqlalchemy import select

from categoryrag.database.db import get_session
from categoryrag.exceptions import NotFoundError, ValidationError
from categoryrag.models import Category, new_id, utc_now


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

        now = utc_now()
        category = Category(
            id=new_id(),
            name=name,
            description=description.strip(),
            created_at=now,
            updated_at=now,
        )
        with get_session() as session:
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    def delete(self, category_id: str) -> None:
        if not self.get(category_id):
            raise NotFoundError(
                "not_found",
                {"resource": "category", "id": category_id},
            )

        from categoryrag.services.document_service import document_service
        from categoryrag.services.retriever_registry import retriever_registry

        document_service.delete_category_files(category_id)
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


category_service = CategoryService()
