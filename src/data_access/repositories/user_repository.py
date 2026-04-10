from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import User


# Kapselt reine Datenbankzugriffe fuer Benutzer.
class UserRepository:
	# Laedt einen User per Vertragsnummer.
	@staticmethod
	def get_by_contract_number(session: Session, contract_number: str) -> User | None:
		statement = select(User).where(User.contract_number == contract_number)
		return session.exec(statement).first()

	# Laedt einen User per ID.
	@staticmethod
	def get_by_id(session: Session, user_id: int) -> User | None:
		return session.get(User, user_id)

	# Persistiert Aenderungen eines Users.
	@staticmethod
	def save(session: Session, user: User) -> User:
		session.add(user)
		session.commit()
		session.refresh(user)
		return user
