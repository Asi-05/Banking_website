"""src.ui.controllers.transaction_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Transaktionen sind die zentrale Buchungs-Entitaet der App. Die UI sendet Werte
haeufig als Strings (insbesondere Datum). Der `TransactionService` erwartet
Python-Objekte wie `datetime.date`.

Dieser Controller normalisiert deshalb Datumsfelder und wandelt Service-Ergebnisse
in UI-freundliche Strukturen (z.B. bereits formatierte Strings) um.
"""

from __future__ import annotations

from datetime import date

from src.services.transaction_service import transaction_service
from src.utils.formatters import format_date_dmy, format_transaction_type


# Orchestriert Transaktions-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class TransactionController:
    """UI-Controller fuer Transaktionen (CRUD + Filter)."""

    # Erstellt eine neue Transaktion.
    def create_transaction(self, payload: dict) -> str | None:
        """Erstellt eine neue Transaktion.

        Der Controller normalisiert Datumsfelder aus der UI (ISO-String -> `date`).

        Args:
            payload: Eingabedaten aus der UI.

        Returns:
            `None` bei Erfolg, sonst Fehlertext.
        """
        try:
            # Datum von String (UI) in Python Date-Objekt umwandeln
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = date.fromisoformat(payload["date"])
                
            transaction_service.create_transaction(payload)
            return None
        except Exception as error:
            return str(error)

    # Bearbeitet eine bestehende Transaktion.
    def edit_transaction(self, transaction_id: int, payload: dict) -> str | None:
        """Bearbeitet eine bestehende Transaktion.

        Args:
            transaction_id: ID der zu bearbeitenden Transaktion.
            payload: Zu aendernde Felder (z.B. amount, note, optional date).

        Returns:
            `None` bei Erfolg, sonst Fehlertext.
        """
        try:
            # Datum von String (UI) in Python Date-Objekt umwandeln
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = date.fromisoformat(payload["date"])
                
            transaction_service.edit_transaction(transaction_id, payload)
            return None
        except Exception as error:
            return str(error)

    # Loescht eine bestehende Transaktion.
    def delete_transaction(self, transaction_id: int, confirm: bool) -> str | None:
        """Loescht eine Transaktion.

        Das Flag `confirm` ist eine UI-Schutzmassnahme, damit nicht versehentlich
        geloescht wird.
        Args:
            transaction_id: ID der zu loeschenden Transaktion.
            confirm: UI-Schutzflag; muss aktiv gesetzt werden, damit geloescht wird.

        Returns:
            `None` bei Erfolg, sonst Fehlertext.
        """
        try:
            transaction_service.delete_transaction(transaction_id, confirm)
            return None
        except Exception as error:
            return str(error)

    # Filtert Transaktionen und gibt Liste oder Fehlermeldung zurueck.
    def filter_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: int | None = None,
        user_id: int | None = None,
    ) -> list | str:
        """Filtert Transaktionen und liefert UI-geeignete Dictionaries.

        Die View bekommt hier keine ORM-Objekte, sondern serialisierbare Dicts mit
        bereits formatierten Strings (Datum/Typ), damit UI-Logik einfach bleibt.
        Args:
            start_date: Optionaler Start (inkl.).
            end_date: Optionales Ende (inkl.).
            category_id: Optionaler Kategorien-Filter.
            user_id: Optionaler User-Filter (Ownership wird im Service geklaert).

        Returns:
            Liste serialisierbarer Dicts oder Fehlertext als String.
        """
        try:
            transactions = transaction_service.filter_transactions(
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                user_id=user_id,
            )
            return [
                {
                    "transaction_id": transaction.transaction_id,
                    "amount": transaction.amount,
                    "date": format_date_dmy(transaction.date),
                    "type": format_transaction_type(transaction.type),
                    "note": transaction.note,
                    "category_id": transaction.category_id,
                    "account_id": transaction.account_id,
                    "card_id": transaction.card_id,
                    "creditcard_id": transaction.creditcard_id,
                }
                for transaction in transactions
            ]
        except Exception as error:
            return str(error)


transaction_controller = TransactionController()