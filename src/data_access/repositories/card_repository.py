"""src.data_access.repositories.card_repository

Repository fuer Debitkarten- und Kreditkarten-Datenbankzugriffe.

Dieses Repository kapselt DB-Operationen fuer zwei unterschiedliche Kartentypen:

- Debitkarten (`DebitCard`) gehoeren immer zu genau einem Konto (`Account`).
- Kreditkarten (`CreditCard`) gehoeren direkt zu einem User und haben einen
  eigenen `balance` (genutzter Kredit). Dieser Wert ist **kein** Kontostand.

Services (z.B. CardService und CreditCardBillingService) verwenden dieses
Repository, um Karten zu laden, zu erstellen und Status/Saldo zu speichern.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import CreditCard, DebitCard


# Kapselt reine Datenbankzugriffe fuer Debit- und Kreditkarten.
class CardRepository:
	"""Datenbankzugriffe fuer Debit- und Kreditkarten.

	Hinweis:
		Die Methoden committen die Session selbst (create/save). Dadurch ist das
		Repository leicht zu benutzen, aber Transaktionen werden nicht ueber mehrere
		Aufrufe hinweg gebuendelt.
	"""
	def __init__(self, session: Session):
		"""Initialisiert das Repository mit einer DB-Session.

		Args:
			session: Offene SQLModel-Session.
		"""
		self.session = session

	# Laedt eine Debitkarte per ID.
	def get_debit_by_id(self, card_id: int) -> DebitCard | None:
		"""Lädt eine Debitkarte per ID.

		Args:
			card_id: Primärschlüssel der Debitkarte.

		Returns:
			Debitkarte oder `None`.
		"""
		return self.session.get(DebitCard, card_id)

	# Laedt eine Kreditkarte per ID.
	def get_credit_by_id(self, creditcard_id: int) -> CreditCard | None:
		"""Lädt eine Kreditkarte per ID.

		Args:
			creditcard_id: Primärschlüssel der Kreditkarte.

		Returns:
			Kreditkarte oder `None`.
		"""
		return self.session.get(CreditCard, creditcard_id)

	# Gibt alle Debitkarten eines Kontos zurueck.
	def list_debit_by_account(self, account_id: int) -> list[DebitCard]:
		"""Listet alle Debitkarten eines Kontos.

		Args:
			account_id: Konto-ID.

		Returns:
			Liste der Debitkarten (unabhängig vom Status).
		"""
		statement = select(DebitCard).where(DebitCard.account_id == account_id)
		return list(self.session.exec(statement).all())

	# Gibt alle aktiven Debitkarten eines Kontos zurueck.
	def list_active_debit_by_account(self, account_id: int) -> list[DebitCard]:
		"""Listet nur aktive Debitkarten eines Kontos.

		Args:
			account_id: Konto-ID.

		Returns:
			Liste aktiver Debitkarten.
		"""
		statement = select(DebitCard).where(
			DebitCard.account_id == account_id,
			DebitCard.status == "aktiv",
		)
		return list(self.session.exec(statement).all())

	# Legt eine Debitkarte an und persistiert sie.
	def create_debit(self, card: DebitCard) -> DebitCard:
		"""Erstellt eine neue Debitkarte.

		Args:
			card: Neue Debitkarte.

		Returns:
			Gespeicherte Debitkarte.
		"""
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card

	# Persistiert Aenderungen einer Debitkarte.
	def save_debit(self, card: DebitCard) -> DebitCard:
		"""Speichert Aenderungen an einer Debitkarte (z. B. Status).

		Args:
			card: Debitkarte mit geaenderten Feldern.

		Returns:
			Aktualisierte Debitkarte (nach Commit/Refresh).
		"""
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card

	# Gibt alle Debitkarten eines Users zurueck (via Account-Join).
	def list_debit_by_user(self, user_id: int) -> list[DebitCard]:
		"""Listet alle Debitkarten eines Users.

		Debitkarten hängen am Konto. Darum muss diese Query über `accounts` joinen,
		um vom User zur Karte zu kommen.

		Args:
			user_id: User-ID.

		Returns:
			Liste der Debitkarten.
		"""
		from src.domain.models import Account
		# SELECT debit_cards JOIN accounts WHERE accounts.user_id = :user_id
		statement = (
			select(DebitCard)
			.join(Account, Account.account_id == DebitCard.account_id)
			.where(Account.user_id == user_id)
		)
		return list(self.session.exec(statement).all())

	# Gibt alle Kreditkarten eines Users zurueck.
	def list_credit_by_user(self, user_id: int) -> list[CreditCard]:
		"""Listet alle Kreditkarten eines Users.

		Args:
			user_id: User-ID.

		Returns:
			Liste der Kreditkarten.
		"""
		statement = select(CreditCard).where(CreditCard.user_id == user_id)
		return list(self.session.exec(statement).all())

	# Legt eine Kreditkarte an und persistiert sie.
	def create_credit(self, card: CreditCard) -> CreditCard:
		"""Erstellt eine neue Kreditkarte.

		Args:
			card: Neue Kreditkarte.

		Returns:
			Gespeicherte Kreditkarte (nach Commit/Refresh).
		"""
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card

	# Persistiert Aenderungen einer Kreditkarte.
	def save_credit(self, card: CreditCard) -> CreditCard:
		"""Speichert Aenderungen an einer Kreditkarte (z. B. Status, balance).

		Args:
			card: Kreditkarte mit geaenderten Feldern.

		Returns:
			Aktualisierte Kreditkarte (nach Commit/Refresh).
		"""
		self.session.add(card)
		self.session.commit()
		self.session.refresh(card)
		return card
