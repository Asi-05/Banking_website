"""src.data_access.repositories.category_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS IST EINE KATEGORIE? ===
Kategorien sind Bezeichnungen, die jeder Transaktion und jedem Budget zugeordnet
werden. Beispiele: "Lebensmittel", "Miete", "Gehalt", "Freizeit".

Die Kategorien sind Stammdaten - sie aendern sich selten und werden beim ersten
Start der App durch `seed_database()` angelegt (in seed.py).

=== WAS MACHT DIESES REPOSITORY? ===
Einfaches Laden von Kategorien aus der Datenbank.

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank

    Aufgerufen von:
    - category_service.list_categories() → category_controller → Dropdown in Views
    - Diversen Services, die eine Kategorie per ID validieren muessen

=== WARUM KEINE SCHREIB-METHODEN? ===
In dieser App koennen Nutzer keine eigenen Kategorien anlegen. Die Kategorien
sind festgelegt und werden einmalig durch seed.py angelegt. Deshalb hat dieses
Repository nur Lese-Methoden.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Category


# Kapselt reine Datenbankzugriffe fuer Kategorien.
class CategoryRepository:
    """Datenbankzugriffe fuer `Category`-Objekte (nur Lesen).

    Wird von CategoryService und anderen Services genutzt, um
    verfuegbare Kategorien zu laden.
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        WOHER KOMMT DIE SESSION?
            Der Service oeffnet sie mit `with Session(engine) as session:`
            und uebergibt sie: `CategoryRepository(session)`

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        self.session = session

    def list_all(self) -> list[Category]:
        """Laedt alle verfuegbaren Kategorien aus der Datenbank.

        AUFRUF-KETTE:
            category_controller.list_categories()
            → category_service.list_categories()
            → CategoryRepository.list_all()
            → SQL: SELECT * FROM categories ORDER BY category_id

        WARUM SORTIERUNG NACH category_id?
            Damit die Reihenfolge in Dropdowns immer gleich ist (deterministisch).
            Ohne ORDER BY koennte die Datenbank die Zeilen in beliebiger Reihenfolge
            zurueckgeben (je nach internem Zustand).

        RUECKGABE:
            Liste von Category-Objekten. Jedes Objekt hat:
            .category_id: Ganzzahl (Primaerschluessel)
            .name: Text (z.B. "Lebensmittel")

        Returns:
            Liste aller Category-Objekte, sortiert nach category_id.
        """
        # select(Category) = "Hole alle Zeilen aus der categories-Tabelle"
        # .order_by(Category.category_id) = "Sortiere nach ID (aufsteigend)"
        statement = select(Category).order_by(Category.category_id)
        # .all() gibt alle Ergebnisse zurueck; list() macht eine normale Python-Liste
        return list(self.session.exec(statement).all())

    def get_by_id(self, category_id: int) -> Category | None:
        """Laedt eine einzelne Kategorie anhand ihrer ID.

        AUFRUF-KETTE:
            Diversen Services (z.B. beim Validieren ob eine Kategorie existiert)
            → CategoryRepository.get_by_id(category_id)
            → SQL: SELECT * FROM categories WHERE category_id = :category_id

        VERWENDUNG:
            Wird verwendet, wenn ein Service sicherstellen muss, dass die vom
            Nutzer ausgewaehlte Kategorie tatsaechlich in der Datenbank existiert.

        Args:
            category_id: Die ID der gesuchten Kategorie (Ganzzahl).

        Returns:
            Category-Objekt wenn gefunden, None wenn Kategorie nicht existiert.
        """
        # session.get() = direkter Lookup per Primaerschluessel (schnell, nutzt Cache)
        return self.session.get(Category, category_id)
