from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Account


# Kapselt reine Datenbankzugriffe fuer Konten.
class AccountRepository:
	# Legt ein neues Konto an und persistiert es.
	@staticmethod
	def create(session: Session, account: Account) -> Account:
		session.add(account)
		session.commit()
		session.refresh(account)
		return account

	# Laedt ein Konto anhand der ID.
	@staticmethod
	def get_by_id(session: Session, account_id: int) -> Account | None:
		return session.get(Account, account_id)

	# Laedt ein Konto anhand der IBAN.
	@staticmethod
	def get_by_iban(session: Session, iban: str) -> Account | None:
		statement = select(Account).where(Account.iban == iban)
		return session.exec(statement).first()

	# Gibt alle Konten eines Users zurueck.
	@staticmethod
	def list_by_user(session: Session, user_id: int) -> list[Account]:
		statement = select(Account).where(Account.user_id == user_id)
		return list(session.exec(statement).all())

	# Persistiert Aenderungen eines Kontos.
	@staticmethod
	def save(session: Session, account: Account) -> Account:
		session.add(account)
		session.commit()
		session.refresh(account)
		return account
