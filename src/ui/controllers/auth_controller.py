"""src.ui.controllers.auth_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Controller in dieser App sind die "Klebstoff"-Schicht zwischen Views (NiceGUI)
und Services:

- Views rufen Controller-Methoden auf.
- Controller rufen Service-Methoden auf.
- Controller kuemmern sich um einfache Fehlerbehandlung und geben Ergebnisse in
	einem Format zurueck, das die UI leicht anzeigen kann.

Wichtig: Der Controller enthaelt *keine* Datenbanklogik und moeglichst wenig
fachliche Regeln. Die Regeln liegen in den Services.
"""

from __future__ import annotations

from src.services.auth_service import auth_service


# Orchestriert Login-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AuthController:
	"""UI-Controller fuer Authentifizierung (Login-Use-Case)."""

	# Fuehrt den Login durch und liefert Ergebnis oder Fehlermeldung.
	def login(self, contract_number: str, password: str) -> dict | str:
		"""Fuehrt den Login durch.

		Die UI moechte meist nicht mit Exceptions arbeiten, sondern mit einem
		"Ergebnisobjekt". Deshalb wird hier jede Exception abgefangen und als
		String zurueckgegeben.

		Args:
			contract_number: Vertragsnummer als Login-Identifikator.
			password: Passwort im Klartext (wird im Service geprueft und nie gespeichert).

		Returns:
			Entweder ein Dict mit Login-Ergebnis (z.B. Userdaten) oder eine
			Fehlermeldung als String.
		"""
		try:
			return auth_service.login(contract_number, password)
		except Exception as error:
			return str(error)

	# Gibt den vollstaendigen Namen eines Users zurueck.
	def get_username(self, user_id: int) -> str:
		"""Hilfsfunktion fuer die UI: liefert einen Anzeigenamen.

		Args:
			user_id: ID des eingeloggten Users.

		Returns:
			Vollstaendiger Name fuer die Anzeige oder ein leerer String bei Fehlern.
		"""
		try:
			return auth_service.get_full_name(user_id)
		except Exception:
			return ""


auth_controller = AuthController()
