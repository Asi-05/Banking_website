from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Budget


# Kapselt reine Datenbankzugriffe fuer Budgets.
class BudgetRepository:
	def __init__(self, session: Session):
		self.session = session

	# Laedt ein Budget eindeutig nach ID.
	def get_by_id(self, budget_id: int) -> Budget | None:
		return self.session.get(Budget, budget_id)

	# Laedt ein Budget eindeutig nach User, Monat, Jahr und optional Kategorie.
	def get_by_scope(
		self,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None,
	) -> Budget | None:
		statement = select(Budget).where(
			Budget.user_id == user_id,
			Budget.month == month,
			Budget.year == year,
			Budget.category_id == category_id,
		)
		return self.session.exec(statement).first()

	# Legt ein neues Budget an und persistiert es.
	def create(self, budget: Budget) -> Budget:
		self.session.add(budget)
		self.session.commit()
		self.session.refresh(budget)
		return budget

	# Persistiert Aenderungen eines Budgets.
	def save(self, budget: Budget) -> Budget:
		self.session.add(budget)
		self.session.commit()
		self.session.refresh(budget)
		return budget

	# Gibt Budgets eines Users optional gefiltert nach Monat/Jahr zurueck.
	def list_by_user(
		self,
		user_id: int,
		month: int | None = None,
		year: int | None = None,
	) -> list[Budget]:
		statement = select(Budget).where(Budget.user_id == user_id)
		if month is not None:
			statement = statement.where(Budget.month == month)
		if year is not None:
			statement = statement.where(Budget.year == year)
		return list(self.session.exec(statement).all())

	# Loescht ein Budget anhand der ID.
	def delete(self, budget_id: int) -> None:
		budget = self.get_by_id(budget_id)
		if budget is None:
			return
		self.session.delete(budget)
		self.session.commit()
