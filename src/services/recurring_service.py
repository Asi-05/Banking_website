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
			account = AccountRepository.get_by_id(session, account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if session.get(Category, category_id) is None:
				raise KeyError(f"Kategorie {category_id} nicht gefunden")

			template_transaction = Transaction(
				amount=0.0,
				date=start_date,
				type="expense",
				note="Dauerauftrag Vorlage",
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
			return RecurringRepository.create(session, recurring)

	# Verarbeitet alle faelligen Dauerauftraege eines Users beim Login.
	def process_due_recurring_on_login(self, user_id: int, login_date: date) -> int:
		executed = 0
		with Session(engine) as session:
			due_candidates = RecurringRepository.list_due_by_user(
				session,
				user_id=user_id,
				reference_date=login_date,
			)

		for recurring in due_candidates:
			if recurring.end_date is not None and recurring.end_date < login_date:
				continue
			if not self._is_due(recurring, login_date):
				continue

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
			with Session(engine) as session:
				reloaded = RecurringRepository.get_by_id(session, recurring.recurring_id)
				if reloaded is not None:
					reloaded.last_executed = login_date
					RecurringRepository.save(session, reloaded)
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


recurring_service = RecurringService()
