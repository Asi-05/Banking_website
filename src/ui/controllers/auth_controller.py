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


auth_controller = AuthController()
