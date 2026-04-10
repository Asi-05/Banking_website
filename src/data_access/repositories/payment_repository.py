from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Payment, Transaction, Transfer


# Kapselt reine Datenbankzugriffe fuer Zahlungsobjekte.
class PaymentRepository:
	# Legt ein Payment-Objekt an und persistiert es.
	@staticmethod
	def create_payment(session: Session, payment: Payment) -> Payment:
		session.add(payment)
		session.commit()
		session.refresh(payment)
		return payment

	# Legt ein Transfer-Objekt an und persistiert es.
	@staticmethod
	def create_transfer(session: Session, transfer: Transfer) -> Transfer:
		session.add(transfer)
		session.commit()
		session.refresh(transfer)
		return transfer

	# Gibt alle kontobezogenen Transaktionen in einem Datumsbereich zurueck.
	@staticmethod
	def list_account_transactions_in_range(
		session: Session,
		account_id: int,
		start_date: date,
		end_date: date,
	) -> list[Transaction]:
		statement = (
			select(Transaction)
			.where(Transaction.account_id == account_id)
			.where(Transaction.date >= start_date)
			.where(Transaction.date <= end_date)
			.order_by(Transaction.date.asc(), Transaction.transaction_id.asc())
		)
		return list(session.exec(statement).all())
