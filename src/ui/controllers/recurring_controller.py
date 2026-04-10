from __future__ import annotations

from datetime import date

from src.services.recurring_service import recurring_service


# Orchestriert Dauerauftrag-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class RecurringController:
	# Legt einen Dauerauftrag an.
	def create_recurring(self, payload: dict) -> str | None:
		try:
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
