"""Budget-Logik (Service-Schicht).

Dieses Modul implementiert die Geschäftslogik für Budgets: anlegen/ändern,
auflisten, löschen und den aktuellen Budgetstatus berechnen.
Es gehört zur Service-Schicht, weil hier Regeln (Validierung, Berechnung) und
Orchestrierung von Repositories passieren (`BudgetRepository`, `TransactionRepository`).
"""

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
	"""Service für Budgetverwaltung und Budget-Checks."""
	# Legt ein Budget an oder aktualisiert ein bestehendes Budget im gleichen Scope.
	def set_budget(self, payload: dict) -> Budget:
		"""Legt ein Budget an oder aktualisiert ein bestehendes Budget (Upsert).

		Warum Upsert?
		Im Datenmodell gibt es einen UniqueConstraint auf
		(`user_id`, `month`, `year`, `category_id`). Dadurch darf es pro Scope nur
		ein Budget geben. Diese Methode prüft zuerst, ob schon eins existiert und
		entscheidet dann zwischen "create" oder "update".

		Args:
			payload: Eingaben aus UI/Controller. Erwartet u. a.
				`user_id`, `limit_amount`, `month`, `year` und optional `category_id`.

		Returns:
			Das neu erstellte oder aktualisierte Budget.

		Raises:
			ValueError: Bei ungültigem Betrag oder ungültigem Monat/Jahr.
			KeyError: Wenn der User nicht existiert.
		"""
		user_id = int(payload["user_id"])
		limit_amount = float(payload["limit_amount"])
		month = int(payload["month"])
		year = int(payload["year"])
		category_id = payload.get("category_id")
		category_id = int(category_id) if category_id is not None else None

		validate_positive_amount(limit_amount)
		validate_budget_month_year(month, year)
		# Allow creating budgets for past months (useful for importing historical budgets)

		with Session(engine) as session:
			user_repository = UserRepository(session)
			budget_repository = BudgetRepository(session)

			if user_repository.get_by_id(user_id) is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			# Scope-Suche: wenn schon ein Budget existiert, dürfen wir kein zweites anlegen.
			existing = budget_repository.get_by_scope(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
			if existing is None:
				# Neues Budget anlegen.
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
		"""Berechnet den aktuellen Budgetstatus (Verbrauch vs. Limit).

		Die Ausgaben werden aus den Transaktionen des Monats berechnet.
		Wichtig: Wir zählen nur `expense`-Transaktionen als "Verbrauch".
		Einnahmen erhöhen nicht das Budget-Limit, sondern sind nur Geldzufluss.

		Args:
			user_id: Besitzer.
			month: Monat (1-12).
			year: Jahr.
			category_id: Optional: Budget nur für eine Kategorie.

		Returns:
			Dictionary mit Limit, aktuellem Verbrauch und Überschreitungs-Flag.

		Raises:
			ValueError: Wenn Monat/Jahr ungültig sind.
			KeyError: Wenn kein Budget für diesen Scope existiert.
		"""
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

			# Alle Transaktionen des Monats laden (optional gefiltert nach Kategorie).
			transactions = transaction_repository.list_for_month(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
			# Verbrauch = Summe der Ausgaben (expense). Einnahmen werden ignoriert.
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
		"""Listet alle Budgets eines Users."""
		with Session(engine) as session:
			budget_repository = BudgetRepository(session)
			return budget_repository.list_by_user(user_id)

	# Aktualisiert den Budgetbetrag eines bestehenden Budgets.
	def update_budget(self, budget_id: int, limit_amount: float) -> Budget:
		"""Ändert das Limit eines bestehenden Budgets.

		Args:
			budget_id: ID des Budgets.
			limit_amount: Neues Limit (> 0).

		Returns:
			Aktualisiertes Budget.

		Raises:
			ValueError: Wenn der Betrag ungültig ist.
			KeyError: Wenn das Budget nicht existiert.
		"""
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
		"""Löscht ein Budget.

		Args:
			budget_id: ID des Budgets.

		Raises:
			KeyError: Wenn das Budget nicht existiert.
		"""
		with Session(engine) as session:
			budget_repository = BudgetRepository(session)
			budget = budget_repository.get_by_id(budget_id)
			if budget is None:
				raise KeyError(f"Budget {budget_id} nicht gefunden")
			budget_repository.delete(budget_id)


budget_service = BudgetService()
