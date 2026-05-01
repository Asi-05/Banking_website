from __future__ import annotations

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from sqlmodel import Session

from src.services.account_service import account_service


# Orchestriert Konto-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AccountController:
	# Liefert den vollstaendigen Namen des aktuellen Users oder None.
	def get_current_user_display_name(self, user_id: int) -> str | None:
		try:
			with Session(engine) as session:
				user = UserRepository(session).get_by_id(user_id)
				if user is None:
					return None
				return f"{user.first_name} {user.last_name}"
		except Exception:
			return None

	# Fuehrt die Kontoeroeffnung aus.
	def open_account(self, payload: dict) -> str | None:
		try:
			account_service.open_account(payload)
			return None
		except Exception as error:
			return str(error)

	# Fuehrt die Kontoschliessung gemaess Business-Regeln aus.
	def close_account(self, account_id: int) -> str | None:
		try:
			account_service.close_account(account_id)
			return None
		except Exception as error:
			return str(error)

	# Liefert Kontenliste oder Fehlermeldung.
	def list_accounts(self, user_id: int) -> list | str:
		try:
			return account_service.list_accounts(user_id)
		except Exception as error:
			return str(error)


account_controller = AccountController()
