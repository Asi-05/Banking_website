"""src.ui.controllers.dashboard_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Das Dashboard ist eine aggregierte Sicht auf Konten und Transaktionen.
Dieser Controller ruft den `DashboardService` auf und kapselt Fehler so, dass
die View entweder eine Summary oder einen Fehlertext anzeigen kann.
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
    """UI-Controller fuer Dashboard-Daten."""

    def _current_month_range(self) -> tuple[date, date, str]:
        """Berechnet den aktuellen Monatsbereich und den deutschen Monatsnamen."""
        today = date.today()
        start_date = date(today.year, today.month, 1)
        end_date = date(today.year, today.month, monthrange(today.year, today.month)[1])
        month_names = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni",
            7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
        }
        return start_date, end_date, month_names[today.month]

    def get_dashboard(self, user_id: int, start_date: date, end_date: date):
        """Liefert Dashboard-Aggregationen fuer einen Zeitraum.

        Args:
            user_id: ID des eingeloggten Users.
            start_date: Startdatum (inkl.).
            end_date: Enddatum (inkl.).

        Returns:
            Ein `DashboardSummary`-Objekt oder eine Fehlermeldung als String.

        Raises:
            Keine. Fehler werden als String zur UI zurueckgegeben.
        """
        try:
            return dashboard_service.dashboard(user_id, start_date, end_date)
        except Exception as error:
            return str(error)

    def get_dashboard_view_data(self, user_id: int):
        """Liefert die bereits fuer die View aufbereiteten Dashboard-Daten.

        Die View soll moeglichst nur noch rendern. Daher werden hier die
        Anzeige-spezifischen Daten wie aktive Konten, letzte Transaktionen und
        formatierte Betrags-/Datumswerte vorbereitet.
        """
        try:
            start_date, end_date, month_name = self._current_month_range()
            summary = self.get_dashboard(user_id, start_date, end_date)
            if isinstance(summary, str):
                return summary

            accounts_result = account_controller.list_accounts(user_id)
            transactions_result = transaction_controller.filter_transactions(
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
            )
            category_names = category_controller.list_categories()

            if isinstance(accounts_result, str):
                return accounts_result
            if isinstance(transactions_result, str):
                return transactions_result

            type_names = {"privat": "Privatkonto", "spar": "Sparkonto"}

            active_accounts = []
            for account in accounts_result:
                acc_type = account.account_type if hasattr(account, "account_type") else account.get("account_type")
                if (account.status if hasattr(account, "status") else account.get("status")) != "aktiv":
                    continue

                iban = (account.iban if hasattr(account, "iban") else account.get("iban") or "").upper()
                balance = account.balance if hasattr(account, "balance") else account.get("balance")
                active_accounts.append(
                    {
                        "label": type_names.get(acc_type, acc_type),
                        "iban": iban,
                        "balance": balance,
                    }
                )

            def _to_date(value):
                if isinstance(value, date):
                    return value
                if isinstance(value, str):
                    return datetime.strptime(value, "%d-%m-%Y").date()
                return date.today()

            recent_transactions = []
            booked = [t for t in transactions_result if _to_date(t["date"]) <= date.today()]
            recent = sorted(booked, key=lambda t: _to_date(t["date"]), reverse=True)[:5]

            for transaction in recent:
                is_income = transaction.get("type") in ("income", "Einkommen")
                amount_value = abs(transaction["amount"])
                recent_transactions.append(
                    {
                        "note": (transaction.get("note") or transaction.get("type") or "").strip() or "—",
                        "date": str(transaction["date"]).replace("-", "."),
                        "amount_str": f"+CHF {format_chf(amount_value)}" if is_income else f"-CHF {format_chf(amount_value)}",
                        "amount_class": "font-semibold text-green-600" if is_income else "font-semibold text-red-600",
                        "category_name": category_names.get(transaction.get("category_id"), ""),
                    }
                )

            return {
                "summary": summary,
                "month_name": month_name,
                "active_accounts": active_accounts,
                "recent_transactions": recent_transactions,
            }
        except Exception as error:
            return str(error)


dashboard_controller = DashboardController()
