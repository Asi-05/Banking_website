from __future__ import annotations

from src.services.account_service import account_service


# Orchestriert Konto-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AccountController:
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
