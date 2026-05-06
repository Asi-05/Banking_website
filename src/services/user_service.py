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
		"""Laedt die Profildaten eines Users.

		Args:
			user_id: ID des Users.

		Returns:
			User-Objekt (ORM-Model) mit Profildaten oder `None`, wenn der User
			nicht existiert.
		"""
		# Service-Schicht: Session/Transaktion steuern, DB-Details ans Repository delegieren.
		with Session(engine) as session:
			return UserRepository(session).get_by_id(user_id)

	def update_profile(self, user_id: int, phone: str | None, address: str | None):
		"""Aktualisiert Profildaten eines Users (Telefon und/oder Adresse).

		Args:
			user_id: ID des Users.
			phone: Neue Telefonnummer oder `None` (dann nicht aendern).
			address: Neue Adresse oder `None` (dann nicht aendern).

		Returns:
			Das aktualisierte User-Objekt.

		Raises:
			KeyError: Wenn der User nicht gefunden wurde.
		"""
		# Repository kümmert sich um "User laden → Felder setzen → speichern".
		with Session(engine) as session:
			return UserRepository(session).update_profile(user_id, phone, address)


user_service = UserService()
