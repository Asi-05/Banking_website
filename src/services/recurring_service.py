from __future__ import annotations

import calendar
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.recurring_repository import RecurringRepository
from src.domain.models import Category, RecurringTransaction, Transaction
from src.services.transaction_service import transaction_service
from src.utils.validators import (
	validate_iban,
	validate_positive_amount,
	validate_recurring_interval,
)


# Implementiert die Geschaeftslogik fuer Dauerauftraege.
class RecurringService:
	# Legt einen neuen Dauerauftrag mit Startkonfiguration an.
	def create_recurring(self, payload: dict) -> RecurringTransaction:
		amount = float(payload["amount"])
		category_id = int(payload["category_id"])
		account_id = int(payload["account_id"])
		target_iban = str(payload["target_iban"])
		interval = str(payload["interval"])
		start_date = payload["start_date"]
		end_date = payload.get("end_date")

		validate_positive_amount(amount)
		validate_iban(target_iban)
		validate_recurring_interval(interval)

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.status != "aktiv":
				raise ValueError(f"Konto {account_id} ist nicht aktiv und kann nicht verwendet werden")
			if session.get(Category, category_id) is None:
				raise KeyError(f"Kategorie {category_id} nicht gefunden")

			template_transaction = Transaction(
				amount=amount,
				date=start_date,
				type="expense",
				note="Dauerauftrag",
				category_id=category_id,
				account_id=account_id,
			)
			session.add(template_transaction)
			session.commit()
			session.refresh(template_transaction)

			recurring = RecurringTransaction(
				amount=amount,
				target_iban=target_iban,
				interval=interval,
				start_date=start_date,
				end_date=end_date,
				last_executed=self._previous_due_date(start_date, interval),
				account_id=account_id,
				category_id=category_id,
				transaction_id=template_transaction.transaction_id,
			)
			session.add(recurring)
			session.commit()
			session.refresh(recurring)
			return recurring

	# Verarbeitet alle faelligen Dauerauftraege eines Users beim Login.
	def process_due_recurring_on_login(self, user_id: int, login_date: date) -> int:
		executed = 0
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			due_candidates = recurring_repository.list_due_by_user(
				user_id=user_id,
				reference_date=login_date,
			)

		for recurring in due_candidates:
			if recurring.end_date is not None and recurring.end_date < login_date:
				continue
			if not self._is_due(recurring, login_date):
				continue

			try:
				transaction_service.create_transaction(
					{
						"amount": recurring.amount,
						"type": "expense",
						"date": login_date,
						"category_id": recurring.category_id,
						"account_id": recurring.account_id,
						"note": "Dauerauftrag Ausfuehrung",
					}
				)
			except (ValueError, KeyError):
				continue
			with Session(engine) as session:
				recurring_repository = RecurringRepository(session)
				reloaded = recurring_repository.get_by_id(recurring.recurring_id)
				if reloaded is not None:
					reloaded.last_executed = login_date
					recurring_repository.save(reloaded)
			executed += 1

		return executed

	# Prueft, ob ein einzelner Dauerauftrag zum Referenzdatum faellig ist.
	def _is_due(self, recurring: RecurringTransaction, reference_date: date) -> bool:
		if reference_date < recurring.start_date:
			return False

		next_due = self._next_due_date(recurring.last_executed, recurring.interval)
		return next_due <= reference_date

	# Berechnet das naechste Faelligkeitsdatum aus Intervall und letzter Ausfuehrung.
	def _next_due_date(self, from_date: date, interval: str) -> date:
		if interval == "monthly":
			year = from_date.year + (from_date.month // 12)
			month = (from_date.month % 12) + 1
			day = min(from_date.day, calendar.monthrange(year, month)[1])
			return date(year, month, day)
		if interval == "yearly":
			year = from_date.year + 1
			day = min(from_date.day, calendar.monthrange(year, from_date.month)[1])
			return date(year, from_date.month, day)
		return from_date

	# Berechnet das direkte Vorgaengerdatum zum Intervall fuer den Initialzustand.
	def _previous_due_date(self, from_date: date, interval: str) -> date:
		if interval == "monthly":
			year = from_date.year
			month = from_date.month - 1
			if month == 0:
				month = 12
				year -= 1
			day = min(from_date.day, calendar.monthrange(year, month)[1])
			return date(year, month, day)
		if interval == "yearly":
			year = from_date.year - 1
			day = min(from_date.day, calendar.monthrange(year, from_date.month)[1])
			return date(year, from_date.month, day)
		return from_date


	# Gibt alle Dauerauftraege eines Users zurueck.
	def list_recurring(self, user_id: int) -> list[RecurringTransaction]:
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			return recurring_repository.list_by_user(user_id)

	# Aktualisiert einen Dauerauftrag.
	def update_recurring(self, recurring_id: int, payload: dict) -> RecurringTransaction:
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			recurring = recurring_repository.get_by_id(recurring_id)
			if recurring is None:
				raise KeyError(f"Dauerauftrag {recurring_id} nicht gefunden")

			# Validiere und aktualisiere Felder
			if "amount" in payload:
				amount = float(payload["amount"])
				validate_positive_amount(amount)
				recurring.amount = amount

			if "interval" in payload:
				interval = str(payload["interval"])
				validate_recurring_interval(interval)
				recurring.interval = interval

			if "target_iban" in payload:
				target_iban = str(payload["target_iban"])
				validate_iban(target_iban)
				recurring.target_iban = target_iban

			if "end_date" in payload:
				end_date_val = payload["end_date"]
				if isinstance(end_date_val, str):
					end_date_val = date.fromisoformat(end_date_val) if end_date_val else None
				recurring.end_date = end_date_val

			if "category_id" in payload and payload["category_id"] is not None:
				recurring.category_id = int(payload["category_id"])

			if "account_id" in payload and payload["account_id"] is not None:
				recurring.account_id = int(payload["account_id"])

			return recurring_repository.save(recurring)

	# Liefert einen einzelnen Dauerauftrag per ID.
	def get_by_id(self, recurring_id: int) -> RecurringTransaction | None:
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			return recurring_repository.get_by_id(recurring_id)

	# Oeffentliche Version von _next_due_date fuer die Controller-Schicht.
	def next_execution_date(self, last_executed: date, interval: str) -> date:
		return self._next_due_date(last_executed, interval)

	# Loescht einen Dauerauftrag und die verknuepfte Template-Transaktion.
	def delete_recurring(self, recurring_id: int) -> None:
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			recurring = recurring_repository.get_by_id(recurring_id)
			if recurring is None:
				raise KeyError(f"Dauerauftrag {recurring_id} nicht gefunden")

			transaction_id = recurring.transaction_id

			# Zuerst Dauerauftrag löschen, dann Template-Transaktion
			recurring_repository.delete(recurring_id)

			if transaction_id:
				from src.data_access.repositories.transaction_repository import TransactionRepository
				from src.domain.models import Transaction
				transaction_repository = TransactionRepository(session)
				transaction = session.get(Transaction, transaction_id)
				if transaction is not None:
					transaction_repository.delete(transaction)


recurring_service = RecurringService()
