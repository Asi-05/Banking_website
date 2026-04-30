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
	# Erstellt eine neue Transaktion und aktualisiert den betroffenen Saldo.
	def create_transaction(self, payload: dict) -> Transaction:
		amount = float(payload["amount"])
		transaction_type = str(payload["type"])
		transaction_date = payload.get("date") or date.today()
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
		self._validate_transaction_source_rule(account_id, card_id, creditcard_id)

		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
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
			self._apply_source_effect(session, created, multiplier=1)
			return created

	# Bearbeitet eine bestehende Transaktion und aktualisiert alle betroffenen Salden.
	def edit_transaction(self, transaction_id: int, payload: dict) -> Transaction:
		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
			transaction = transaction_repository.get_by_id(transaction_id)
			if transaction is None:
				raise KeyError(f"Transaktion {transaction_id} nicht gefunden")

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
			self._apply_source_effect(session, updated, multiplier=1)
			return updated

	# Loescht eine bestehende Transaktion nach expliziter Bestaetigung.
	def delete_transaction(self, transaction_id: int, confirm: bool) -> bool:
		if not confirm:
			raise ValueError("Loeschen abgebrochen: Bestaetigung erforderlich")

		with Session(engine, expire_on_commit=False) as session:
			transaction_repository = TransactionRepository(session)
			transaction = transaction_repository.get_by_id(transaction_id)
			if transaction is None:
				raise KeyError(f"Transaktion {transaction_id} nicht gefunden")

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
		if session.get(Category, category_id) is None:
			raise KeyError(f"Kategorie {category_id} nicht gefunden")

	# Erzwingt die Exactly-one-Regel fuer Transaktionsquellen in der Service-Schicht.
	def _validate_transaction_source_rule(
		self,
		account_id: int | None,
		card_id: int | None,
		creditcard_id: int | None,
	) -> None:
		if creditcard_id is not None and (account_id is not None or card_id is not None):
			raise ValueError(
				"Ungueltige Transaktionsquelle: Bei creditcard_id duerfen account_id und card_id nicht gesetzt sein"
			)

		if creditcard_id is None:
			has_account = account_id is not None
			has_card = card_id is not None
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
		account_repository = AccountRepository(session)
		card_repository = CardRepository(session)

		if account_id is not None:
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.status != "aktiv":
				raise ValueError("Transaktion nicht erlaubt: Konto ist nicht aktiv")

		if card_id is not None:
			card = card_repository.get_debit_by_id(card_id)
			if card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			if card.status != "aktiv":
				raise ValueError("Transaktion nicht erlaubt: Debitkarte ist nicht aktiv")

		if creditcard_id is not None:
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
		account_repository = AccountRepository(session)
		card_repository = CardRepository(session)

		signed_amount = transaction.amount if transaction.type == "income" else -transaction.amount
		delta = signed_amount * multiplier

		if transaction.account_id is not None:
			account = account_repository.get_by_id(transaction.account_id)
			if account is None:
				raise KeyError(f"Konto {transaction.account_id} nicht gefunden")
			if transaction.type == "expense" and multiplier == 1 and account.balance < transaction.amount:
				raise ValueError("Unzureichender Kontosaldo")
			account.balance += delta
			account_repository.save(account)
			return

		if transaction.card_id is not None:
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
			credit_card = card_repository.get_credit_by_id(transaction.creditcard_id)
			if credit_card is None:
				raise KeyError(f"Kreditkarte {transaction.creditcard_id} nicht gefunden")

			if transaction.type == "expense":
				new_balance = credit_card.balance + (transaction.amount * multiplier)
				if multiplier == 1 and new_balance > credit_card.limit:
					raise ValueError("Kreditkartenlimit ueberschritten")
				credit_card.balance = max(0.0, new_balance)
			else:
				credit_card.balance = max(
					0.0,
					credit_card.balance - (transaction.amount * multiplier),
				)

			card_repository.save_credit(credit_card)


transaction_service = TransactionService()
