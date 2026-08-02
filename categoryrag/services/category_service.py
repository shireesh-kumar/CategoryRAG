from __future__ import annotations

from sqlalchemy import select

from categoryrag.database.db import get_session
from categoryrag.models import Category, new_id, utc_now


class CategoryService:
    def list(self) -> list[Category]:
        with get_session() as session:
            return list(session.scalars(select(Category).order_by(Category.created_at)).all())

    def get(self, category_id: str) -> Category | None:
        with get_session() as session:
            return session.get(Category, category_id)

    def create(self, name: str, description: str = "") -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Category name is required")

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

    def delete(self, category_id: str) -> bool:
        with get_session() as session:
            category = session.get(Category, category_id)
            if not category:
                return False
            session.delete(category)
            session.commit()
            return True


category_service = CategoryService()
