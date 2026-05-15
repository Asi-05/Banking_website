"""src.services.budget_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS IST EIN BUDGET? ===
Ein Budget ist ein selbst gesetztes Ausgabenlimit fuer einen bestimmten Zeitraum.

Beispiel:
    User setzt Budget: CHF 500 fuer "Lebensmittel" im Mai 2026.
    → Wenn im Mai mehr als CHF 500 fuer Lebensmittel ausgegeben wird,
      ist das Budget "ueberschritten" (is_exceeded = True).

Ein Budget kann auch GLOBAL sein (category_id = None), dann gilt es fuer
alle Ausgaben zusammen (nicht nur eine Kategorie).

=== UPSERT - WAS IST DAS? ===
"Upsert" = UPDATE oder INSERT (je nachdem was gebraucht wird).

Da es pro (User + Monat + Jahr + Kategorie) nur EIN Budget geben darf,
prueft `set_budget` zuerst, ob schon eines existiert:
    - Existiert bereits eines → UPDATE (Limit aendern)
    - Existiert noch keines  → INSERT (neues Budget anlegen)

Das nennt man UPSERT-Pattern (Update + Insert).

=== WIE WIRD DER VERBRAUCH BERECHNET? ===
`check_budget_status` laedt alle Transaktionen des Users im betreffenden
Monat und summiert alle "expense"-Transaktionen auf.
WICHTIG: Nur Ausgaben (type="expense") zaehlen als Verbrauch.
Einnahmen (type="income") erhoehen NICHT den Budgetverbrauch.

=== ARCHITEKTUR-KETTE ===
    View (budget_view.py) → Controller (budget_controller.py)
    → **BudgetService (du bist hier)**
    → BudgetRepository (Budget laden/speichern)
    → TransactionRepository (Transaktionen fuer Verbrauchsberechnung)
    → UserRepository (User-Existenz pruefen)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `budget_service = BudgetService()`
"""

from __future__ import annotations

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.budget_repository import BudgetRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import Budget
from src.utils.validators import (
    validate_budget_month_year,
    validate_positive_amount,
)


class BudgetService:
    """Service fuer Budgetverwaltung und Budget-Verbrauchsberechnung."""

    def set_budget(self, payload: dict) -> Budget:
        """Legt ein Budget an oder aktualisiert ein bestehendes (UPSERT).

        AUFRUF-KETTE:
            budget_controller.set_budget(payload)
            → BudgetService.set_budget(payload)
            → validate_positive_amount(limit_amount)              [Betrag > 0?]
            → validate_budget_month_year(month, year)             [Gueltiger Monat/Jahr?]
            → UserRepository.get_by_id(user_id)                   [User existiert?]
            → BudgetRepository.get_by_scope(user_id, month, year, category_id)
              [Gibt es schon ein Budget fuer diesen Scope?]
            → ENTWEDER BudgetRepository.create(budget)            [Neues Budget]
            → ODER     BudgetRepository.save(existing)            [Bestehendes aktualisieren]

        RUECKGABE-KETTE:
            DB → BudgetRepository → BudgetService → budget_controller
            → View zeigt: "Budget gesetzt" / "Budget aktualisiert"

        PAYLOAD-KEYS (WAS WIRD ERWARTET?):
            - "user_id" (int/str)           → Pflichtfeld
            - "limit_amount" (float/str)    → Pflichtfeld, muss > 0 sein
            - "month" (int/str)             → Pflichtfeld, 1-12
            - "year" (int/str)              → Pflichtfeld, z.B. 2026
            - "category_id" (int/None)      → Optional, None = globales Budget

        WAS IST EIN "SCOPE"?
            Der Scope ist die eindeutige Kombination aus:
            (user_id, month, year, category_id)
            Pro Scope darf nur EIN Budget existieren (UniqueConstraint in DB).

        Args:
            payload: Dictionary aus UI/Controller.

        Returns:
            Das neu erstellte oder aktualisierte Budget-Objekt.

        Raises:
            ValueError: Wenn limit_amount <= 0 oder Monat/Jahr ungueltig.
            KeyError: Wenn der User nicht existiert.
        """
        user_id = int(payload["user_id"])
        limit_amount = float(payload["limit_amount"])
        month = int(payload["month"])
        year = int(payload["year"])
        # category_id kann None sein (globales Budget) oder eine int-ID
        category_id = payload.get("category_id")
        category_id = int(category_id) if category_id is not None else None

        # Validierungen: Betrag und Datum pruefen, bevor DB-Session geoeffnet wird.
        validate_positive_amount(limit_amount)
        validate_budget_month_year(month, year)

        with Session(engine) as session:
            user_repository = UserRepository(session)
            budget_repository = BudgetRepository(session)

            if user_repository.get_by_id(user_id) is None:
                raise KeyError(f"User {user_id} nicht gefunden")

            # UPSERT-Pruefung: Gibt es schon ein Budget fuer diesen Scope?
            existing = budget_repository.get_by_scope(
                user_id=user_id,
                month=month,
                year=year,
                category_id=category_id,
            )
            if existing is None:
                # Kein Budget vorhanden → Neues anlegen (INSERT).
                budget = Budget(
                    user_id=user_id,
                    limit_amount=limit_amount,
                    month=month,
                    year=year,
                    category_id=category_id,
                )
                return budget_repository.create(budget)

            # Budget schon vorhanden → Nur Limit aendern (UPDATE).
            existing.limit_amount = limit_amount
            return budget_repository.save(existing)

    def check_budget_status(
        self,
        user_id: int,
        month: int,
        year: int,
        category_id: int | None = None,
    ) -> dict:
        """Berechnet den aktuellen Budgetstatus (Verbrauch vs. Limit).

        AUFRUF-KETTE:
            budget_controller.check_budget_status(...)
            → BudgetService.check_budget_status(...)
            → BudgetRepository.get_by_scope(...)          [Budget laden]
            → TransactionRepository.list_for_month(...)   [Transaktionen des Monats laden]
            → sum() ueber expense-Transaktionen           [Verbrauch berechnen]

        RUECKGABE-KETTE:
            Berechnung → BudgetService → budget_controller
            → View zeigt: Fortschrittsbalken (Verbrauch/Limit), "Ueberschritten!"-Warnung

        WIE WIRD VERBRAUCH BERECHNET?
            Alle Transaktionen des Users in diesem Monat werden geladen.
            Dann werden alle "expense"-Transaktionen summiert.
            Einnahmen (income) werden IGNORIERT (sie erhoehen nicht den Verbrauch).

            Beispiel:
            Transaktionen Mai 2026:
            - CHF 120.00 Lebensmittel (expense)   → zaehlt
            - CHF 80.00  Transport (expense)       → zaehlt
            - CHF 2000.00 Gehalt (income)          → zaehlt NICHT
            current_spending = 120.00 + 80.00 = 200.00

        RUECKGABE-DICT:
            - "budget_id": ID des Budgets
            - "limit_amount": Das gesetzte Limit (z.B. 500.00)
            - "current_spending": Aktueller Verbrauch (z.B. 200.00)
            - "is_exceeded": True wenn current_spending > limit_amount
            - "month", "year", "category_id": Die gefragten Parameter

        Args:
            user_id: Besitzer des Budgets.
            month: Monat (1-12).
            year: Jahr.
            category_id: Optional: Nur Transaktionen dieser Kategorie zaehlen.
                         None = alle Ausgaben des Users zaehlen.

        Returns:
            Dictionary mit Budgetstatus-Informationen.

        Raises:
            ValueError: Wenn Monat oder Jahr ungueltig sind.
            KeyError: Wenn kein Budget fuer diesen Scope existiert.
        """
        validate_budget_month_year(month, year)

        with Session(engine) as session:
            budget_repository = BudgetRepository(session)
            transaction_repository = TransactionRepository(session)

            # Budget laden (muss fuer diesen Scope existieren).
            budget = budget_repository.get_by_scope(
                user_id=user_id,
                month=month,
                year=year,
                category_id=category_id,
            )
            if budget is None:
                raise KeyError("Budget nicht gefunden")

            # Alle Transaktionen des Users in diesem Monat laden.
            # `list_for_month` verwendet einen halboffenen Intervall [1. des Monats, 1. des Folge-Monats)
            # damit auch der letzte Monatstag korrekt erfasst wird.
            transactions = transaction_repository.list_for_month(
                user_id=user_id,
                month=month,
                year=year,
                category_id=category_id,
            )

            # Verbrauch = Summe aller Ausgaben (nur type="expense").
            # Einnahmen werden mit `if t.type == "expense"` herausgefiltert.
            current_spending = sum(
                t.amount for t in transactions if t.type == "expense"
            )

            return {
                "budget_id": budget.budget_id,
                "limit_amount": budget.limit_amount,
                "current_spending": current_spending,
                "is_exceeded": current_spending > budget.limit_amount,
                "month": month,
                "year": year,
                "category_id": category_id,
            }

    def list_budgets(self, user_id: int) -> list[Budget]:
        """Listet alle Budgets eines Users.

        AUFRUF-KETTE:
            budget_controller.list_budgets(user_id)
            → BudgetService.list_budgets(user_id)
            → BudgetRepository.list_by_user(user_id)
            → SQL: SELECT * FROM budgets WHERE user_id = :user_id

        RUECKGABE-KETTE:
            DB → BudgetRepository → BudgetService → budget_controller
            → View zeigt Tabelle mit allen Budgets

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            Liste von Budget-Objekten (kann leer sein).
        """
        with Session(engine) as session:
            budget_repository = BudgetRepository(session)
            return budget_repository.list_by_user(user_id)

    def update_budget(self, budget_id: int, limit_amount: float) -> Budget:
        """Aendert das Limit eines bestehenden Budgets.

        AUFRUF-KETTE:
            budget_controller.update_budget(budget_id, limit_amount)
            → BudgetService.update_budget(budget_id, limit_amount)
            → validate_positive_amount(limit_amount)
            → BudgetRepository.get_by_id(budget_id)
            → BudgetRepository.save(budget)
            → SQL: UPDATE budgets SET limit_amount=:amount WHERE budget_id=:id

        RUECKGABE-KETTE:
            DB → BudgetRepository → BudgetService → budget_controller
            → View zeigt: "Budget aktualisiert"

        UNTERSCHIED ZU set_budget():
            set_budget() kennt den Scope (User + Monat + Jahr + Kategorie) und
            findet das Budget selbst. update_budget() erhalt direkt die budget_id
            und aendert nur das Limit. Beide Methoden erreichen aehnliches,
            aber mit unterschiedlichen Eingaben.

        Args:
            budget_id: Datenbank-ID des Budgets.
            limit_amount: Neues Limit (muss > 0 sein).

        Returns:
            Aktualisiertes Budget-Objekt.

        Raises:
            ValueError: Wenn limit_amount <= 0.
            KeyError: Wenn kein Budget mit dieser ID existiert.
        """
        validate_positive_amount(limit_amount)

        with Session(engine) as session:
            budget_repository = BudgetRepository(session)
            budget = budget_repository.get_by_id(budget_id)
            if budget is None:
                raise KeyError(f"Budget {budget_id} nicht gefunden")

            budget.limit_amount = float(limit_amount)
            return budget_repository.save(budget)

    def delete_budget(self, budget_id: int) -> None:
        """Loescht ein Budget dauerhaft.

        AUFRUF-KETTE:
            budget_controller.delete_budget(budget_id)
            → BudgetService.delete_budget(budget_id)
            → BudgetRepository.get_by_id(budget_id)   [Existenz pruefen]
            → BudgetRepository.delete(budget_id)
            → SQL: DELETE FROM budgets WHERE budget_id = :budget_id

        RUECKGABE-KETTE:
            (kein Rueckgabewert) → budget_controller
            → View zeigt: "Budget geloescht"

        WARUM ERST LADEN, DANN LOESCHEN?
            Wir wollen eine aussagekraeftige Fehlermeldung, wenn das Budget
            nicht existiert. Das Repository hat zwar auch eine "safe delete"
            (passiert nichts wenn nicht gefunden), aber hier pruefen wir
            explizit damit der Controller eine KeyError abfangen kann.

        Args:
            budget_id: Datenbank-ID des zu loeschenden Budgets.

        Raises:
            KeyError: Wenn kein Budget mit dieser ID existiert.
        """
        with Session(engine) as session:
            budget_repository = BudgetRepository(session)
            budget = budget_repository.get_by_id(budget_id)
            if budget is None:
                raise KeyError(f"Budget {budget_id} nicht gefunden")
            budget_repository.delete(budget_id)


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.budget_service import budget_service`
budget_service = BudgetService()
