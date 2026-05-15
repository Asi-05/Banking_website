"""src.ui.controllers.category_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS IST EINE KATEGORIE? ===
Kategorien sind Beschriftungen fuer Transaktionen. Beispiele: "Lebensmittel",
"Miete", "Gehalt", "Freizeit". Jede Transaktion muss einer Kategorie zugeordnet sein.

In der UI werden Kategorien als Dropdown-Liste angezeigt (z.B. beim Erstellen
einer Transaktion: "Waehlen Sie eine Kategorie...").

=== WAS MACHT DIESER CONTROLLER? ===
Er laedt alle Kategorien aus der Datenbank und gibt sie in einem Format zurueck,
das NiceGUI direkt als Dropdown-Optionen verwenden kann: ein Dictionary von
`category_id → name`.

    AUFRUF-KETTE:
    [1] View braucht Kategorie-Dropdown (z.B. transaction_view.py beim Laden)
    [2] view ruft category_controller.list_categories() auf
    [3] category_controller ruft category_service.list_categories() auf
    [4] category_service ruft category_repository.list_all() auf
    [5] Datenbank gibt alle Kategorien-Zeilen zurueck

    RUECKGABE:
    {1: "Lebensmittel", 2: "Miete", 3: "Gehalt", ...}

    NiceGUI nutzt dieses Dict direkt:
    ui.select(options=category_controller.list_categories())

=== WARUM DICT STATT LISTE? ===
NiceGUI's ui.select() kann ein Dictionary nehmen, wobei der Key der gespeicherte
Wert (category_id) und der Value der angezeigte Text (Name) ist.
Das ist praktischer als eine Liste, weil man dann direkt die ID speichern kann.
"""

from __future__ import annotations

from src.services.category_service import category_service


class CategoryController:
    """UI-Controller fuer Kategorien (Listen/Dropdown-Daten).

    Gibt Kategorien in einem fuer NiceGUI-Dropdowns optimierten Format zurueck.
    """

    def list_categories(self) -> dict:
        """Laedt alle Kategorien als Dictionary `category_id -> name`.

        AUFRUF-KETTE:
            Jede View die ein Kategorie-Dropdown zeigt (transaction_view, budget_view, ...)
            → list_categories()
            → category_service.list_categories()
            → category_repository.list_all() → Datenbank

        RUECKGABE (Beispiel):
            {
              1: "Lebensmittel",
              2: "Miete",
              3: "Gehalt",
              4: "Freizeit",
              ...
            }

        FEHLERBEHANDLUNG:
            Bei jedem Fehler (Datenbankfehler, etc.) wird ein leeres Dict {} zurueck-
            gegeben. Die View zeigt dann ein leeres Dropdown, aber keinen Absturz.
            Damit wird verhindert, dass ein Fehler bei Kategorien die ganze Seite
            unbrauchbar macht.

        Returns:
            Dictionary {category_id: name} fuer NiceGUI-Dropdowns; {} bei Fehlern.
        """
        try:
            # Alle Kategorie-Objekte aus der Datenbank laden
            categories = category_service.list_categories()
            # Umwandeln von Liste → Dictionary, damit NiceGUI es direkt nutzen kann
            # c.category_id wird der Key (gespeicherter Wert), c.name der angezeigte Text
            return {c.category_id: c.name for c in categories}
        except Exception:
            # Leeres Dict bei Fehler (kein Absturz, nur leeres Dropdown)
            return {}


# Singleton-Instanz: wird von vielen Views importiert (transaction, budget, card, ...).
category_controller = CategoryController()
