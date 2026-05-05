"""User-Funktionen (Service-Schicht).

Dieses Modul enthält die Service-Logik rund um Benutzer-Profile.
Es gehört zur Service-Schicht, weil es den Ablauf steuert (Session öffnen,
Repository aufrufen) und so UI/Controller von Datenbankdetails trennt.
Es arbeitet mit `UserRepository` und nutzt die DB-Engine aus `data_access.db`.
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
		# Service-Schicht: Session/Transaktion steuern, DB-Details ans Repository delegieren.
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
		# Repository kümmert sich um "User laden → Felder setzen → speichern".
		with Session(engine) as session:
			return UserRepository(session).update_profile(user_id, phone, address)


user_service = UserService()
