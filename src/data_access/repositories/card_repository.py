from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import CreditCard, DebitCard


# Kapselt reine Datenbankzugriffe fuer Debit- und Kreditkarten.
class CardRepository:
	def __init__(self, session: Session):
		self.session = session

	# Laedt eine Debitkarte per ID.
	def get_debit_by_id(self, card_id: int) -> DebitCard | None:
		return self.session.get(DebitCard, card_id)

	# Laedt eine Kreditkarte per ID.
	def get_credit_by_id(self, creditcard_id: int) -> CreditCard | None:
		return self.session.get(CreditCard, creditcard_id)

	# Gibt alle Debitkarten eines Kontos zurueck.
	def list_debit_by_account(self, account_id: int) -> list[DebitCard]:
		statement = select(DebitCard).where(DebitCard.account_id == account_id)
		return list(self.session.exec(statement).all())

	# Gibt alle aktiven Debitkarten eines Kontos zurueck.
	def list_active_debit_by_account(self, account_id: int) -> list[DebitCard]:
		statement = select(DebitCard).where(
			DebitCard.account_id == account_id,
			DebitCard.status == "aktiv",
		)
		return list(self.session.exec(statement).all())

	# Legt eine Debitkarte an und persistiert sie.
	def create_debit(self, card: DebitCard) -> DebitCard:
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card

	# Persistiert Aenderungen einer Debitkarte.
	def save_debit(self, card: DebitCard) -> DebitCard:
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card

	# Gibt alle Debitkarten eines Users zurueck (via Account-Join).
	def list_debit_by_user(self, user_id: int) -> list[DebitCard]:
		from src.domain.models import Account
		statement = (
			select(DebitCard)
			.join(Account, Account.account_id == DebitCard.account_id)
			.where(Account.user_id == user_id)
		)
		return list(self.session.exec(statement).all())

	# Gibt alle Kreditkarten eines Users zurueck.
	def list_credit_by_user(self, user_id: int) -> list[CreditCard]:
		statement = select(CreditCard).where(CreditCard.user_id == user_id)
		return list(self.session.exec(statement).all())

	# Legt eine Kreditkarte an und persistiert sie.
	def create_credit(self, card: CreditCard) -> CreditCard:
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card

	# Persistiert Aenderungen einer Kreditkarte.
	def save_credit(self, card: CreditCard) -> CreditCard:
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card
