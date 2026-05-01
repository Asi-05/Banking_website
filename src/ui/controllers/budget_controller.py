from __future__ import annotations

from src.data_access.db import engine
from src.data_access.repositories.category_repository import CategoryRepository
from src.services.budget_service import budget_service
from sqlmodel import Session


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

	# Aktualisiert ein bestehendes Budget.
	def update_budget(self, budget_id: int, limit_amount: float) -> str | None:
		try:
			budget_service.update_budget(budget_id, limit_amount)
			return None
		except Exception as error:
			return str(error)

	# Loescht ein bestehendes Budget.
	def delete_budget(self, budget_id: int) -> str | None:
		try:
			budget_service.delete_budget(budget_id)
			return None
		except Exception as error:
			return str(error)

	# Liefert alle Kategorien fuer Dropdowns.
	def get_all_categories(self) -> dict | str:
		try:
			with Session(engine) as session:
				category_repository = CategoryRepository(session)
				categories = category_repository.list_all()
			return {c.category_id: c.name for c in categories}
		except Exception as error:
			return str(error)

	# Liefert alle Budgets für einen User oder Fehlermeldung.
	def list_budgets(self, user_id: int) -> list | str:
		try:
			return budget_service.list_budgets(user_id)
		except Exception as error:
			return str(error)


budget_controller = BudgetController()
