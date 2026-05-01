from __future__ import annotations

from datetime import date

from src.data_access.db import engine
from src.data_access.repositories.recurring_repository import RecurringRepository
from src.services.recurring_service import recurring_service
from sqlmodel import Session


# Orchestriert Dauerauftrag-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class RecurringController:
    # Legt einen Dauerauftrag an.
    def create_recurring(self, payload: dict) -> str | None:
        try:
            # --- NEU: Datumsumwandlungen ---
            # 1. Startdatum des Dauerauftrags
            if "start_date" in payload and isinstance(payload["start_date"], str):
                payload["start_date"] = date.fromisoformat(payload["start_date"])
                
            # 2. Enddatum des Dauerauftrags (falls vorhanden)
            if "end_date" in payload and isinstance(payload["end_date"], str):
                payload["end_date"] = date.fromisoformat(payload["end_date"])
                
            # 3. Datum für die zugrundeliegende Basis-Transaktion
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = date.fromisoformat(payload["date"])
            # -------------------------------

            recurring_service.create_recurring(payload)
            return None
        except Exception as error:
            return str(error)

    # Verarbeitet faellige Dauerauftraege beim Login.
    def process_due_on_login(self, user_id: int, login_date: date) -> int | str:
        try:
            return recurring_service.process_due_recurring_on_login(user_id, login_date)
        except Exception as error:
            return str(error)

    # Aktualisiert einen bestehenden Dauerauftrag.
    def update_recurring(self, recurring_id: int, payload: dict) -> str | None:
        try:
            # Umwandlung von Dateien in date-Objekte
            if "end_date" in payload and isinstance(payload["end_date"], str):
                payload["end_date"] = date.fromisoformat(payload["end_date"]) if payload["end_date"] else None

            recurring_service.update_recurring(recurring_id, payload)
            return None
        except Exception as error:
            return str(error)

    # Loescht einen Dauerauftrag.
    def delete_recurring(self, recurring_id: int) -> str | None:
        try:
            recurring_service.delete_recurring(recurring_id)
            return None
        except Exception as error:
            return str(error)

    # Liefert einen Dauerauftrag nach ID oder einen Fehler.
    def get_recurring_by_id(self, recurring_id: int) -> dict | str:
        try:
            with Session(engine) as session:
                recurring_repository = RecurringRepository(session)
                recurring = recurring_repository.get_by_id(recurring_id)
            if recurring is None:
                return "Dauerauftrag nicht gefunden"
            return {
                "recurring_id": recurring.recurring_id,
                "amount": recurring.amount,
                "category_id": recurring.category_id,
                "account_id": recurring.account_id,
                "start_date": recurring.start_date.isoformat() if recurring.start_date else None,
                "end_date": recurring.end_date.isoformat() if recurring.end_date else None,
                "frequency": recurring.frequency,
                "description": recurring.description,
            }
        except Exception as error:
            return str(error)

    # Liefert alle Daueraufträge für einen User oder Fehlermeldung.
    def list_recurring(self, user_id: int) -> list | str:
        try:
            return recurring_service.list_recurring(user_id)
        except Exception as error:
            return str(error)

    # Berechnet das nächste Ausführungsdatum eines Dauerauftrags.
    def calculate_next_due_date(self, from_date: date, interval: str) -> date | str:
        try:
            return recurring_service._next_due_date(from_date, interval)
        except Exception as error:
            return str(error)


recurring_controller = RecurringController()