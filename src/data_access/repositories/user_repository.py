from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import User


# Kapselt reine Datenbankzugriffe fuer Benutzer.
class UserRepository:
	def __init__(self, session: Session):
		self.session = session

	# Laedt einen User per Vertragsnummer.
	def get_by_contract_number(self, contract_number: str) -> User | None:
		statement = select(User).where(User.contract_number == contract_number)
		return self.session.exec(statement).first()

	# Laedt einen User per ID.
	def get_by_id(self, user_id: int) -> User | None:
		return self.session.get(User, user_id)

	# Persistiert Aenderungen eines Users.
	def save(self, user: User) -> User:
		self.session.add(user)
		self.session.commit()
		self.session.refresh(user)
		return user

	# Aktualisiert Profildaten eines Users (E-Mail und Adresse).
	def update_profile(self, user_id: int, email: str | None, address: str | None) -> User:
		user = self.get_by_id(user_id)
		if user is None:
			raise KeyError(f"User {user_id} nicht gefunden")
		if email is not None:
			user.email = email
		if address is not None:
			user.address = address
		return self.save(user)
