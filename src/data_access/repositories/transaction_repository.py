"""src.data_access.repositories.transaction_repository

Repository fuer Transaktions-Datenbankzugriffe (Data-Access-Schicht).

Dieses Repository kapselt alle DB-Operationen rund um `Transaction` und wird
vom TransactionService genutzt, um Transaktionen zu erstellen, zu speichern,
zu loeschen und zu filtern.

Ownership-/Join-Hintergrund:
	Eine Transaktion kann genau **eine** Belastungsquelle haben:
	Konto ODER Debitkarte ODER Kreditkarte.
	Fuer die Filterung nach User muessen deshalb mehrere (outer) Joins
	verwendet werden, um eine Transaktion korrekt einem User zuzuordnen.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Transaction


# Kapselt reine Datenbankzugriffe fuer Transaktionen.
class TransactionRepository:
	"""Datenbankzugriffe fuer `Transaction`-Objekte.

	Hinweis:
		Die Methoden committen die Session selbst (create/save/delete). Dadurch ist
		das Repository einfach zu verwenden, aber Transaktionen werden nicht ueber
		mehrere Repository-Aufrufe hinweg gebuendelt.
	"""
	def __init__(self, session: Session):
		"""Initialisiert das Repository mit einer DB-Session.

		Args:
			session: Offene SQLModel-Session.
		"""
		self.session = session

	# Legt eine Transaktion an und persistiert sie.
	def create(self, transaction: Transaction) -> Transaction:
		"""Speichert eine neue Transaktion in der Datenbank.

		Args:
			transaction: Neue Transaktion.

		Returns:
			Die gespeicherte Transaktion (inkl. DB-generierter `transaction_id`).
		"""
		self.session.add(transaction)
		self.session.commit()
		self.session.refresh(transaction)
		return transaction

	# Laedt eine Transaktion per ID.
	def get_by_id(self, transaction_id: int) -> Transaction | None:
		"""Lädt eine Transaktion anhand ihrer ID.

		Args:
			transaction_id: Primärschlüssel.

		Returns:
			Transaktion oder `None`.
		"""
		return self.session.get(Transaction, transaction_id)

	# Persistiert Aenderungen an einer Transaktion.
	def save(self, transaction: Transaction) -> Transaction:
		"""Speichert Änderungen an einer Transaktion.

		Args:
			transaction: Geänderte Transaktion.

		Returns:
			Aktualisierte Transaktion nach `commit()`/`refresh()`.
		"""
		self.session.add(transaction)
		self.session.commit()
		self.session.refresh(transaction)
		return transaction

	# Loescht eine Transaktion endgueltig.
	def delete(self, transaction: Transaction) -> None:
		"""Löscht eine Transaktion dauerhaft aus der Datenbank.

		Args:
			transaction: Die zu löschende Transaktion.
		"""
		self.session.delete(transaction)
		self.session.commit()

	# Filtert Transaktionen optional nach Zeitraum, Kategorie und User-Zuordnung.
	def filter_transactions(
		self,
		start_date: date | None = None,
		end_date: date | None = None,
		category_id: int | None = None,
		user_id: int | None = None,
	) -> list[Transaction]:
		"""Filtert Transaktionen nach Datum, Kategorie und optional nach User.

		Wenn `user_id` gesetzt ist, wird ueber mehrere (outer) Joins gefiltert,
		weil eine Transaktion ihre Quelle in unterschiedlichen Spalten speichern
		kann (Account/DebitCard/CreditCard). Fuer den Account-Join ueber DebitCard
		wird ein Alias verwendet, damit `accounts` zweimal gejoint werden kann.

		Args:
			start_date: Wenn gesetzt, nur Transaktionen ab diesem Datum (inkl.).
			end_date: Wenn gesetzt, nur Transaktionen bis zu diesem Datum (inkl.).
			category_id: Wenn gesetzt, nur Transaktionen dieser Kategorie.
			user_id: Wenn gesetzt, nur Transaktionen, die dem User gehören.

		Returns:
			Liste der passenden Transaktionen (neueste zuerst).
		"""
		# Basis-Query: alle Transaktionen, danach bauen wir optional weitere WHEREs dran.
		statement = select(Transaction)
		if start_date is not None:
			# Datum >= start_date
			statement = statement.where(Transaction.date >= start_date)
		if end_date is not None:
			# Datum <= end_date
			statement = statement.where(Transaction.date <= end_date)
		if category_id is not None:
			# Kategorie = category_id
			statement = statement.where(Transaction.category_id == category_id)
		if user_id is not None:
			from sqlalchemy.orm import aliased
			from src.domain.models import Account, CreditCard, DebitCard

			# Ownership-Problem:
			# Eine Transaktion speichert entweder `account_id` ODER `card_id` ODER
			# `creditcard_id`. Um "alle Transaktionen eines Users" zu finden, müssen wir
			# daher alle drei Wege prüfen.
			#
			# Alias für Account-Join via DebitCard:
			# Eine Debitkarte gehört einem Konto. Damit würden wir die `accounts`-Tabelle
			# ein zweites Mal joinen. Dafür brauchen wir ein SQL-Alias.
			AccountViaCard = aliased(Account)

			statement = statement.join(
				Account,
				isouter=True,
				onclause=Account.account_id == Transaction.account_id,
			).join(
				CreditCard,
				isouter=True,
				onclause=CreditCard.creditcard_id == Transaction.creditcard_id,
			).join(
				DebitCard,
				isouter=True,
				onclause=DebitCard.card_id == Transaction.card_id,
			).join(
				AccountViaCard,
				isouter=True,
				onclause=AccountViaCard.account_id == DebitCard.account_id,
			).where(
				# Ein Treffer reicht: User besitzt das Konto ODER die Kreditkarte ODER
				# (über Debitkarte) das Konto.
				(Account.user_id == user_id)
				| (CreditCard.user_id == user_id)
				| (AccountViaCard.user_id == user_id)
			)

		# Sortierung: neueste Transaktionen zuerst (bei gleichem Datum nach ID).
		statement = statement.order_by(Transaction.date.desc(), Transaction.transaction_id.desc())
		return list(self.session.exec(statement).all())

	# Gibt alle Transaktionen eines Monats optional je Kategorie zurueck.
	def list_for_month(
		self,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None = None,
	) -> list[Transaction]:
		"""Lädt Transaktionen eines Users für einen bestimmten Monat.

		Der Zeitraum wird als halboffenes Intervall modelliert:
		`[Monatsanfang, Monatsanfang des Folgemonats)`.
		Das ist robust gegen unterschiedliche Monatslaengen.

		Args:
			user_id: Der Besitzer der Transaktionen.
			month: Monat (1-12).
			year: Jahr (z. B. 2026).
			category_id: Optionaler Kategorien-Filter.

		Returns:
			Liste der Transaktionen in diesem Monat.
		"""
		from src.domain.models import Account, CreditCard, DebitCard

		# Zeitraum [Monatsanfang, Monatsanfang des Folgemonats)
		statement = select(Transaction).where(
			Transaction.date >= date(year, month, 1),
			Transaction.date < date(year + (month // 12), ((month % 12) + 1), 1),
		)
		if category_id is not None:
			statement = statement.where(Transaction.category_id == category_id)

		from sqlalchemy.orm import aliased
		# Alias ist aus dem gleichen Grund nötig wie in `filter_transactions()`.
		AccountViaCard = aliased(Account)

		statement = statement.join(
			Account,
			isouter=True,
			onclause=Account.account_id == Transaction.account_id,
		).join(
			CreditCard,
			isouter=True,
			onclause=CreditCard.creditcard_id == Transaction.creditcard_id,
		).join(
			DebitCard,
			isouter=True,
			onclause=DebitCard.card_id == Transaction.card_id,
		).join(
			AccountViaCard,
			isouter=True,
			onclause=AccountViaCard.account_id == DebitCard.account_id,
		).where(
			(Account.user_id == user_id)
			| (CreditCard.user_id == user_id)
			| (AccountViaCard.user_id == user_id)
		)

		return list(self.session.exec(statement).all())
