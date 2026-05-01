from __future__ import annotations

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import Category


class CategoryService:
    def list_categories(self) -> list[Category]:
        with Session(engine) as session:
            return CategoryRepository(session).list_all()


category_service = CategoryService()
