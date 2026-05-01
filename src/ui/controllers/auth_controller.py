from __future__ import annotations

from src.services.auth_service import auth_service


# Orchestriert Login-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AuthController:
	# Fuehrt den Login durch und liefert Ergebnis oder Fehlermeldung.
	def login(self, contract_number: str, password: str) -> dict | str:
		try:
			return auth_service.login(contract_number, password)
		except Exception as error:
			return str(error)

	# Gibt den vollstaendigen Namen eines Users zurueck.
	def get_username(self, user_id: int) -> str:
		try:
			return auth_service.get_full_name(user_id)
		except Exception:
			return ""


auth_controller = AuthController()
