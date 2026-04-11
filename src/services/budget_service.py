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

		with Session(engine) as session:
			if UserRepository.get_by_id(session, user_id) is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			existing = BudgetRepository.get_by_scope(
				session,
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
				return BudgetRepository.create(session, budget)

			raise ValueError(
				"Budget existiert bereits fuer diesen User, Monat, Jahr und Kategorie"
			)

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
			budget = BudgetRepository.get_by_scope(
				session,
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
			if budget is None:
				raise KeyError("Budget nicht gefunden")

			transactions = TransactionRepository.list_for_month(
				session,
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


budget_service = BudgetService()
