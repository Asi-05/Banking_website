from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Account, RecurringTransaction


# Kapselt reine Datenbankzugriffe fuer Dauerauftraege.
class RecurringRepository:
	def __init__(self, session: Session):
		self.session = session

	# Legt einen Dauerauftrag an und persistiert ihn.
	def create(self, recurring: RecurringTransaction) -> RecurringTransaction:
		self.session.add(recurring)
		self.session.commit()
		self.session.refresh(recurring)
		return recurring

	# Laedt einen Dauerauftrag per ID.
	def get_by_id(self, recurring_id: int) -> RecurringTransaction | None:
		return self.session.get(RecurringTransaction, recurring_id)

	# Gibt alle Dauerauftraege eines Users zurueck.
	def list_by_user(self, user_id: int) -> list[RecurringTransaction]:
		statement = (
			select(RecurringTransaction)
			.join(Account, Account.account_id == RecurringTransaction.account_id)
			.where(Account.user_id == user_id)
		)
		return list(self.session.exec(statement).all())

	# Gibt potenziell faellige Dauerauftraege eines Users zurueck.
	def list_due_by_user(
		self,
		user_id: int,
		reference_date: date,
	) -> list[RecurringTransaction]:
		statement = (
			select(RecurringTransaction)
			.join(Account, Account.account_id == RecurringTransaction.account_id)
			.where(Account.user_id == user_id)
			.where(RecurringTransaction.start_date <= reference_date)
		)
		return list(self.session.exec(statement).all())

	# Persistiert Aenderungen eines Dauerauftrags.
	def save(self, recurring: RecurringTransaction) -> RecurringTransaction:
		self.session.add(recurring)
		self.session.commit()
		self.session.refresh(recurring)
		return recurring

	# Loescht einen Dauerauftrag per ID.
	def delete(self, recurring_id: int) -> None:
		recurring = self.session.get(RecurringTransaction, recurring_id)
		if recurring is not None:
			self.session.delete(recurring)
			self.session.commit()
