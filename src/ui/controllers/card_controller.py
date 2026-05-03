from __future__ import annotations

from src.services.card_service import card_service


# Orchestriert Karten-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class CardController:
	# Bestellt eine Debitkarte.
	def order_debit_card(self, account_id: int) -> str | None:
		try:
			card_service.order_debit_card(account_id)
			return None
		except Exception as error:
			return str(error)

	# Sperrt eine Debitkarte.
	def block_debit_card(self, card_id: int) -> str | None:
		try:
			card_service.block_debit_card(card_id)
			return None
		except Exception as error:
			return str(error)

	# Ersetzt eine Debitkarte.
	def replace_debit_card(self, card_id: int) -> str | None:
		try:
			card_service.replace_debit_card(card_id)
			return None
		except Exception as error:
			return str(error)

	# Bestellt eine Kreditkarte.
	def create_credit_card(self, payload: dict) -> str | None:
		try:
			card_service.create_credit_card(payload)
			return None
		except Exception as error:
			return str(error)

	# Sperrt eine Kreditkarte.
	def block_credit_card(self, creditcard_id: int) -> str | None:
		try:
			card_service.block_credit_card(creditcard_id)
			return None
		except Exception as error:
			return str(error)

	# Ersetzt eine Kreditkarte.
	def replace_credit_card(self, creditcard_id: int) -> str | None:
		try:
			card_service.replace_credit_card(creditcard_id)
			return None
		except Exception as error:
			return str(error)

	# Setzt das Abrechnungskonto fuer eine Kreditkarte.
	def handle_set_billing_account(self, creditcard_id: int, account_id: int) -> str | None:
		try:
			card_service.set_billing_account(creditcard_id, account_id)
			return None
		except Exception as error:
			return str(error)

	# Listet alle Debitkarten eines Users.
	def list_debit_cards(self, user_id: int) -> list | str:
		try:
			return card_service.list_debit_cards(user_id)
		except Exception as error:
			return str(error)

	# Listet alle Kreditkarten eines Users.
	def list_credit_cards(self, user_id: int) -> list | str:
		try:
			return card_service.list_credit_cards(user_id)
		except Exception as error:
			return str(error)


card_controller = CardController()
