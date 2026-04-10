from __future__ import annotations

import secrets
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from src.services.recurring_service import recurring_service
from src.utils.validators import verify_password


# Implementiert die Geschaeftslogik fuer Authentifizierung.
class AuthService:
	# Authentifiziert einen User und verarbeitet faellige Dauerauftraege.
	def login(self, contract_number: str, password: str) -> dict:
		with Session(engine) as session:
			user = UserRepository.get_by_contract_number(session, contract_number)
			if user is None:
				raise ValueError("Ungueltige Anmeldedaten")

			stored_hash = user.password_hash
			password_ok = (
				verify_password(password, stored_hash)
				if "$" in stored_hash
				else stored_hash == password
			)
			if not password_ok:
				raise ValueError("Ungueltige Anmeldedaten")

		executed_recurring = recurring_service.process_due_recurring_on_login(
			user.user_id,
			date.today(),
		)
		return {
			"success": True,
			"auth_token": secrets.token_urlsafe(24),
			"user_id": user.user_id,
			"executed_recurring": executed_recurring,
		}


auth_service = AuthService()
