"""src.data_access.repositories.user_repository

Repository fuer Benutzer-Datenbankzugriffe (Data-Access-Schicht).

Ein Repository kapselt **nur** Datenbankzugriffe: laden, speichern, einfache
Queries. Es enthaelt keine Fachlogik (Regeln), weil diese in der Service-Schicht
leben soll.

Dieses Repository wird z. B. von Auth-/UI-Logik genutzt, um User anhand von ID
oder Vertragsnummer zu finden und Profildaten zu aktualisieren.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import User


# Kapselt reine Datenbankzugriffe fuer Benutzer.
class UserRepository:
	"""Datenbankzugriffe für `User`-Objekte.

	Attributes:
		session: Offene SQLModel-Session, über die alle Queries laufen.
	"""
	# Hinweis: Methoden committen die Session selbst (save/update_profile).
	def __init__(self, session: Session):
		"""Erstellt ein Repository mit einer vorhandenen DB-Session.

		Args:
			session: Eine bereits geöffnete Datenbank-Session.
		"""
		self.session = session

	# Laedt einen User per Vertragsnummer.
	def get_by_contract_number(self, contract_number: str) -> User | None:
		"""Lädt einen User anhand der Vertragsnummer.

		Args:
			contract_number: Eindeutige Vertragsnummer (z. B. "BB-100001").

		Returns:
			Den gefundenen User oder `None`, falls es keinen gibt.
		"""
		# SELECT ... WHERE contract_number = :contract_number
		statement = select(User).where(User.contract_number == contract_number)
		return self.session.exec(statement).first()

	# Laedt einen User per ID.
	def get_by_id(self, user_id: int) -> User | None:
		"""Lädt einen User anhand der Primärschlüssel-ID.

		Args:
			user_id: Primärschlüssel aus der Tabelle `users`.

		Returns:
			Den User oder `None`, falls nicht vorhanden.
		"""
		return self.session.get(User, user_id)

	# Persistiert Aenderungen eines Users.
	def save(self, user: User) -> User:
		"""Speichert einen User (neu oder geändert) in der Datenbank.

		Ablauf:
		- `add()` markiert das Objekt für die Session
		- `commit()` schreibt die Änderungen in die DB
		- `refresh()` lädt DB-generierte Werte (z. B. `user_id`) zurück ins Objekt

		Args:
			user: Das User-Objekt, das gespeichert werden soll.

		Returns:
			Das gespeicherte (aktualisierte) User-Objekt.
		"""
		self.session.add(user)
		self.session.commit()
		self.session.refresh(user)
		return user

	# Aktualisiert Profildaten eines Users (Telefon und Adresse).
	def update_profile(self, user_id: int, phone: str | None, address: str | None) -> User:
		"""Aktualisiert Telefon und/oder Adresse eines Users.

		Args:
			user_id: ID des Users.
			phone: Neue Telefonnummer oder `None`, um sie unverändert zu lassen.
			address: Neue Adresse oder `None`, um sie unverändert zu lassen.

		Returns:
			Den gespeicherten User nach der Aktualisierung.

		Raises:
			KeyError: Wenn es keinen User mit dieser ID gibt.
		"""
		user = self.get_by_id(user_id)
		if user is None:
			raise KeyError(f"User {user_id} nicht gefunden")
		# Nur Felder überschreiben, die wirklich gesetzt wurden.
		if phone is not None:
			user.phone = phone
		if address is not None:
			user.address = address
		return self.save(user)
