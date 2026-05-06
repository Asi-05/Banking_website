"""Kontoverwaltung (Service-Schicht).

Dieses Modul implementiert die Geschäftslogik für Konten: Konto eröffnen,
schließen und auflisten. Es gehört zur Service-Schicht, weil hier Regeln
(z. B. "Schließen nur bei Saldo 0") und Abläufe umgesetzt werden.
Der Service arbeitet mit `AccountRepository`/`UserRepository` für DB-Zugriffe
und nutzt `generate_ch_iban()` für Demo-IBANs.
"""

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
	"""Service für Konto-Eröffnung, Konto-Schließung und Konto-Listen."""
	# Eroeffnet ein Konto fuer einen bestehenden User.
	def open_account(self, payload: dict) -> Account:
		"""Eröffnet ein neues Konto für einen bestehenden User.

		Regeln:
		- `account_type` muss "privat" oder "spar" sein
		- die IBAN muss eindeutig sein

		Args:
			payload: Dictionary mit Eingaben aus Controller/UI.
				Erwartet mindestens `user_id` und `account_type`.
				Optional: `iban`, `balance`.

		Returns:
			Das neu gespeicherte `Account`-Objekt.

		Raises:
			ValueError: Bei ungültigem Kontotyp oder wenn die IBAN schon existiert.
			KeyError: Wenn der User nicht existiert.
		"""
		# Eingaben normalisieren (Strings trimmen, Zahlen casten), damit Validierung robust ist.
		user_id = int(payload["user_id"])
		account_type = str(payload["account_type"]).strip().lower()
		# Validierungsregel: nur die zwei bekannten Typen erlauben.
		if account_type not in {"privat", "spar"}:
			raise ValueError("Ungueltiger Kontotyp: erlaubt sind privat und spar")

		with Session(engine) as session:
			user_repository = UserRepository(session)
			account_repository = AccountRepository(session)

			user = user_repository.get_by_id(user_id)
			if user is None:
				raise KeyError(f"User {user_id} nicht gefunden")

			# IBAN entweder aus Payload übernehmen oder automatisch generieren.
			iban = str(payload.get("iban") or self._generate_iban(user_id))
			# Eindeutigkeit prüfen, weil die IBAN fachlich ein eindeutiger Identifikator ist.
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
		"""Schließt ein Konto, aber nur wenn der Saldo 0 ist.

		Args:
			account_id: ID des zu schließenden Kontos.

		Returns:
			Das aktualisierte Konto.

		Raises:
			KeyError: Wenn das Konto nicht existiert.
			ValueError: Wenn der Saldo nicht 0 ist.
		"""
		with Session(engine) as session:
			account_repository = AccountRepository(session)
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			# Geschäftsregel: Nur leere Konten dürfen geschlossen werden.
			if account.balance != 0.0:
				raise ValueError("Konto kann nicht geschlossen werden: Balance ist nicht 0")

			account.close()
			return account_repository.save(account)

	# Gibt alle Konten eines Users zurueck.
	def list_accounts(self, user_id: int) -> list[Account]:
		"""Listet alle Konten eines Users.

		Args:
			user_id: User-ID.

		Returns:
			Liste der Konten.
		"""
		with Session(engine) as session:
			account_repository = AccountRepository(session)
			return account_repository.list_by_user(user_id)

	# Erzeugt eine Schweizer Demo-IBAN fuer neue Konten (Bankleitzahl 09000).
	def _generate_iban(self, user_id: int) -> str:
		"""Generiert eine eindeutige Demo-IBAN.

		Wir erzeugen zufällige Kontonummern und berechnen daraus eine CH-IBAN.
		Danach prüfen wir in der DB, ob diese IBAN schon existiert.

		Args:
			user_id: Wird hier nicht direkt verwendet, ist aber nützlich für Logs/
				spätere Erweiterungen.

		Returns:
			Eine IBAN, die aktuell nicht in der Datenbank vorkommt.

		Raises:
			ValueError: Wenn nach vielen Versuchen keine freie IBAN gefunden wird.
		"""
		# Sicherheitsnetz: wir versuchen es begrenzt oft, um Endlosschleifen zu vermeiden.
		for _ in range(100):
			# 12-stellige Kontonummer, als String mit führenden Nullen.
			account_number = f"{random.randint(0, 999_999_999_999):012d}"
			iban = generate_ch_iban("09000", account_number)
			# Hinweis: Hier wird pro Versuch eine Session geöffnet.
			# Das ist nicht maximal effizient, aber für ein Demo-Projekt einfach.
			with Session(engine) as session:
				account_repository = AccountRepository(session)
				existing = account_repository.get_by_iban(iban)
				if existing is None:
					return iban
		raise ValueError("Konnte keine eindeutige IBAN generieren")


account_service = AccountService()
