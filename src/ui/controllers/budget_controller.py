from __future__ import annotations

from src.services.budget_service import budget_service


# Orchestriert Budget-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class BudgetController:
	# Legt ein Budget an oder aktualisiert es.
	def set_budget(self, payload: dict) -> str | None:
		try:
			budget_service.set_budget(payload)
			return None
		except Exception as error:
			return str(error)

	# Liefert den Budgetstatus oder eine Fehlermeldung.
	def check_budget_status(
		self,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None = None,
	) -> dict | str:
		try:
			return budget_service.check_budget_status(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
		except Exception as error:
			return str(error)


budget_controller = BudgetController()
