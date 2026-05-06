"""src.ui.controllers.card_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Der CardController bietet UI-freundliche Methoden rund um Debit- und Kreditkarten.
Er delegiert die fachlichen Regeln (z.B. "max. 1 aktive Debitkarte", "Limit") an
`CardService` und gibt statt Exceptions einfache Rueckgabewerte zurueck.
"""

from __future__ import annotations

from src.services.card_service import card_service


# Orchestriert Karten-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class CardController:
	"""UI-Controller fuer Karten-Use-Cases (Debit/Kredit)."""

	# Bestellt eine Debitkarte.
	def order_debit_card(self, account_id: int) -> str | None:
		"""Bestellt eine Debitkarte fuer ein Konto.

		Args:
			account_id: ID des Kontos, fuer das eine Debitkarte bestellt werden soll.

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.order_debit_card(account_id)
			return None
		except Exception as error:
			return str(error)

	# Sperrt eine Debitkarte.
	def block_debit_card(self, card_id: int) -> str | None:
		"""Sperrt eine Debitkarte.

		Args:
			card_id: ID der Debitkarte.

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.block_debit_card(card_id)
			return None
		except Exception as error:
			return str(error)

	# Ersetzt eine Debitkarte.
	def replace_debit_card(self, card_id: int) -> str | None:
		"""Ersetzt eine Debitkarte (alte wird inaktiv, neue wird aktiv).

		Args:
			card_id: ID der zu ersetzenden Debitkarte.

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.replace_debit_card(card_id)
			return None
		except Exception as error:
			return str(error)

	# Bestellt eine Kreditkarte.
	def create_credit_card(self, payload: dict) -> str | None:
		"""Beantragt/erstellt eine Kreditkarte anhand eines Payloads aus der UI.

		Args:
			payload: Eingabedaten aus der UI (z.B. user_id, desired_limit).

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.create_credit_card(payload)
			return None
		except Exception as error:
			return str(error)

	# Sperrt eine Kreditkarte.
	def block_credit_card(self, creditcard_id: int) -> str | None:
		"""Sperrt eine Kreditkarte.

		Args:
			creditcard_id: ID der Kreditkarte.

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.block_credit_card(creditcard_id)
			return None
		except Exception as error:
			return str(error)

	# Ersetzt eine Kreditkarte.
	def replace_credit_card(self, creditcard_id: int) -> str | None:
		"""Ersetzt eine Kreditkarte (Saldo/Uebernahme im Service geregelt).

		Args:
			creditcard_id: ID der zu ersetzenden Kreditkarte.

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.replace_credit_card(creditcard_id)
			return None
		except Exception as error:
			return str(error)

	# Setzt das Abrechnungskonto fuer eine Kreditkarte.
	def handle_set_billing_account(self, creditcard_id: int, account_id: int) -> str | None:
		"""Setzt das Abrechnungskonto einer Kreditkarte.

		Args:
			creditcard_id: ID der Kreditkarte.
			account_id: ID des Kontos, das als Abrechnungskonto genutzt werden soll.

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			card_service.set_billing_account(creditcard_id, account_id)
			return None
		except Exception as error:
			return str(error)

	# Listet alle Debitkarten eines Users.
	def list_debit_cards(self, user_id: int) -> list | str:
		"""Listet alle Debitkarten eines Users.

		Args:
			user_id: ID des eingeloggten Users.

		Returns:
			Liste von Debitkarten (ORM-Objekte oder Dicts, je nach Aufrufpfad) oder
			Fehlertext als String.
		"""
		try:
			return card_service.list_debit_cards(user_id)
		except Exception as error:
			return str(error)

	# Listet alle Kreditkarten eines Users.
	def list_credit_cards(self, user_id: int) -> list | str:
		"""Listet alle Kreditkarten eines Users.

		Args:
			user_id: ID des eingeloggten Users.

		Returns:
			Liste von Kreditkarten (ORM-Objekte oder Dicts, je nach Aufrufpfad) oder
			Fehlertext als String.
		"""
		try:
			return card_service.list_credit_cards(user_id)
		except Exception as error:
			return str(error)


card_controller = CardController()
