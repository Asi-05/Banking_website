from __future__ import annotations

import random

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import Account
from src.utils.validators import generate_ch_iban


# Implementiert die Geschaeftslogik fuer Konten.
class AccountService:
	# Eroeffnet ein Konto fuer einen bestehenden User.
	def open_account(self, payload: dict) -> Account:
		user_id = int(payload["user_id"])
		account_type = str(payload["account_type"]).strip().lower()
		if account_type not in {"privat", "spar"}:
			raise ValueError("Ungueltiger Kontotyp: erlaubt sind privat und spar")

		with Session(engine) as session:
			user_repository = UserRepository(session)
			account_repository = AccountRepository(session)

			user = user_repository.get_by_id(user_id)
			if user is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			iban = str(payload.get("iban") or self._generate_iban(user_id))
			existing = account_repository.get_by_iban(iban)
			if existing is not None:
				raise ValueError("IBAN ist bereits vergeben")

			account = Account(
				account_type=account_type,
				balance=float(payload.get("balance", 0.0)),
				status="aktiv",
				iban=iban,
				user_id=user_id,
			)
			return account_repository.create(account)

	# Schliesst ein Konto nur bei Saldo 0.0.
	def close_account(self, account_id: int) -> Account:
		with Session(engine) as session:
			account_repository = AccountRepository(session)
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.balance != 0.0:
				raise ValueError("Konto kann nicht geschlossen werden: Balance ist nicht 0")

			account.close()
			return account_repository.save(account)

	# Gibt alle Konten eines Users zurueck.
	def list_accounts(self, user_id: int) -> list[Account]:
		with Session(engine) as session:
			account_repository = AccountRepository(session)
			return account_repository.list_by_user(user_id)

	# Erzeugt eine Schweizer Demo-IBAN fuer neue Konten (Bankleitzahl 09000).
	def _generate_iban(self, user_id: int) -> str:
		for _ in range(100):
			account_number = f"{random.randint(0, 999_999_999_999):012d}"
			iban = generate_ch_iban("09000", account_number)
			with Session(engine) as session:
				account_repository = AccountRepository(session)
				existing = account_repository.get_by_iban(iban)
				if existing is None:
					return iban
		raise ValueError("Konnte keine eindeutige IBAN generieren")


account_service = AccountService()
