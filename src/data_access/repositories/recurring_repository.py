from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Account, RecurringTransaction


# Kapselt reine Datenbankzugriffe fuer Dauerauftraege.
class RecurringRepository:
	# Legt einen Dauerauftrag an und persistiert ihn.
	@staticmethod
	def create(
		session: Session, recurring: RecurringTransaction
	) -> RecurringTransaction:
		session.add(recurring)
		session.commit()
		session.refresh(recurring)
		return recurring

	# Laedt einen Dauerauftrag per ID.
	@staticmethod
	def get_by_id(session: Session, recurring_id: int) -> RecurringTransaction | None:
		return session.get(RecurringTransaction, recurring_id)

	# Gibt alle Dauerauftraege eines Users zurueck.
	@staticmethod
	def list_by_user(session: Session, user_id: int) -> list[RecurringTransaction]:
		statement = (
			select(RecurringTransaction)
			.join(Account, Account.account_id == RecurringTransaction.account_id)
			.where(Account.user_id == user_id)
		)
		return list(session.exec(statement).all())

	# Gibt potenziell faellige Dauerauftraege eines Users zurueck.
	@staticmethod
	def list_due_by_user(
		session: Session,
		user_id: int,
		reference_date: date,
	) -> list[RecurringTransaction]:
		statement = (
			select(RecurringTransaction)
			.join(Account, Account.account_id == RecurringTransaction.account_id)
			.where(Account.user_id == user_id)
			.where(RecurringTransaction.start_date <= reference_date)
		)
		return list(session.exec(statement).all())

	# Persistiert Aenderungen eines Dauerauftrags.
	@staticmethod
	def save(
		session: Session, recurring: RecurringTransaction
	) -> RecurringTransaction:
		session.add(recurring)
		session.commit()
		session.refresh(recurring)
		return recurring
