from __future__ import annotations

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.budget_repository import BudgetRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import Budget
from src.utils.validators import (
	validate_budget_month_year,
	validate_positive_amount,
)


# Implementiert die Geschaeftslogik fuer Budgets.
class BudgetService:
	# Legt ein Budget an oder aktualisiert ein bestehendes Budget im gleichen Scope.
	def set_budget(self, payload: dict) -> Budget:
		user_id = int(payload["user_id"])
		limit_amount = float(payload["limit_amount"])
		month = int(payload["month"])
		year = int(payload["year"])
		category_id = payload.get("category_id")
		category_id = int(category_id) if category_id is not None else None

		validate_positive_amount(limit_amount)
		validate_budget_month_year(month, year)
		from datetime import date
		today = date.today()
		if date(year, month, 1) < date(today.year, today.month, 1):
			raise ValueError("Budget kann nicht für vergangene Monate erstellt werden")

		with Session(engine) as session:
			user_repository = UserRepository(session)
			budget_repository = BudgetRepository(session)

			if user_repository.get_by_id(user_id) is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			existing = budget_repository.get_by_scope(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
			if existing is None:
				budget = Budget(
					user_id=user_id,
					limit_amount=limit_amount,
					month=month,
					year=year,
					category_id=category_id,
				)
				return budget_repository.create(budget)

			# Budget aktualisieren falls bereits vorhanden (Upsert)
			existing.limit_amount = limit_amount
			return budget_repository.save(existing)

	# Prueft den aktuellen Budgetstatus fuer einen Scope.
	def check_budget_status(
		self,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None = None,
	) -> dict:
		validate_budget_month_year(month, year)

		with Session(engine) as session:
			budget_repository = BudgetRepository(session)
			transaction_repository = TransactionRepository(session)

			budget = budget_repository.get_by_scope(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
			if budget is None:
				raise KeyError("Budget nicht gefunden")

			transactions = transaction_repository.list_for_month(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
			current_spending = sum(
				t.amount for t in transactions if t.type == "expense"
			)
			return {
				"budget_id": budget.budget_id,
				"limit_amount": budget.limit_amount,
				"current_spending": current_spending,
				"is_exceeded": current_spending > budget.limit_amount,
				"month": month,
				"year": year,
				"category_id": category_id,
			}


	# Gibt alle Budgets eines Users zurueck.
	def list_budgets(self, user_id: int) -> list[Budget]:
		with Session(engine) as session:
			budget_repository = BudgetRepository(session)
			return budget_repository.list_by_user(user_id)

	# Aktualisiert den Budgetbetrag eines bestehenden Budgets.
	def update_budget(self, budget_id: int, limit_amount: float) -> Budget:
		validate_positive_amount(limit_amount)

		with Session(engine) as session:
			budget_repository = BudgetRepository(session)
			budget = budget_repository.get_by_id(budget_id)
			if budget is None:
				raise KeyError(f"Budget {budget_id} nicht gefunden")

			budget.limit_amount = float(limit_amount)
			return budget_repository.save(budget)

	# Loescht ein bestehendes Budget.
	def delete_budget(self, budget_id: int) -> None:
		with Session(engine) as session:
			budget_repository = BudgetRepository(session)
			budget = budget_repository.get_by_id(budget_id)
			if budget is None:
				raise KeyError(f"Budget {budget_id} nicht gefunden")
			budget_repository.delete(budget_id)


budget_service = BudgetService()
