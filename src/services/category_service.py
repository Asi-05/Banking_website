"""Kategorie-Funktionen (Service-Schicht).

Dieses Modul stellt Service-Methoden für Kategorien bereit.
Es gehört zur Service-Schicht, weil Controller/UI nicht direkt SQL/Repositories
nutzen sollen. Intern delegiert der Service an `CategoryRepository`.
"""

from __future__ import annotations

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import Category


class CategoryService:
    def list_categories(self) -> list[Category]:
        """Listet alle Kategorien (Stammdaten).

        Returns:
            Liste aller Kategorien aus der DB.
        """
        with Session(engine) as session:
            # Reiner DB-Zugriff steckt im Repository.
            return CategoryRepository(session).list_all()


category_service = CategoryService()
