from __future__ import annotations

from datetime import date

from src.services.recurring_service import recurring_service


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


recurring_controller = RecurringController()