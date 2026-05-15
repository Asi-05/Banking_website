"""src.ui.controllers.dashboard_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS ZEIGT DAS DASHBOARD? ===
Das Dashboard ist die Startseite nach dem Login. Es zeigt:
    - Gesamtsaldo aller aktiven Konten
    - Einnahmen und Ausgaben im aktuellen Monat
    - Ein Diagramm mit Einnahmen/Ausgaben-Verlauf
    - Liste der aktiven Konten mit Saldo
    - Die 5 letzten Transaktionen

=== WAS MACHT DIESER CONTROLLER? ===
Er sammelt Daten aus MEHREREN anderen Controllern und bereitet sie so auf,
dass die View nur noch anzeigen muss (kein eigenes Berechnen in der View):

    AUFRUF-KETTE (get_dashboard_view_data):
    [1] dashboard_view.py (Seite laden)
    [2] → dashboard_controller.get_dashboard_view_data(user_id)
    [3] → dashboard_service.dashboard(user_id, start_date, end_date) [Summen/Diagramm]
    [3] → account_controller.list_accounts(user_id) [Konten-Liste]
    [3] → transaction_controller.filter_transactions(...) [letzte Transaktionen]
    [3] → category_controller.list_categories() [Kategorie-Namen]
    [4] Alles wird zu einem einzigen Dictionary zusammengefuehrt
    [5] Dashboard-View rendert dieses Dictionary

=== WARUM DIESER CONTROLLER? ===
Die View soll so einfach wie moeglich sein - sie zeigt nur noch Daten an.
Das Sammeln und Aufbereiten von Daten aus mehreren Quellen macht dieser Controller.
Das nennt man "Presenter" oder "View-Model" Muster.

=== RÜCKGABE (bei Erfolg) ===
{
  "summary":             DashboardSummary-Objekt (total_balance, income, expenses, chart_data)
  "month_name":          z.B. "Mai"
  "active_accounts":     Liste von {"label": "Privatkonto", "iban": "CH...", "balance": 1234.56}
  "recent_transactions": Liste von {"note": "Miete", "date": "01.05.2026",
                                    "amount_str": "-CHF 1'200.00", "category_name": "Miete"}
}
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from src.services.dashboard_service import dashboard_service
from src.ui.controllers.account_controller import account_controller
from src.ui.controllers.category_controller import category_controller
from src.ui.controllers.transaction_controller import transaction_controller
from src.utils.formatters import format_chf


class DashboardController:
    """UI-Controller fuer Dashboard-Daten.

    Sammelt Daten aus mehreren Services/Controllern und bereitet sie
    fuer die direkte Darstellung in dashboard_view.py auf.
    """

    def _current_month_range(self) -> tuple[date, date, str]:
        """Berechnet den ersten und letzten Tag des aktuellen Monats.

        VERWENDUNG: Wird intern genutzt, um den Standard-Zeitraum fuer das
        Dashboard zu bestimmen (immer der aktuelle Monat).

        WARUM 'monthrange'?
            Nicht alle Monate haben 30 Tage. monthrange(2026, 2) gibt (0, 28) zurueck
            (Februar 2026 hat 28 Tage). So berechnen wir immer den korrekten letzten Tag.

        Returns:
            Tupel aus (start_date, end_date, monatsname_auf_deutsch).
            Beispiel: (date(2026, 5, 1), date(2026, 5, 31), "Mai")
        """
        today = date.today()
        # Erster Tag des Monats ist immer der 1.
        start_date = date(today.year, today.month, 1)
        # Letzter Tag: monthrange gibt (Wochentag-des-1., Anzahl-Tage) zurueck
        end_date = date(today.year, today.month, monthrange(today.year, today.month)[1])
        month_names = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni",
            7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
        }
        return start_date, end_date, month_names[today.month]

    def get_dashboard(self, user_id: int, start_date: date, end_date: date):
        """Ruft Dashboard-Aggregationen fuer einen Zeitraum ab.

        AUFRUF-KETTE:
            Beliebige View → get_dashboard(user_id, start_date, end_date)
            → dashboard_service.dashboard(user_id, start_date, end_date)
            → transaction_repository.sum_by_type_and_period(...) → Datenbank

        RUECKGABE:
            DashboardSummary-Objekt mit:
            .total_balance: Gesamtsaldo aller Konten
            .total_income:  Einnahmen im Zeitraum
            .total_expenses: Ausgaben im Zeitraum
            .chart_data:    Liste von ChartData-Objekten (fuer Diagramm)

        Args:
            user_id: ID des eingeloggten Users.
            start_date: Beginn des Auswertungszeitraums (erster Tag inkl.).
            end_date: Ende des Auswertungszeitraums (letzter Tag inkl.).

        Returns:
            DashboardSummary-Objekt oder Fehlermeldung als String.
        """
        try:
            return dashboard_service.dashboard(user_id, start_date, end_date)
        except Exception as error:
            return str(error)

    def get_dashboard_view_data(self, user_id: int):
        """Bereitet alle Dashboard-Daten fuer die View auf.

        AUFRUF-KETTE (vollstaendig):
            dashboard_view.py (Seite laden)
            → get_dashboard_view_data(user_id)
            → _current_month_range()                    [berechnet Start/Ende des Monats]
            → dashboard_service.dashboard(...)          [Summen + Diagrammdaten]
            → account_controller.list_accounts(user_id) [aktive Konten]
            → transaction_controller.filter_transactions(...) [letzte Transaktionen]
            → category_controller.list_categories()     [Kategorie-Namen]

        WAS DIESE METHODE AUSSERDEM TUT:
            - Filtert nur aktive Konten heraus (Status = "aktiv")
            - Sortiert Transaktionen nach Datum (neueste zuerst)
            - Nimmt nur die letzten 5 Transaktionen
            - Formatiert Betraege als Strings mit +/- und CHF (z.B. "-CHF 1'200.00")
            - Formatiert Daten als TT.MM.JJJJ

        RÜCKGABE (dict bei Erfolg):
            {
              "summary": DashboardSummary,
              "month_name": "Mai",
              "active_accounts": [{"label": ..., "iban": ..., "balance": ...}, ...],
              "recent_transactions": [{"note": ..., "date": ..., "amount_str": ...,
                                       "amount_class": ..., "category_name": ...}, ...]
            }

        Args:
            user_id: ID des eingeloggten Users (aus app_state["user_id"]).

        Returns:
            Aufbereitetes Dictionary fuer die View oder Fehlermeldung als String.
        """
        try:
            # Zeitraum: aktueller Monat (1. bis letzter Tag)
            start_date, end_date, month_name = self._current_month_range()

            # Dashboard-Summen (Gesamtsaldo, Einnahmen, Ausgaben, Diagrammdaten)
            summary = self.get_dashboard(user_id, start_date, end_date)
            if isinstance(summary, str):
                return summary  # Fehler: als String weitergeben

            # Alle Konten des Users laden
            accounts_result = account_controller.list_accounts(user_id)
            # Alle Transaktionen im aktuellen Monat laden (fuer "letzte Transaktionen")
            transactions_result = transaction_controller.filter_transactions(
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
            )
            # Kategorie-Namen laden (fuer Anzeige in Transaktionsliste)
            category_names = category_controller.list_categories()

            # Fehler-Pruefung: Konten oder Transaktionen konnten nicht geladen werden
            if isinstance(accounts_result, str):
                return accounts_result
            if isinstance(transactions_result, str):
                return transactions_result

            # Konten-Typen in lesbares Deutsch uebersetzen
            type_names = {"privat": "Privatkonto", "spar": "Sparkonto"}

            # Nur aktive Konten herausfiltern und aufbereiten
            active_accounts = []
            for account in accounts_result:
                # .attribute funktioniert fuer SQLModel-Objekte, .get() fuer Dictionaries
                acc_type = account.account_type if hasattr(account, "account_type") else account.get("account_type")
                if (account.status if hasattr(account, "status") else account.get("status")) != "aktiv":
                    continue  # Inaktive/geschlossene Konten ueberspringen

                iban = (account.iban if hasattr(account, "iban") else account.get("iban") or "").upper()
                balance = account.balance if hasattr(account, "balance") else account.get("balance")
                active_accounts.append(
                    {
                        "label": type_names.get(acc_type, acc_type),
                        "iban": iban,
                        "balance": balance,
                    }
                )

            # Hilfsfunktion: Datum-String oder date-Objekt in date-Objekt umwandeln
            def _to_date(value):
                if isinstance(value, date):
                    return value
                if isinstance(value, str):
                    return datetime.strptime(value, "%d-%m-%Y").date()
                return date.today()

            # Letzte 5 Transaktionen (neueste zuerst, nur bereits gebuchte)
            recent_transactions = []
            # Nur Transaktionen bis heute beruecksichtigen (keine zukunftigen)
            booked = [t for t in transactions_result if _to_date(t["date"]) <= date.today()]
            # Sortieren nach Datum (neueste zuerst), dann die letzten 5 nehmen
            recent = sorted(booked, key=lambda t: _to_date(t["date"]), reverse=True)[:5]

            for transaction in recent:
                # Einnahme oder Ausgabe? Bestimmt die Farbe und das Vorzeichen
                is_income = transaction.get("type") in ("income", "Einkommen")
                amount_value = abs(transaction["amount"])
                recent_transactions.append(
                    {
                        "note": (transaction.get("note") or transaction.get("type") or "").strip() or "—",
                        "date": str(transaction["date"]).replace("-", "."),
                        # +CHF fuer Einnahmen (gruen), -CHF fuer Ausgaben (rot)
                        "amount_str": f"+CHF {format_chf(amount_value)}" if is_income else f"-CHF {format_chf(amount_value)}",
                        # CSS-Klasse: gruen fuer Einnahmen, rot fuer Ausgaben
                        "amount_class": "font-semibold text-green-600" if is_income else "font-semibold text-red-600",
                        "category_name": category_names.get(transaction.get("category_id"), ""),
                    }
                )

            # Alles in einem Dictionary zusammenfassen fuer die View
            return {
                "summary": summary,
                "month_name": month_name,
                "active_accounts": active_accounts,
                "recent_transactions": recent_transactions,
            }
        except Exception as error:
            return str(error)


# Singleton-Instanz: wird von dashboard_view.py importiert.
dashboard_controller = DashboardController()
