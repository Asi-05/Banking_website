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
			return CardRepository.list_debit_by_user(session, user_id)

	# Listet alle Kreditkarten eines Users.
	def list_credit_cards(self, user_id: int) -> list[CreditCard]:
		with Session(engine) as session:
			return CardRepository.list_credit_by_user(session, user_id)

	# Bestellt eine neue Debitkarte fuer ein Privatkonto.
	def order_debit_card(self, account_id: int) -> DebitCard:
		with Session(engine) as session:
			account = AccountRepository.get_by_id(session, account_id)
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
			return CardRepository.create_debit(session, card)

	# Sperrt eine bestehende Debitkarte.
	def block_debit_card(self, card_id: int) -> DebitCard:
		with Session(engine) as session:
			card = CardRepository.get_debit_by_id(session, card_id)
			if card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			card.block()
			return CardRepository.save_debit(session, card)

	# Ersetzt eine Debitkarte und erstellt eine neue aktive Karte.
	def replace_debit_card(self, card_id: int) -> DebitCard:
		with Session(engine) as session:
			old_card = CardRepository.get_debit_by_id(session, card_id)
			if old_card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			old_account = AccountRepository.get_by_id(session, old_card.account_id)
			if old_account is None:
				raise KeyError(f"Konto {old_card.account_id} nicht gefunden")

			old_card.replace()
			CardRepository.save_debit(session, old_card)
			self._ensure_user_has_no_active_debit_card(session, old_account.user_id)

			new_card = DebitCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				status="aktiv",
				account_id=old_card.account_id,
			)
			return CardRepository.create_debit(session, new_card)

	# Erstellt eine unabhaengige Kreditkarte mit Limit.
	def create_credit_card(self, payload: dict) -> CreditCard:
		user_id = int(payload["user_id"])
		desired_limit = float(payload["desired_limit"])
		validate_positive_amount(desired_limit)

		with Session(engine) as session:
			if UserRepository.get_by_id(session, user_id) is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			credit_card = CreditCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				limit=desired_limit,
				balance=0.0,
				status="aktiv",
				user_id=user_id,
			)
			return CardRepository.create_credit(session, credit_card)

	# Sperrt eine unabhaengige Kreditkarte.
	def block_credit_card(self, creditcard_id: int) -> CreditCard:
		with Session(engine) as session:
			card = CardRepository.get_credit_by_id(session, creditcard_id)
			if card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
			card.block()
			return CardRepository.save_credit(session, card)

	# Ersetzt eine unabhaengige Kreditkarte und uebernimmt den offenen Saldo.
	def replace_credit_card(self, creditcard_id: int) -> CreditCard:
		with Session(engine) as session:
			old_card = CardRepository.get_credit_by_id(session, creditcard_id)
			if old_card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
			old_card.replace()
			CardRepository.save_credit(session, old_card)

			new_card = CreditCard(
				card_number=self._generate_card_number(),
				expire_date=date(date.today().year + 4, date.today().month, 1),
				limit=old_card.limit,
				balance=old_card.balance,
				status="aktiv",
				user_id=old_card.user_id,
			)
			return CardRepository.create_credit(session, new_card)

	# Erzeugt eine pseudozufaellige 16-stellige Kartennummer.
	def _generate_card_number(self) -> str:
		return "".join(str(random.randint(0, 9)) for _ in range(16))

	# Prueft, dass ein User global maximal eine aktive Debitkarte besitzt.
	def _ensure_user_has_no_active_debit_card(self, session: Session, user_id: int) -> None:
		accounts = AccountRepository.list_by_user(session, user_id)
		for account in accounts:
			active_cards = CardRepository.list_active_debit_by_account(session, account.account_id)
			if active_cards:
				raise ValueError(
					"Debitkarten-Limit erreicht: Ein User darf maximal eine aktive Debitkarte besitzen"
				)


card_service = CardService()
