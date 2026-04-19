from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Category


# Kapselt reine Datenbankzugriffe fuer Kategorien.
class CategoryRepository:
    # Gibt alle Kategorien zurueck.
    @staticmethod
    def list_all(session: Session) -> list[Category]:
        statement = select(Category).order_by(Category.category_id)
        return list(session.exec(statement).all())

    # Laedt eine Kategorie per ID.
    @staticmethod
    def get_by_id(session: Session, category_id: int) -> Category | None:
        return session.get(Category, category_id)
