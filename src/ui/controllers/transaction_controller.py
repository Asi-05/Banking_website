from __future__ import annotations

from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.category_repository import CategoryRepository
from src.services.transaction_service import transaction_service
from src.utils.formatters import format_date_dmy, format_transaction_type


# Orchestriert Transaktions-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class TransactionController:
    # Liefert alle verfuegbaren Transaktionskategorien.
    def get_all_categories(self) -> dict | str:
        try:
            with Session(engine) as session:
                category_repository = CategoryRepository(session)
                categories = category_repository.list_all()
            return {c.category_id: c.name for c in categories}
        except Exception as error:
            return str(error)

    # Erstellt eine neue Transaktion.
    def create_transaction(self, payload: dict) -> str | None:
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