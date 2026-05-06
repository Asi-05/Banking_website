"""Kartenlogik (Service-Schicht).

Dieses Modul implementiert die Geschäftslogik für Debitkarten und Kreditkarten:
Bestellen/Ersetzen/Sperren sowie das Setzen eines Abrechnungskontos.
Es gehört zur Service-Schicht, weil hier Regeln geprüft werden (z. B. "nur für
Privatkonten" oder "maximal eine aktive Debitkarte pro User").
Für Datenbankzugriffe werden `CardRepository` und `AccountRepository` genutzt.
"""

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
	"""Service für Debitkarten und Kreditkarten."""
	# Listet alle Debitkarten eines Users.
	def list_debit_cards(self, user_id: int) -> list[DebitCard]:
		"""Listet alle Debitkarten eines Users.

		Args:
			user_id: User-ID.

		Returns:
			Liste der Debitkarten.
		"""
		with Session(engine) as session:
			card_repository = CardRepository(session)
			return card_repository.list_debit_by_user(user_id)

	# Listet alle Kreditkarten eines Users als Dicts (inkl. aufgeloester billing_account IBAN).
	def list_credit_cards(self, user_id: int) -> list[dict]:
		"""Listet Kreditkarten und löst optional die IBAN des Abrechnungskontos auf.

		Warum `dict` statt `CreditCard`-Objekten?
		Die UI will hier zusätzliche, "aufgelöste" Daten anzeigen (billing_account IBAN).
		Das ist einfacher als in der UI selbst mehrere DB-Calls zu machen.

		Args:
			user_id: User-ID.

		Returns:
			Liste von Dictionaries mit Kreditkartenfeldern und optionalem billing_account.
		"""
		with Session(engine) as session:
			card_repository = CardRepository(session)
			account_repository = AccountRepository(session)
			cards = card_repository.list_credit_by_user(user_id)
			result = []
			for card in cards:
				billing_account = None
				if card.billing_account_id is not None:
					# Abrechnungskonto ist optional. Wenn gesetzt, holen wir die IBAN für die Anzeige.
					acc = account_repository.get_by_id(card.billing_account_id)
					if acc is not None:
						billing_account = {"iban": acc.iban}
				result.append({
					"creditcard_id": card.creditcard_id,
					"card_number": card.card_number,
					"expire_date": card.expire_date,
					"limit": card.limit,
					# `balance` bei Kreditkarten bedeutet: genutzter Kredit (nicht Kontostand!).
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
		"""Bestellt eine neue Debitkarte für ein Privatkonto.

		Regeln:
		- Debitkarten dürfen nur auf Privatkonten bestellt werden.
		- Pro User ist maximal **eine** aktive Debitkarte erlaubt.

		Args:
			account_id: ID des Kontos.

		Returns:
			Die neu erstellte Debitkarte.

		Raises:
			KeyError: Wenn das Konto nicht existiert.
			ValueError: Wenn Konto kein Privatkonto ist oder das Debitkarten-Limit erreicht ist.
		"""
		with Session(engine) as session:
			account_repository = AccountRepository(session)
			card_repository = CardRepository(session)

			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			# Geschäftsregel: Debitkarte nur für Privatkonto.
			if account.account_type != "privat":
				raise ValueError("Debitkarten koennen nur fuer Privatkonten bestellt werden")
			# Geschäftsregel: pro User max. eine aktive Debitkarte.
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
		"""Sperrt eine Debitkarte.

		Args:
			card_id: Debitkarten-ID.

		Returns:
			Aktualisierte Debitkarte.

		Raises:
			KeyError: Wenn die Karte nicht existiert.
		"""
		with Session(engine) as session:
			card_repository = CardRepository(session)
			card = card_repository.get_debit_by_id(card_id)
			if card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			card.block()
			return card_repository.save_debit(card)

	# Ersetzt eine Debitkarte und erstellt eine neue aktive Karte.
	def replace_debit_card(self, card_id: int) -> DebitCard:
		"""Ersetzt eine Debitkarte (alte wird markiert, neue wird erstellt).

		Args:
			card_id: ID der zu ersetzenden Debitkarte.

		Returns:
			Die neue Debitkarte.

		Raises:
			KeyError: Wenn Karte oder zugehöriges Konto nicht existiert.
			ValueError: Wenn dadurch das "max. eine aktive Debitkarte"-Limit verletzt wäre.
		"""
		with Session(engine) as session:
			card_repository = CardRepository(session)
			account_repository = AccountRepository(session)

			old_card = card_repository.get_debit_by_id(card_id)
			if old_card is None:
				raise KeyError(f"Debitkarte {card_id} nicht gefunden")
			old_account = account_repository.get_by_id(old_card.account_id)
			if old_account is None:
				raise KeyError(f"Konto {old_card.account_id} nicht gefunden")

			# Alte Karte markieren.
			old_card.replace()
			card_repository.save_debit(old_card)
			# Sicherheitscheck: es soll nicht zufällig doch schon eine aktive Karte geben.
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
		"""Beantragt eine neue Kreditkarte mit einem gewünschten Limit.

		Wichtig: Eine Kreditkarte hat ein `limit` (Kreditrahmen) und eine `balance`
		(genutzter Kredit). Zu Beginn ist `balance` 0.

		Args:
			payload: Erwartet `user_id` und `desired_limit`.

		Returns:
			Das neu erstellte Kreditkarten-Objekt.

		Raises:
			ValueError: Wenn der Betrag ungültig ist oder über dem Max-Limit liegt.
			KeyError: Wenn der User nicht existiert.
		"""
		MAX_CREDIT_LIMIT = 10_000.0
		user_id = int(payload["user_id"])
		desired_limit = float(payload["desired_limit"])
		validate_positive_amount(desired_limit)
		# Business-Regel: wir begrenzen Limits im Demo-System.
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
				# Status "beantragt" ist ein Demo-Workflow (noch nicht aktiv).
				status="beantragt",
				user_id=user_id,
			)
			return card_repository.create_credit(credit_card)

	# Sperrt eine unabhaengige Kreditkarte.
	def block_credit_card(self, creditcard_id: int) -> CreditCard:
		"""Sperrt eine Kreditkarte.

		Args:
			creditcard_id: Kreditkarten-ID.

		Returns:
			Aktualisierte Kreditkarte.

		Raises:
			KeyError: Wenn die Kreditkarte nicht existiert.
		"""
		with Session(engine) as session:
			card_repository = CardRepository(session)
			card = card_repository.get_credit_by_id(creditcard_id)
			if card is None:
				raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
			card.block()
			return card_repository.save_credit(card)

	# Ersetzt eine unabhaengige Kreditkarte und uebernimmt den offenen Saldo.
	def replace_credit_card(self, creditcard_id: int) -> CreditCard:
		"""Ersetzt eine Kreditkarte und übernimmt den offenen Saldo.

		Warum Saldo übernehmen?
		`balance` bedeutet "genutzter Kredit". Wenn eine Karte ersetzt wird, soll
		dieser offene Betrag nicht verschwinden, sondern auf die neue Karte übergehen.

		Args:
			creditcard_id: ID der alten Kreditkarte.

		Returns:
			Die neue Kreditkarte.

		Raises:
			KeyError: Wenn die Kreditkarte nicht existiert.
		"""
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
		"""Erzeugt eine pseudozufällige 16-stellige Kartennummer (Demo)."""
		return "".join(str(random.randint(0, 9)) for _ in range(16))

	# Setzt das Abrechnungskonto fuer eine Kreditkarte.
	def set_billing_account(self, creditcard_id: int, account_id: int) -> CreditCard:
		"""Setzt das Abrechnungskonto einer Kreditkarte.

		Das Abrechnungskonto ist das Konto, von dem die Monatsabrechnung abgebucht
		wird (siehe `creditcard_billing_service`).

		Args:
			creditcard_id: Kreditkarten-ID.
			account_id: Konto-ID, das als Abrechnungskonto dienen soll.

		Returns:
			Aktualisierte Kreditkarte.

		Raises:
			KeyError: Wenn Kreditkarte/Konto nicht existieren.
			ValueError: Wenn Konto nicht aktiv ist oder nicht zum selben User gehört.
		"""
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
		"""Prüft die Business-Regel: max. eine aktive Debitkarte pro User.

		Args:
			session: Offene DB-Session.
			user_id: User-ID.

		Raises:
			ValueError: Wenn bereits eine aktive Debitkarte existiert.
		"""
		account_repository = AccountRepository(session)
		card_repository = CardRepository(session)
		# Wir prüfen über alle Konten des Users, ob irgendwo eine aktive Debitkarte hängt.
		accounts = account_repository.list_by_user(user_id)
		for account in accounts:
			active_cards = card_repository.list_active_debit_by_account(account.account_id)
			if active_cards:
				raise ValueError(
					"Debitkarten-Limit erreicht: Ein User darf maximal eine aktive Debitkarte besitzen"
				)


card_service = CardService()
