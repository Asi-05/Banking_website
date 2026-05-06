"""src.data_access.repositories.category_repository

Repository fuer Kategorie-Datenbankzugriffe (Data-Access-Schicht).

Kategorien werden in Transaktionen und Budgets referenziert und sind deshalb
eine zentrale Stammdaten-Tabelle. Services/Views nutzen dieses Repository,
um z. B. Dropdown-Optionen fuer die UI zu laden.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Category


# Kapselt reine Datenbankzugriffe fuer Kategorien.
class CategoryRepository:
    """Datenbankzugriffe fuer `Category`-Objekte."""
    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer DB-Session.

        Args:
            session: Offene SQLModel-Session.
        """
        self.session = session

    # Gibt alle Kategorien zurueck.
    def list_all(self) -> list[Category]:
        """Listet alle Kategorien in stabiler Reihenfolge.

        Returns:
            Liste aller Kategorien, sortiert nach `category_id`.
        """
        # Sortierung ist praktisch für UI-Dropdowns (immer gleiche Reihenfolge).
        statement = select(Category).order_by(Category.category_id)
        return list(self.session.exec(statement).all())

    # Laedt eine Kategorie per ID.
    def get_by_id(self, category_id: int) -> Category | None:
        """Lädt eine Kategorie anhand der Primärschlüssel-ID.

        Args:
            category_id: ID der Kategorie.

        Returns:
            Kategorie oder `None`.
        """
        return self.session.get(Category, category_id)
