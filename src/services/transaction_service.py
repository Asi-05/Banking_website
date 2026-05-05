"""Transaktionslogik (Service-Schicht).

Dieses Modul implementiert die Geschäftslogik für Transaktionen: erstellen,
bearbeiten, löschen und filtern. Es gehört zur Service-Schicht, weil hier
Validierungsregeln und Saldo-Updates umgesetzt werden.
Der Service wird vom `transaction_controller` aufgerufen und nutzt Repositories
(`TransactionRepository`, `AccountRepository`, `CardRepository`) für DB-Zugriffe.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.domain.models import Category, Transaction
from src.utils.validators import (
	validate_date_range,
	validate_positive_amount,
	validate_transaction_type,
)


# Implementiert die Geschaeftslogik fuer Transaktionen.
class TransactionService:
	"""Service für Transaktionen inklusive Saldo-Updates."""
	# Erstellt eine neue Transaktion und aktualisiert den betroffenen Saldo.
	def create_transaction(self, payload: dict) -> Transaction:
		"""Erstellt eine Transaktion und wendet den Effekt auf die Geldquelle an.

		Args:
			payload: Dictionary aus UI/Controller. Erwartet u. a.
				`amount`, `type` (income/expense), `category_id` und genau eine Quelle:
				`account_id` ODER `card_id` ODER `creditcard_id`.
				Optional: `date` (kann aus der UI als ISO-String kommen), `note`.

		Returns:
			Die gespeicherte Transaktion.

		Raises:
			ValueError: Bei ungültigen Eingaben (Betrag, Typ, Quelle, Saldo/Limit).
			KeyError: Wenn referenzierte Objekte (Konto/Karte/Kategorie) fehlen.
		"""
		amount = float(payload["amount"])
		transaction_type = str(payload["type"])
		transaction_date = payload.get("date") or date.today()
		# NiceGUI-Datepicker liefert oft ISO-Strings ("YYYY-MM-DD").
		# Für die Datenbank wollen wir echte `date`-Objekte.
		if isinstance(transaction_date, str):
			transaction_date = date.fromisoformat(transaction_date)
		category_id = int(payload["category_id"])
		account_id = payload.get("account_id")
		card_id = payload.get("card_id")
		creditcard_id = payload.get("creditcard_id")
		note = payload.get("note")

		account_id = int(account_id) if account_id is not None else None
		card_id = int(card_id) if card_id is not None else None
		creditcard_id = int(creditcard_id) if creditcard_id is not None else None

		validate_positive_amount(amount)
		validate_transaction_type(transaction_type)
		# Zentrale Regel: genau eine Quelle (sonst wäre unklar, wo wir abbuchen sollen).
		self._validate_transaction_source_rule(account_id, card_id, creditcard_id)

		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
			# Kategorie und Quelle müssen existieren/aktiv sein, sonst brechen wir ab.
			self._ensure_category_exists(session, category_id)
			self._ensure_source_valid(session, account_id, card_id, creditcard_id)

			transaction = Transaction(
				amount=amount,
				date=transaction_date,
				type=transaction_type,
				note=note,
				category_id=category_id,
				account_id=account_id,
				card_id=card_id,
				creditcard_id=creditcard_id,
			)
			created = transaction_repository.create(transaction)
			# Nach dem Speichern wenden wir den Effekt auf den Saldo an.
			self._apply_source_effect(session, created, multiplier=1)
			return created

	# Bearbeitet eine bestehende Transaktion und aktualisiert alle betroffenen Salden.
	def edit_transaction(self, transaction_id: int, payload: dict) -> Transaction:
		"""Ändert eine Transaktion und korrigiert den Saldo korrekt.

		Wichtig: Beim Editieren müssen wir zuerst den "alten" Effekt rückgängig machen
		(multiplier=-1), dann die neuen Werte setzen und den neuen Effekt anwenden.
		So vermeiden wir, dass der Saldo doppelt oder falsch gerechnet wird.

		Args:
			transaction_id: ID der zu ändernden Transaktion.
			payload: Neue Werte (teilweise möglich).

		Returns:
			Aktualisierte Transaktion.

		Raises:
			KeyError: Wenn die Transaktion nicht existiert.
			ValueError: Bei ungültigen Eingaben oder wenn Saldo/Limit verletzt wird.
		"""
		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
			transaction = transaction_repository.get_by_id(transaction_id)
			if transaction is None:
				raise KeyError(f"Transaktion {transaction_id} nicht gefunden")

			# 1) Alten Effekt rückgängig machen.
			self._apply_source_effect(session, transaction, multiplier=-1)

			new_amount = float(payload.get("amount", transaction.amount))
			new_type = str(payload.get("type", transaction.type))
			new_date = payload.get("date", transaction.date)
			new_category_id = int(payload.get("category_id", transaction.category_id))
			new_account_id = payload.get("account_id", transaction.account_id)
			new_card_id = payload.get("card_id", transaction.card_id)
			new_creditcard_id = payload.get("creditcard_id", transaction.creditcard_id)
			new_note = payload.get("note", transaction.note)

			new_account_id = int(new_account_id) if new_account_id is not None else None
			new_card_id = int(new_card_id) if new_card_id is not None else None
			new_creditcard_id = (
				int(new_creditcard_id) if new_creditcard_id is not None else None
			)

			validate_positive_amount(new_amount)
			validate_transaction_type(new_type)
			# Auch nach Änderungen muss die Exactly-one-Regel gelten.
			self._validate_transaction_source_rule(
				new_account_id,
				new_card_id,
				new_creditcard_id,
			)
			self._ensure_category_exists(session, new_category_id)
			self._ensure_source_valid(
				session,
				new_account_id,
				new_card_id,
				new_creditcard_id,
			)

			transaction.amount = new_amount
			transaction.type = new_type
			transaction.date = new_date
			transaction.category_id = new_category_id
			transaction.account_id = new_account_id
			transaction.card_id = new_card_id
			transaction.creditcard_id = new_creditcard_id
			transaction.note = new_note

			updated = transaction_repository.save(transaction)
			# 2) Neuen Effekt anwenden.
			self._apply_source_effect(session, updated, multiplier=1)
			return updated

	# Loescht eine bestehende Transaktion nach expliziter Bestaetigung.
	def delete_transaction(self, transaction_id: int, confirm: bool) -> bool:
		"""Löscht eine Transaktion und macht ihren Saldo-Effekt rückgängig.

		Args:
			transaction_id: ID der Transaktion.
			confirm: Muss True sein, sonst wird abgebrochen (Sicherheitsabfrage).

		Returns:
			True bei Erfolg.

		Raises:
			ValueError: Wenn `confirm` False ist.
			KeyError: Wenn die Transaktion nicht existiert.
		"""
		if not confirm:
			raise ValueError("Loeschen abgebrochen: Bestaetigung erforderlich")

		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
			transaction = transaction_repository.get_by_id(transaction_id)
			if transaction is None:
				raise KeyError(f"Transaktion {transaction_id} nicht gefunden")

			# Effekt rückgängig machen, dann DB-Zeile löschen.
			self._apply_source_effect(session, transaction, multiplier=-1)
			transaction_repository.delete(transaction)
			return True

	# Filtert Transaktionen nach Zeitraum und/oder Kategorie.
	def filter_transactions(
		self,
		start_date: date | None = None,
		end_date: date | None = None,
		category_id: int | None = None,
		user_id: int | None = None,
	) -> list[Transaction]:
		"""Filtert Transaktionen (z. B. für Listen/Tabellen in der UI).

		Args:
			start_date: Optionales Startdatum.
			end_date: Optionales Enddatum.
			category_id: Optionaler Kategorien-Filter.
			user_id: Optionaler User-Filter (Ownership-Filter über Quellen).

		Returns:
			Liste der passenden Transaktionen.

		Raises:
			ValueError: Wenn ein ungültiger Datumsbereich übergeben wird.
		"""
		if start_date is not None and end_date is not None:
			validate_date_range(start_date, end_date)

		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
			return transaction_repository.filter_transactions(
				start_date=start_date,
				end_date=end_date,
				category_id=category_id,
				user_id=user_id,
			)

	# Prueft, dass die Kategorie existiert.
	def _ensure_category_exists(self, session: Session, category_id: int) -> None:
		"""Stellt sicher, dass die Kategorie-ID in der DB existiert.

		Args:
			session: Offene DB-Session.
			category_id: Kategorie-ID.

		Raises:
			KeyError: Wenn die Kategorie nicht existiert.
		"""
		if session.get(Category, category_id) is None:
			raise KeyError(f"Kategorie {category_id} nicht gefunden")

	# Erzwingt die Exactly-one-Regel fuer Transaktionsquellen in der Service-Schicht.
	def _validate_transaction_source_rule(
		self,
		account_id: int | None,
		card_id: int | None,
		creditcard_id: int | None,
	) -> None:
		"""Validiert die Belastungsquelle (genau eine Quelle).

		Warum diese Regel?
		Eine Transaktion darf nicht gleichzeitig mehrere Quellen belasten,
		sonst würden wir denselben Betrag mehrfach abziehen oder wüssten nicht,
		welche Quelle "die richtige" ist.

		Args:
			account_id: Konto-ID oder None.
			card_id: Debitkarten-ID oder None.
			creditcard_id: Kreditkarten-ID oder None.

		Raises:
			ValueError: Wenn die Quelle-Regel verletzt ist.
		"""
		# Sonderregel: Wenn eine Kreditkarte gesetzt ist, darf *nichts anderes* gesetzt sein.
		if creditcard_id is not None and (account_id is not None or card_id is not None):
			raise ValueError(
				"Ungueltige Transaktionsquelle: Bei creditcard_id duerfen account_id und card_id nicht gesetzt sein"
			)

		if creditcard_id is None:
			has_account = account_id is not None
			has_card = card_id is not None
			# Genau-eine-Regel für Konto/Debitkarte: True/False darf nicht gleich sein.
			if has_account == has_card:
				raise ValueError(
					"Ungueltige Transaktionsquelle: Genau eine Quelle muss gesetzt sein (account_id oder card_id)"
				)

	# Prueft, dass genau die gesetzte Quelle fachlich gueltig ist.
	def _ensure_source_valid(
		self,
		session: Session,
		account_id: int | None,
		card_id: int | None,
		creditcard_id: int | None,
	) -> None:
		"""Prüft, ob die gesetzte Quelle existiert und aktiv ist.

		Args:
			session: Offene DB-Session.
			account_id: Konto-ID oder None.
			card_id: Debitkarten-ID oder None.
			creditcard_id: Kreditkarten-ID oder None.

		Raises:
			KeyError: Wenn Konto/Karte nicht gefunden wird.
			ValueError: Wenn Konto/Karte nicht aktiv ist.
		"""
		account_repository = AccountRepository(session)
		card_repository = CardRepository(session)

		if account_id is not None:
			# Konto muss existieren und aktiv sein.
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.status != "aktiv":
				raise ValueError("Transaktion nicht erlaubt: Konto ist nicht aktiv")

		if card_id is not None:
			# Debitkarte muss existieren und aktiv sein.
			card = card_repository.get_debit_by_id(card_id)
			if card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			if card.status != "aktiv":
				raise ValueError("Transaktion nicht erlaubt: Debitkarte ist nicht aktiv")

		if creditcard_id is not None:
			# Kreditkarte muss existieren und aktiv sein.
			credit_card = card_repository.get_credit_by_id(creditcard_id)
			if credit_card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
			if credit_card.status != "aktiv":
				raise ValueError("Transaktion nicht erlaubt: Kreditkarte ist nicht aktiv")

	# Wendet die Saldoaenderung einer Transaktion auf die Belastungsquelle an.
	def _apply_source_effect(
		self,
		session: Session,
		transaction: Transaction,
		multiplier: int,
	) -> None:
		"""Wendet den Geld-Effekt der Transaktion auf Konto/Debit/Kreditkarte an.

		`multiplier` ist der Trick, um Edit/Delete korrekt zu behandeln:
		- multiplier = 1  -> Effekt anwenden
		- multiplier = -1 -> Effekt rückgängig machen

		Args:
			session: Offene DB-Session.
			transaction: Die Transaktion, deren Effekt angewendet wird.
			multiplier: 1 oder -1.

		Raises:
			KeyError: Wenn referenzierte Konten/Karten fehlen.
			ValueError: Bei unzureichendem Kontosaldo oder überschrittenem Kreditlimit.
		"""
		account_repository = AccountRepository(session)
		card_repository = CardRepository(session)

		# Vorzeichen-Regel:
		# - income erhöht den Saldo (positiv)
		# - expense senkt den Saldo (negativ)
		signed_amount = transaction.amount if transaction.type == "income" else -transaction.amount
		delta = signed_amount * multiplier

		if transaction.account_id is not None:
			# Direkte Belastung eines Kontos.
			account = account_repository.get_by_id(transaction.account_id)
			if account is None:
				raise KeyError(f"Konto {transaction.account_id} nicht gefunden")
			# Bei Ausgaben prüfen wir, ob genug Geld da ist (nur beim "anwenden").
			if transaction.type == "expense" and multiplier == 1 and account.balance < transaction.amount:
				raise ValueError("Unzureichender Kontosaldo")
			account.balance += delta
			account_repository.save(account)
			return

		if transaction.card_id is not None:
			# Debitkarte belastet immer das zugehörige Konto.
			debit_card = card_repository.get_debit_by_id(transaction.card_id)
			if debit_card is None:
				raise KeyError(f"Debitkarte {transaction.card_id} nicht gefunden")
			account = account_repository.get_by_id(debit_card.account_id)
			if account is None:
				raise KeyError(f"Konto {debit_card.account_id} nicht gefunden")
			if transaction.type == "expense" and multiplier == 1 and account.balance < transaction.amount:
				raise ValueError("Unzureichender Kontosaldo")
			account.balance += delta
			account_repository.save(account)
			return

		if transaction.creditcard_id is not None:
			# Kreditkarte: wir ändern NICHT den Kontostand, sondern den genutzten Kredit.
			credit_card = card_repository.get_credit_by_id(transaction.creditcard_id)
			if credit_card is None:
				raise KeyError(f"Kreditkarte {transaction.creditcard_id} nicht gefunden")

			if transaction.type == "expense":
				# Ausgaben erhöhen den genutzten Kredit (balance) bis zum Limit.
				new_balance = credit_card.balance + (transaction.amount * multiplier)
				if multiplier == 1 and new_balance > credit_card.limit:
					raise ValueError("Kreditkartenlimit ueberschritten")
				credit_card.balance = max(0.0, new_balance)
			else:
				# Einnahmen reduzieren den genutzten Kredit (z. B. Rückerstattung).
				credit_card.balance = max(
					0.0,
					credit_card.balance - (transaction.amount * multiplier),
				)

			card_repository.save_credit(credit_card)


transaction_service = TransactionService()
