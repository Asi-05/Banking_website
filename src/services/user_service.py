"""
User Service - Betterbank Banking App
Verwaltet Geschäftslogik für Benutzerdaten und Profiländerungen.
"""

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from sqlmodel import Session


class UserService:
	"""Service für Benutzerverwaltung und Profilbearbeitung."""

	def get_profile(self, user_id: int):
		"""
		Lädt die Profildaten eines Users.
		
		Args:
		    user_id: ID des Users
		    
		Returns:
		    User-Objekt mit Profildaten oder None
		"""
		with Session(engine) as session:
			return UserRepository(session).get_by_id(user_id)

	def update_profile(self, user_id: int, phone: str | None, address: str | None):
		"""
		Aktualisiert die Profildaten eines Users (Telefon, Adresse).
		
		Args:
		    user_id: ID des Users
		    phone: Neue Telefonnummer (optional)
		    address: Neue Wohnadresse (optional)
		    
		Returns:
		    Aktualisiertes User-Objekt
		    
		Raises:
		    KeyError: User nicht gefunden
		"""
		with Session(engine) as session:
			return UserRepository(session).update_profile(user_id, phone, address)


user_service = UserService()
