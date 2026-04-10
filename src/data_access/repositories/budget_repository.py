from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Budget


# Kapselt reine Datenbankzugriffe fuer Budgets.
class BudgetRepository:
	# Laedt ein Budget eindeutig nach User, Monat, Jahr und optional Kategorie.
	@staticmethod
	def get_by_scope(
		session: Session,
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
		return session.exec(statement).first()

	# Legt ein neues Budget an und persistiert es.
	@staticmethod
	def create(session: Session, budget: Budget) -> Budget:
		session.add(budget)
		session.commit()
		session.refresh(budget)
		return budget

	# Persistiert Aenderungen eines Budgets.
	@staticmethod
	def save(session: Session, budget: Budget) -> Budget:
		session.add(budget)
		session.commit()
		session.refresh(budget)
		return budget

	# Gibt Budgets eines Users optional gefiltert nach Monat/Jahr zurueck.
	@staticmethod
	def list_by_user(
		session: Session,
		user_id: int,
		month: int | None = None,
		year: int | None = None,
	) -> list[Budget]:
		statement = select(Budget).where(Budget.user_id == user_id)
		if month is not None:
			statement = statement.where(Budget.month == month)
		if year is not None:
			statement = statement.where(Budget.year == year)
		return list(session.exec(statement).all())
