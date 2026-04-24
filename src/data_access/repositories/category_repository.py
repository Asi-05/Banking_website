from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Category


# Kapselt reine Datenbankzugriffe fuer Kategorien.
class CategoryRepository:
    def __init__(self, session: Session):
        self.session = session

    # Gibt alle Kategorien zurueck.
    def list_all(self) -> list[Category]:
        statement = select(Category).order_by(Category.category_id)
        return list(self.session.exec(statement).all())

    # Laedt eine Kategorie per ID.
    def get_by_id(self, category_id: int) -> Category | None:
        return self.session.get(Category, category_id)
