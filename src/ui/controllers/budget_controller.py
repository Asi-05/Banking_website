"""src.ui.controllers.budget_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS IST EIN BUDGET IN DIESER APP? ===
Ein Budget ist ein monatliches Ausgabenlimit. Der Nutzer kann sagen:
"Ich moechte im Mai 2026 nicht mehr als CHF 500 ausgeben" (globales Budget)
oder: "Ich moechte fuer Lebensmittel im Mai maximal CHF 200 ausgeben" (pro Kategorie).

Der BudgetController verbindet die budget_view.py (was der Nutzer sieht)
mit dem BudgetService (der die Regeln kennt und in die Datenbank schreibt).

=== AUFRUF-KETTE (Beispiel: Budget setzen) ===
    [1] Nutzer gibt Limit ein und klickt "Budget setzen" in budget_view.py
    [2] budget_view.py ruft budget_controller.set_budget(payload) auf
    [3] budget_controller ruft budget_service.set_budget(payload) auf
    [4] budget_service prueft Regeln (Monat/Jahr gueltig?) und speichert via Repository
    [5] budget_repository schreibt in die Datenbank

=== WAS BEDEUTEN DIE RUECKGABEWERTE? ===
    None  = Alles gut, Budget wurde gesetzt/geaendert/geloescht
    str   = Ein Fehler (z.B. "Ungueltige Monatszahl"), den die View anzeigen soll
    list  = Liste von Budget-Objekten (bei list_budgets)
    dict  = Status-Informationen (bei check_budget_status)

=== GESCHAEFTSREGELN (im BudgetService, nicht hier) ===
    - Monat muss 1-12 sein, Jahr muss sinnvoll sein
    - Pro Monat und Kategorie kann es nur ein Budget geben (Upsert-Logik)
    - Der tatsaechliche Verbrauch wird aus den Transaktionen berechnet
"""

from __future__ import annotations

from src.services.budget_service import budget_service


# Orchestriert Budget-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class BudgetController:
    """UI-Controller fuer Budget-Use-Cases (Setzen, Pruefen, Auflisten, Loeschen).

    Alle Methoden folgen dem gleichen Muster:
    1. service-Methode aufrufen
    2. Bei Erfolg: None oder das Ergebnis zurueckgeben
    3. Bei Fehler: Fehlermeldung als String zurueckgeben (nie die Exception selbst)
    """

    def set_budget(self, payload: dict) -> str | None:
        """Setzt ein Budget (legt neu an oder aktualisiert ein bestehendes).

        AUFRUF-KETTE:
            budget_view.py (Button "Budget setzen") → set_budget(payload)
            → budget_service.set_budget(payload)
            → budget_repository (create oder update) → Datenbank

        EINGABE (payload-Keys):
            - "user_id"      (int): ID des eingeloggten Users
            - "month"        (int): Monat 1-12
            - "year"         (int): Jahr (z.B. 2026)
            - "limit_amount" (float): Maximale Ausgaben in CHF
            - "category_id"  (int|None): Kategorie oder None fuer globales Budget

        UPSERT-LOGIK (im Service):
            Existiert schon ein Budget fuer diesen User/Monat/Jahr/Kategorie?
            → Dann wird es aktualisiert (nicht doppelt angelegt).
            Noch keins vorhanden?
            → Dann wird ein neues angelegt.

        Args:
            payload: Dictionary mit Eingaben aus budget_view.py.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            budget_service.set_budget(payload)
            return None
        except Exception as error:
            return str(error)

    def check_budget_status(
        self,
        user_id: int,
        month: int,
        year: int,
        category_id: int | None = None,
    ) -> dict | str:
        """Prueft den aktuellen Budgetstatus (Limit vs. bisherige Ausgaben).

        AUFRUF-KETTE:
            budget_view.py (Seite laden) → check_budget_status(...)
            → budget_service.check_budget_status(...)
            → budget_repository.get(...) + transaction_repository.sum_expenses(...)
            → Datenbank

        RUECKGABE (dict bei Erfolg):
            {
              "limit":    CHF-Limit (z.B. 500.0),
              "spent":    bisherige Ausgaben in diesem Monat (z.B. 342.50),
              "remaining": verbleibend (z.B. 157.50),
              "exceeded": True/False (True wenn Limit ueberschritten)
            }

        Args:
            user_id: ID des eingeloggten Users.
            month: Monat (1-12).
            year: Jahr (z.B. 2026).
            category_id: Kategorie-ID oder None fuer globales Budget.

        Returns:
            Dict mit Budgetstatus oder Fehlermeldung als String.
        """
        try:
            return budget_service.check_budget_status(
                user_id=user_id,
                month=month,
                year=year,
                category_id=category_id,
            )
        except Exception as error:
            return str(error)

    def update_budget(self, budget_id: int, limit_amount: float) -> str | None:
        """Aendert das Limit eines bestehenden Budgets.

        AUFRUF-KETTE:
            budget_view.py (Button "Limit aendern") → update_budget(budget_id, neues_limit)
            → budget_service.update_budget(budget_id, limit_amount)
            → budget_repository.save(budget) → Datenbank

        Args:
            budget_id: ID des Budgets, das geaendert werden soll.
            limit_amount: Neues Limit in CHF (muss > 0 sein, prueft der Service).

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            budget_service.update_budget(budget_id, limit_amount)
            return None
        except Exception as error:
            return str(error)

    def delete_budget(self, budget_id: int) -> str | None:
        """Loescht ein Budget dauerhaft aus der Datenbank.

        AUFRUF-KETTE:
            budget_view.py (Button "Budget loeschen") → delete_budget(budget_id)
            → budget_service.delete_budget(budget_id)
            → budget_repository.delete(budget) → Datenbank

        Args:
            budget_id: ID des zu loeschenden Budgets.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            budget_service.delete_budget(budget_id)
            return None
        except Exception as error:
            return str(error)

    def list_budgets_grouped(self, user_id: int, category_names: dict) -> dict | str:
        """Gibt Budgets aufgeteilt in aktive und abgelaufene Liste zurueck.

        Berechnet Budgetstatus (is_exceeded, used_amount) und bestimmt, ob ein
        Budget aktiv oder abgelaufen ist. Die View muss keine Logik mehr selbst
        umsetzen.

        Args:
            user_id: ID des eingeloggten Users.
            category_names: Dict {category_id: name} fuer die Anzeige.

        Returns:
            Dict {"active": [...], "expired": [...]} oder Fehlermeldung als String.
        """
        try:
            from datetime import date
            budgets = budget_service.list_budgets(user_id)
            today = date.today()
            cur_year = today.year
            cur_month = today.month
            month_names = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                           "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
            active_rows = []
            expired_rows = []
            for budget in budgets:
                month_name = month_names[budget.month]
                month_year = f"{month_name} {budget.year}"
                try:
                    status_data = budget_service.check_budget_status(
                        user_id=user_id,
                        month=budget.month,
                        year=budget.year,
                        category_id=budget.category_id,
                    )
                    if isinstance(status_data, dict):
                        is_exceeded = status_data.get("is_exceeded", False)
                        used_amount = status_data.get("current_spending", 0)
                    else:
                        is_exceeded = False
                        used_amount = 0
                except Exception:
                    is_exceeded = False
                    used_amount = 0

                row = {
                    "budget_id": budget.budget_id,
                    "month_year": month_year,
                    "category": "Alle" if budget.category_id is None
                        else category_names.get(budget.category_id, f"ID {budget.category_id}"),
                    "limit": f"{budget.limit_amount:,.2f}",
                    "used": f"{used_amount:,.2f}",
                    "status": "OK ✓" if not is_exceeded else "ÜBERSCHRITTEN ⚠",
                }

                is_active = (budget.year > cur_year) or (
                    budget.year == cur_year and budget.month >= cur_month
                )
                if is_active:
                    active_rows.append(row)
                else:
                    expired_rows.append(row)

            return {"active": active_rows, "expired": expired_rows}
        except Exception as error:
            return str(error)

    def list_budgets(self, user_id: int) -> list | str:
        """Gibt alle Budgets eines Users als Liste zurueck.

        AUFRUF-KETTE:
            budget_view.py (Seite laden) → list_budgets(user_id)
            → budget_service.list_budgets(user_id)
            → budget_repository.list_by_user(user_id) → Datenbank

        RUECKGABE:
            Liste von Budget-Objekten (SQLModel-Instanzen). Jedes Objekt hat Felder wie:
            .budget_id, .month, .year, .limit_amount, .category_id
            Die View zeigt diese als Tabelle an.

        Args:
            user_id: ID des eingeloggten Users.

        Returns:
            Liste von Budget-Objekten oder Fehlermeldung als String.
        """
        try:
            return budget_service.list_budgets(user_id)
        except Exception as error:
            return str(error)


# Singleton-Instanz: wird von budget_view.py importiert.
budget_controller = BudgetController()
