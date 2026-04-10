from __future__ import annotations

from datetime import date

from src.services.payment_service import payment_service


# Orchestriert Zahlungs-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class PaymentController:
	# Fuehrt eine Inlandszahlung aus.
	def create_payment(self, payload: dict) -> str | None:
		try:
			payment_service.create_payment(payload)
			return None
		except Exception as error:
			return str(error)

	# Fuehrt eine Kontoumbuchung aus.
	def create_transfer(self, payload: dict) -> str | None:
		try:
			payment_service.create_transfer(payload)
			return None
		except Exception as error:
			return str(error)

	# Erzeugt einen Kontoauszug oder liefert Fehlermeldung.
	def generate_statement(
		self,
		account_id: int,
		start_date: date,
		end_date: date,
	) -> str:
		try:
			return payment_service.generate_statement(account_id, start_date, end_date)
		except Exception as error:
			return str(error)


payment_controller = PaymentController()
