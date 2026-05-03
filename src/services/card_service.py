from __future__ import annotations

import random
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import CreditCard, DebitCard
from src.utils.validators import validate_positive_amount


# Implementiert die Geschaeftslogik fuer Debit- und Kreditkarten.
class CardService:
	# Listet alle Debitkarten eines Users.
	def list_debit_cards(self, user_id: int) -> list[DebitCard]:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			return card_repository.list_debit_by_user(user_id)

	# Listet alle Kreditkarten eines Users als Dicts (inkl. aufgeloester billing_account IBAN).
	def list_credit_cards(self, user_id: int) -> list[dict]:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			account_repository = AccountRepository(session)
			cards = card_repository.list_credit_by_user(user_id)
			result = []
			for card in cards:
				billing_account = None
				if card.billing_account_id is not None:
					acc = account_repository.get_by_id(card.billing_account_id)
					if acc is not None:
						billing_account = {"iban": acc.iban}
				result.append({
					"creditcard_id": card.creditcard_id,
					"card_number": card.card_number,
					"expire_date": card.expire_date,
					"limit": card.limit,
					"balance": card.balance,
					"status": card.status,
					"user_id": card.user_id,
					"billing_account_id": card.billing_account_id,
					"billing_account": billing_account,
					"last_billed": card.last_billed,
				})
			return result

	# Bestellt eine neue Debitkarte fuer ein Privatkonto.
	def order_debit_card(self, account_id: int) -> DebitCard:
		with Session(engine) as session:
			account_repository = AccountRepository(session)
			card_repository = CardRepository(session)

			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.account_type != "privat":
				raise ValueError("Debitkarten koennen nur fuer Privatkonten bestellt werden")
			self._ensure_user_has_no_active_debit_card(session, account.user_id)

			card = DebitCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				status="aktiv",
				account_id=account_id,
			)
			return card_repository.create_debit(card)

	# Sperrt eine bestehende Debitkarte.
	def block_debit_card(self, card_id: int) -> DebitCard:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			card = card_repository.get_debit_by_id(card_id)
			if card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			card.block()
			return card_repository.save_debit(card)

	# Ersetzt eine Debitkarte und erstellt eine neue aktive Karte.
	def replace_debit_card(self, card_id: int) -> DebitCard:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			account_repository = AccountRepository(session)

			old_card = card_repository.get_debit_by_id(card_id)
			if old_card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			old_account = account_repository.get_by_id(old_card.account_id)
			if old_account is None:
				raise KeyError(f"Konto {old_card.account_id} nicht gefunden")

			old_card.replace()
			card_repository.save_debit(old_card)
			self._ensure_user_has_no_active_debit_card(session, old_account.user_id)

			new_card = DebitCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				status="aktiv",
				account_id=old_card.account_id,
			)
			return card_repository.create_debit(new_card)

	# Erstellt eine unabhaengige Kreditkarte mit Limit.
	def create_credit_card(self, payload: dict) -> CreditCard:
		MAX_CREDIT_LIMIT = 10_000.0
		user_id = int(payload["user_id"])
		desired_limit = float(payload["desired_limit"])
		validate_positive_amount(desired_limit)
		if desired_limit > MAX_CREDIT_LIMIT:
			raise ValueError(f"Maximales Kreditlimit beträgt CHF {MAX_CREDIT_LIMIT:,.0f}")

		with Session(engine) as session:
			user_repository = UserRepository(session)
			card_repository = CardRepository(session)

			if user_repository.get_by_id(user_id) is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			credit_card = CreditCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				limit=desired_limit,
				balance=0.0,
				status="beantragt",
				user_id=user_id,
			)
			return card_repository.create_credit(credit_card)

	# Sperrt eine unabhaengige Kreditkarte.
	def block_credit_card(self, creditcard_id: int) -> CreditCard:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			card = card_repository.get_credit_by_id(creditcard_id)
			if card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
			card.block()
			return card_repository.save_credit(card)

	# Ersetzt eine unabhaengige Kreditkarte und uebernimmt den offenen Saldo.
	def replace_credit_card(self, creditcard_id: int) -> CreditCard:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			old_card = card_repository.get_credit_by_id(creditcard_id)
			if old_card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
			old_card.replace()
			card_repository.save_credit(old_card)

			new_card = CreditCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				limit=old_card.limit,
				balance=old_card.balance,
				status="aktiv",
				user_id=old_card.user_id,
			)
			return card_repository.create_credit(new_card)

	# Erzeugt eine pseudozufaellige 16-stellige Kartennummer.
	def _generate_card_number(self) -> str:
		return "".join(str(random.randint(0, 9)) for _ in range(16))

	# Setzt das Abrechnungskonto fuer eine Kreditkarte.
	def set_billing_account(self, creditcard_id: int, account_id: int) -> CreditCard:
		with Session(engine) as session:
			card_repository = CardRepository(session)
			account_repository = AccountRepository(session)

			# Lade Kreditkarte
			credit_card = card_repository.get_credit_by_id(creditcard_id)
			if credit_card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")

			# Lade Konto
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")

			# Validiere: Konto muss aktiv sein
			if account.status != "aktiv":
				raise ValueError(f"Konto {account_id} ist nicht aktiv")

			# Validiere: Kreditkarte muss dem selben User gehoeren wie das Konto
			if credit_card.user_id != account.user_id:
				raise ValueError("Kreditkarte und Konto gehoeren nicht zum selben User")

			# Setze Abrechnungskonto
			credit_card.billing_account_id = account_id
			return card_repository.save_credit(credit_card)

	# Prueft, dass ein User global maximal eine aktive Debitkarte besitzt.
	def _ensure_user_has_no_active_debit_card(self, session: Session, user_id: int) -> None:
		account_repository = AccountRepository(session)
		card_repository = CardRepository(session)
		accounts = account_repository.list_by_user(user_id)
		for account in accounts:
			active_cards = card_repository.list_active_debit_by_account(account.account_id)
			if active_cards:
				raise ValueError(
					"Debitkarten-Limit erreicht: Ein User darf maximal eine aktive Debitkarte besitzen"
				)


card_service = CardService()
