"""src.data_access.repositories.recurring_repository

Dieses Repository kapselt Datenbankzugriffe für Daueraufträge
(`RecurringTransaction`). Daueraufträge hängen an einem Konto, daher wird für
"alle Daueraufträge eines Users" über `accounts` gejoint.

Wichtig: Ob ein Dauerauftrag wirklich *heute* fällig ist, ist Fachlogik
(Intervall, letztes Ausführungsdatum, optionales Enddatum). Darum liefert
`list_due_by_user()` bewusst nur "potenziell fällige" Einträge; der Service
entscheidet dann, ob wirklich ausgeführt wird.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Account, RecurringTransaction


# Kapselt reine Datenbankzugriffe fuer Dauerauftraege.
class RecurringRepository:
	"""Datenbankzugriffe fuer `RecurringTransaction`-Objekte.

	Hinweis:
		Die Methoden committen die Session selbst (create/save/delete). Dadurch ist
		das Repository in dieser App unkompliziert nutzbar.
	"""
	def __init__(self, session: Session):
		"""Initialisiert das Repository mit einer DB-Session.

		Args:
			session: Offene SQLModel-Session.
		"""
		self.session = session

	# Legt einen Dauerauftrag an und persistiert ihn.
	def create(self, recurring: RecurringTransaction) -> RecurringTransaction:
		"""Speichert einen neuen Dauerauftrag.

		Args:
			recurring: Neues Dauerauftrag-Objekt.

		Returns:
			Gespeicherter Dauerauftrag.
		"""
		self.session.add(recurring)
		self.session.commit()
		self.session.refresh(recurring)
		return recurring

	# Laedt einen Dauerauftrag per ID.
	def get_by_id(self, recurring_id: int) -> RecurringTransaction | None:
		"""Lädt einen Dauerauftrag per ID.

		Args:
			recurring_id: Primärschlüssel.

		Returns:
			Dauerauftrag oder `None`.
		"""
		return self.session.get(RecurringTransaction, recurring_id)

	# Gibt alle Dauerauftraege eines Users zurueck.
	def list_by_user(self, user_id: int) -> list[RecurringTransaction]:
		"""Listet alle Daueraufträge eines Users.

		Args:
			user_id: User-ID.

		Returns:
			Liste aller Daueraufträge.
		"""
		# Join über Account, weil RecurringTransaction nur `account_id` speichert.
		statement = (
			select(RecurringTransaction)
			.join(Account, Account.account_id == RecurringTransaction.account_id)
			.where(Account.user_id == user_id)
		)
		return list(self.session.exec(statement).all())

	# Gibt potenziell faellige Dauerauftraege eines Users zurueck.
	def list_due_by_user(
		self,
		user_id: int,
		reference_date: date,
	) -> list[RecurringTransaction]:
		"""Listet Daueraufträge, die *theoretisch* bis zu einem Datum startbar sind.

		Diese Query prüft nur: `start_date <= reference_date`.
		Alles Weitere (Intervall, last_executed, optionales end_date) entscheidet der
		Service, weil das Geschäftslogik ist.

		Args:
			user_id: User-ID.
			reference_date: Stichtag (meist "heute" beim Login).

		Returns:
			Liste potenziell fälliger Daueraufträge.
		"""
		statement = (
			select(RecurringTransaction)
			.join(Account, Account.account_id == RecurringTransaction.account_id)
			.where(Account.user_id == user_id)
			# Startdatum muss erreicht sein, sonst kann nichts fällig werden.
			.where(RecurringTransaction.start_date <= reference_date)
		)
		return list(self.session.exec(statement).all())

	# Persistiert Aenderungen eines Dauerauftrags.
	def save(self, recurring: RecurringTransaction) -> RecurringTransaction:
		"""Speichert Aenderungen an einem Dauerauftrag.

		Args:
			recurring: Dauerauftrag mit geaenderten Feldern.

		Returns:
			Aktualisierter Dauerauftrag (nach Commit/Refresh).
		"""
		self.session.add(recurring)
		self.session.commit()
		self.session.refresh(recurring)
		return recurring

	# Loescht einen Dauerauftrag per ID.
	def delete(self, recurring_id: int) -> None:
		"""Loescht einen Dauerauftrag, falls er existiert.

		Args:
			recurring_id: ID des zu loeschenden Dauerauftrags.
		"""
		recurring = self.session.get(RecurringTransaction, recurring_id)
		if recurring is not None:
			self.session.delete(recurring)
			self.session.commit()
