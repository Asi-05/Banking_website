"""
User Controller - Betterbank Banking App
Vermittelt zwischen UI und UserService für Profilbearbeitung.
"""

from src.services.user_service import user_service


class UserController:
	"""Controller für Benutzerprofil-Operationen."""

	def get_profile(self, user_id: int):
		"""
		Lädt das Benutzerprofil.
		
		Args:
		    user_id: ID des Users
		    
		Returns:
		    User-Objekt oder Fehlermeldung (str)
		"""
		try:
			return user_service.get_profile(user_id)
		except Exception as e:
			return str(e)

	def update_profile(self, user_id: int, email: str | None, address: str | None) -> str | None:
		"""
		Aktualisiert das Benutzerprofil (E-Mail, Adresse).
		
		Args:
		    user_id: ID des Users
		    email: Neue E-Mail (optional)
		    address: Neue Wohnadresse (optional)
		    
		Returns:
		    None bei Erfolg, Fehlermeldung (str) bei Fehler
		"""
		try:
			user_service.update_profile(user_id, email, address)
			return None
		except Exception as e:
			return str(e)


user_controller = UserController()
