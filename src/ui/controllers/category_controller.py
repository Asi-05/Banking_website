"""src.ui.controllers.category_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Kategorien werden in der UI meist als Dropdown angezeigt. Dieser Controller
liefert daher eine einfache Struktur (Mapping von ID -> Name), die in Views
direkt verwendbar ist.
"""

from __future__ import annotations

from src.services.category_service import category_service


class CategoryController:
    """UI-Controller fuer Kategorien (Listen/Dropdown-Daten)."""

    def list_categories(self) -> dict:
        """Listet alle Kategorien als Mapping `category_id -> name`.

        Die Views brauchen Kategorien oft als Dropdown-Optionen. Ein Dict ist fuer
        NiceGUI praktisch, weil `ui.select(options=...)` direkt damit arbeiten kann.

        Returns:
            Ein Dict fuer UI-Komponenten.
            Bei Fehlern: ein leeres Dict.

        Raises:
            Keine. Fehler werden abgefangen und als leeres Dict abgebildet.
        """
        try:
            categories = category_service.list_categories()
            return {c.category_id: c.name for c in categories}
        except Exception:
            return {}


category_controller = CategoryController()
