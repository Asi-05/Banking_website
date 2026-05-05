"""src.data_access.repositories.account_repository

Repository fuer Konto-Datenbankzugriffe (Data-Access-Schicht).

Dieses Repository kapselt die direkten DB-Operationen fuer `Account`.
Es wird von Services genutzt, um Konten zu finden (z. B. per IBAN) und
Aenderungen am Kontostand/Status zu speichern.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Account


# Kapselt reine Datenbankzugriffe fuer Konten.
class AccountRepository:
	"""Datenbankzugriffe fuer `Account`-Objekte.

	Hinweis:
		Die Methoden committen die Session selbst (create/save). Dadurch ist das
		Repository in dieser App unkompliziert nutzbar, aber Transaktionen werden
		nicht ueber mehrere Aufrufe hinweg gebuendelt.
	"""
	def __init__(self, session: Session):
		"""Initialisiert das Repository mit einer DB-Session.

		Args:
			session: Offene SQLModel-Session.
		"""
		self.session = session

	# Legt ein neues Konto an und persistiert es.
	def create(self, account: Account) -> Account:
		"""Legt ein neues Konto an.

		Args:
			account: Das neue Konto-Objekt.

		Returns:
			Das gespeicherte Konto (inkl. DB-generierter `account_id`).
		"""
		self.session.add(account)
		self.session.commit()
		self.session.refresh(account)
		return account

	# Laedt ein Konto anhand der ID.
	def get_by_id(self, account_id: int) -> Account | None:
		"""Lädt ein Konto per Primärschlüssel.

		Args:
			account_id: ID des Kontos.

		Returns:
			Konto oder `None`.
		"""
		return self.session.get(Account, account_id)

	# Laedt ein Konto anhand der IBAN.
	def get_by_iban(self, iban: str) -> Account | None:
		"""Lädt ein Konto anhand der IBAN.

		Args:
			iban: IBAN-String.

		Returns:
			Konto oder `None`, falls keine IBAN passt.
		"""
		# SELECT ... WHERE iban = :iban
		statement = select(Account).where(Account.iban == iban)
		return self.session.exec(statement).first()

	# Gibt alle Konten eines Users zurueck.
	def list_by_user(self, user_id: int) -> list[Account]:
		"""Listet alle Konten eines Users.

		Args:
			user_id: ID des Users.

		Returns:
			Liste aller Konten (auch geschlossene, falls vorhanden).
		"""
		# SELECT ... WHERE user_id = :user_id
		statement = select(Account).where(Account.user_id == user_id)
		return list(self.session.exec(statement).all())

	# Persistiert Aenderungen eines Kontos.
	def save(self, account: Account) -> Account:
		"""Speichert Änderungen an einem Konto (z. B. Saldo/Status).

		Args:
			account: Geändertes Konto-Objekt.

		Returns:
			Aktualisiertes Konto-Objekt nach `commit()`/`refresh()`.
		"""
		self.session.add(account)
		self.session.commit()
		self.session.refresh(account)
		return account
