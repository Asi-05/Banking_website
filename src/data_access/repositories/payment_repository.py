from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Payment, Transaction, Transfer


# Kapselt reine Datenbankzugriffe fuer Zahlungsobjekte.
class PaymentRepository:
	def __init__(self, session: Session):
		self.session = session

	# Legt ein Payment-Objekt an und persistiert es.
	def create_payment(self, payment: Payment) -> Payment:
		self.session.add(payment)
		self.session.commit()
		self.session.refresh(payment)
		return payment

	# Legt ein Transfer-Objekt an und persistiert es.
	def create_transfer(self, transfer: Transfer) -> Transfer:
		self.session.add(transfer)
		self.session.commit()
		self.session.refresh(transfer)
		return transfer

	# Gibt alle kontobezogenen Transaktionen in einem Datumsbereich zurueck.
	def list_account_transactions_in_range(
		self,
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
		return list(self.session.exec(statement).all())
