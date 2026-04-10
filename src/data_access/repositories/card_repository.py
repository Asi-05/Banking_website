from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import CreditCard, DebitCard


# Kapselt reine Datenbankzugriffe fuer Debit- und Kreditkarten.
class CardRepository:
	# Laedt eine Debitkarte per ID.
	@staticmethod
	def get_debit_by_id(session: Session, card_id: int) -> DebitCard | None:
		return session.get(DebitCard, card_id)

	# Laedt eine Kreditkarte per ID.
	@staticmethod
	def get_credit_by_id(session: Session, creditcard_id: int) -> CreditCard | None:
		return session.get(CreditCard, creditcard_id)

	# Gibt alle Debitkarten eines Kontos zurueck.
	@staticmethod
	def list_debit_by_account(session: Session, account_id: int) -> list[DebitCard]:
		statement = select(DebitCard).where(DebitCard.account_id == account_id)
		return list(session.exec(statement).all())

	# Gibt alle aktiven Debitkarten eines Kontos zurueck.
	@staticmethod
	def list_active_debit_by_account(session: Session, account_id: int) -> list[DebitCard]:
		statement = select(DebitCard).where(
			DebitCard.account_id == account_id,
			DebitCard.status == "aktiv",
		)
		return list(session.exec(statement).all())

	# Legt eine Debitkarte an und persistiert sie.
	@staticmethod
	def create_debit(session: Session, card: DebitCard) -> DebitCard:
		session.add(card)
		session.commit()
		session.refresh(card)
		return card

	# Persistiert Aenderungen einer Debitkarte.
	@staticmethod
	def save_debit(session: Session, card: DebitCard) -> DebitCard:
		session.add(card)
		session.commit()
		session.refresh(card)
		return card

	# Gibt alle Kreditkarten eines Users zurueck.
	@staticmethod
	def list_credit_by_user(session: Session, user_id: int) -> list[CreditCard]:
		statement = select(CreditCard).where(CreditCard.user_id == user_id)
		return list(session.exec(statement).all())

	# Legt eine Kreditkarte an und persistiert sie.
	@staticmethod
	def create_credit(session: Session, card: CreditCard) -> CreditCard:
		session.add(card)
		session.commit()
		session.refresh(card)
		return card

	# Persistiert Aenderungen einer Kreditkarte.
	@staticmethod
	def save_credit(session: Session, card: CreditCard) -> CreditCard:
		session.add(card)
		session.commit()
		session.refresh(card)
		return card
