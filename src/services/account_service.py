from __future__ import annotations

from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import Account


# Implementiert die Geschaeftslogik fuer Konten.
class AccountService:
	# Eroeffnet ein Konto fuer einen bestehenden User.
	def open_account(self, payload: dict) -> Account:
		user_id = int(payload["user_id"])
		account_type = str(payload["account_type"]).strip().lower()
		if account_type not in {"privat", "spar"}:
			raise ValueError("Ungueltiger Kontotyp: erlaubt sind privat und spar")

		with Session(engine) as session:
			user = UserRepository.get_by_id(session, user_id)
			if user is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			iban = str(payload.get("iban") or self._generate_iban(user_id))
			existing = AccountRepository.get_by_iban(session, iban)
			if existing is not None:
				raise ValueError("IBAN ist bereits vergeben")

			account = Account(
				account_type=account_type,
				balance=float(payload.get("balance", 0.0)),
				status="aktiv",
				iban=iban,
				user_id=user_id,
			)
			return AccountRepository.create(session, account)

	# Schliesst ein Konto nur bei Saldo 0.0.
	def close_account(self, account_id: int) -> Account:
		with Session(engine) as session:
			account = AccountRepository.get_by_id(session, account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.balance != 0.0:
				raise ValueError("Konto kann nicht geschlossen werden: Balance ist nicht 0")

			account.close()
			return AccountRepository.save(session, account)

	# Gibt alle Konten eines Users zurueck.
	def list_accounts(self, user_id: int) -> list[Account]:
		with Session(engine) as session:
			return AccountRepository.list_by_user(session, user_id)

	# Erzeugt eine eindeutige Demo-IBAN fuer neue Konten.
	def _generate_iban(self, user_id: int) -> str:
		today = date.today()
		return f"DE{today.year % 100:02d}{today.month:02d}{user_id:016d}"


account_service = AccountService()
