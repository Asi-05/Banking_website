from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Transaction


# Kapselt reine Datenbankzugriffe fuer Transaktionen.
class TransactionRepository:
	# Legt eine Transaktion an und persistiert sie.
	@staticmethod
	def create(session: Session, transaction: Transaction) -> Transaction:
		session.add(transaction)
		session.commit()
		session.refresh(transaction)
		return transaction

	# Laedt eine Transaktion per ID.
	@staticmethod
	def get_by_id(session: Session, transaction_id: int) -> Transaction | None:
		return session.get(Transaction, transaction_id)

	# Persistiert Aenderungen an einer Transaktion.
	@staticmethod
	def save(session: Session, transaction: Transaction) -> Transaction:
		session.add(transaction)
		session.commit()
		session.refresh(transaction)
		return transaction

	# Loescht eine Transaktion endgueltig.
	@staticmethod
	def delete(session: Session, transaction: Transaction) -> None:
		session.delete(transaction)
		session.commit()

	# Filtert Transaktionen optional nach Zeitraum, Kategorie und User-Zuordnung.
	@staticmethod
	def filter_transactions(
		session: Session,
		start_date: date | None = None,
		end_date: date | None = None,
		category_id: int | None = None,
		user_id: int | None = None,
	) -> list[Transaction]:
		statement = select(Transaction)
		if start_date is not None:
			statement = statement.where(Transaction.date >= start_date)
		if end_date is not None:
			statement = statement.where(Transaction.date <= end_date)
		if category_id is not None:
			statement = statement.where(Transaction.category_id == category_id)
		if user_id is not None:
			from sqlalchemy.orm import aliased
			from src.domain.models import Account, CreditCard, DebitCard

			# Alias fuer Account-Join via DebitCard (zweiter Join auf gleiche Tabelle)
			AccountViaCard = aliased(Account)

			statement = statement.join(
				Account,
				isouter=True,
				onclause=Account.account_id == Transaction.account_id,
			).join(
				CreditCard,
				isouter=True,
				onclause=CreditCard.creditcard_id == Transaction.creditcard_id,
			).join(
				DebitCard,
				isouter=True,
				onclause=DebitCard.card_id == Transaction.card_id,
			).join(
				AccountViaCard,
				isouter=True,
				onclause=AccountViaCard.account_id == DebitCard.account_id,
			).where(
				(Account.user_id == user_id)
				| (CreditCard.user_id == user_id)
				| (AccountViaCard.user_id == user_id)
			)

		statement = statement.order_by(Transaction.date.desc(), Transaction.transaction_id.desc())
		return list(session.exec(statement).all())

	# Gibt alle Transaktionen eines Monats optional je Kategorie zurueck.
	@staticmethod
	def list_for_month(
		session: Session,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None = None,
	) -> list[Transaction]:
		from src.domain.models import Account, CreditCard, DebitCard

		statement = select(Transaction).where(
			Transaction.date >= date(year, month, 1),
			Transaction.date < date(year + (month // 12), ((month % 12) + 1), 1),
		)
		if category_id is not None:
			statement = statement.where(Transaction.category_id == category_id)

		from sqlalchemy.orm import aliased
		AccountViaCard = aliased(Account)

		statement = statement.join(
			Account,
			isouter=True,
			onclause=Account.account_id == Transaction.account_id,
		).join(
			CreditCard,
			isouter=True,
			onclause=CreditCard.creditcard_id == Transaction.creditcard_id,
		).join(
			DebitCard,
			isouter=True,
			onclause=DebitCard.card_id == Transaction.card_id,
		).join(
			AccountViaCard,
			isouter=True,
			onclause=AccountViaCard.account_id == DebitCard.account_id,
		).where(
			(Account.user_id == user_id)
			| (CreditCard.user_id == user_id)
			| (AccountViaCard.user_id == user_id)
		)

		return list(session.exec(statement).all())
