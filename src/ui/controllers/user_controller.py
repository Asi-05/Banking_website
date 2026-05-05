"""src.ui.controllers.user_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Der UserController stellt Methoden fuer das Benutzerprofil bereit
(Anzeige/Aktualisierung von Telefon und Adresse).

Wie bei den anderen Controllern gilt:
- Business-Regeln und Persistenz liegen im Service/Repository.
- Der Controller faengt Exceptions ab und liefert fuer die UI einfache
	Rueckgabewerte (Objekt oder Fehlertext).
"""

from src.services.user_service import user_service


class UserController:
	"""UI-Controller fuer Profil-Operationen."""

	def get_profile(self, user_id: int):
		"""Laedt das Benutzerprofil.

		Args:
			user_id: ID des eingeloggten Users.

		Returns:
			User-Objekt bei Erfolg, sonst Fehlermeldung als String.
		"""
		try:
			return user_service.get_profile(user_id)
		except Exception as e:
			return str(e)

	def update_profile(self, user_id: int, phone: str | None, address: str | None) -> str | None:
		"""Aktualisiert Telefon und/oder Adresse.

		Args:
			user_id: ID des eingeloggten Users.
			phone: Neue Telefonnummer oder `None` (unveraendert lassen).
			address: Neue Adresse oder `None` (unveraendert lassen).

		Returns:
			`None` bei Erfolg, sonst Fehlermeldung als String.
		"""
		try:
			user_service.update_profile(user_id, phone, address)
			return None
		except Exception as e:
			return str(e)


user_controller = UserController()
