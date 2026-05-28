"""src.services.category_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der CategoryService stellt Kategorien bereit. Kategorien sind sogenannte
"Stammdaten": Sie werden einmalig beim App-Start in die Datenbank eingetragen
(via `seed.py`) und danach nur noch gelesen - nie geaendert oder geloescht.

Beispiele fuer Kategorien: "Lebensmittel", "Wohnen", "Freizeit", "Transport"

=== WARUM GIBT ES EINEN SERVICE FUER SO EINE SIMPLE AUFGABE? ===
Das MVC-Prinzip (Model-View-Controller) verbietet, dass die View (UI) oder
der Controller direkt auf Repositories oder die Datenbank zugreift.
Der Weg ist IMMER: View → Controller → Service → Repository → DB.
Der CategoryService ist die "Service-Schicht" fuer Kategorien, auch wenn er
aktuell nur eine Methode hat. Er koennte spaeter um "Kategorie anlegen" etc.
erweitert werden.

=== ARCHITEKTUR-KETTE ===
    View (z.B. Dropdown mit Kategorien) → Controller (category_controller.py)
    → **CategoryService (du bist hier)** → CategoryRepository → Datenbank

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `category_service = CategoryService()`
    Diese eine Instanz wird ueberall im Projekt importiert.
"""

from __future__ import annotations

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import Category


class CategoryService:
    """Service fuer Kategorie-Abfragen.

    Kategorien sind Stammdaten (read-only nach dem Seeding).
    Der Service delegiert alle Datenbankzugriffe an das CategoryRepository.
    """

    def list_categories(self) -> list[Category]:
        """Laedt alle verfuegbaren Kategorien aus der Datenbank.

        AUFRUF-KETTE:
            category_controller.list_categories()
            → CategoryService.list_categories()
            → CategoryRepository.list_all()
            → SQL: SELECT * FROM categories ORDER BY name ASC

        RUECKGABE-KETTE:
            DB → CategoryRepository → CategoryService → category_controller
            → category_controller gibt dict {id: name} zurueck (fuer Dropdowns)
            → View zeigt Dropdown mit Kategorien an

        WARUM KEIN FILTER?
            Kategorien sind global - jeder User sieht alle Kategorien.
            Es gibt keine user-spezifischen Kategorien in diesem System.

        Returns:
            Liste aller Category-Objekte, alphabetisch nach Name sortiert.
            Jedes Category-Objekt hat: category_id (int) und name (str).
        """
        with Session(engine) as session:
            # Datenbankzugriff liegt im Repository.
            # Der Service oeffnet die Session und schliesst sie nach der Abfrage.
            return CategoryRepository(session).list_all()


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.category_service import category_service`
category_service = CategoryService()
