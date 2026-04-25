from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Account


# Kapselt reine Datenbankzugriffe fuer Konten.
class AccountRepository:
	def __init__(self, session: Session):
		self.session = session

	# Legt ein neues Konto an und persistiert es.
	def create(self, account: Account) -> Account:
		self.session.add(account)
		self.session.commit()
		self.session.refresh(account)
		return account

	# Laedt ein Konto anhand der ID.
	def get_by_id(self, account_id: int) -> Account | None:
		return self.session.get(Account, account_id)

	# Laedt ein Konto anhand der IBAN.
	def get_by_iban(self, iban: str) -> Account | None:
		statement = select(Account).where(Account.iban == iban)
		return self.session.exec(statement).first()

	# Gibt alle Konten eines Users zurueck.
	def list_by_user(self, user_id: int) -> list[Account]:
		statement = select(Account).where(Account.user_id == user_id)
		return list(self.session.exec(statement).all())

	# Persistiert Aenderungen eines Kontos.
	def save(self, account: Account) -> Account:
		self.session.add(account)
		self.session.commit()
		self.session.refresh(account)
		return account
