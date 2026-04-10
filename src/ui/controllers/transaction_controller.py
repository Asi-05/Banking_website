from __future__ import annotations

from datetime import date

from src.services.transaction_service import transaction_service


# Orchestriert Transaktions-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class TransactionController:
	# Erstellt eine neue Transaktion.
	def create_transaction(self, payload: dict) -> str | None:
		try:
			transaction_service.create_transaction(payload)
			return None
		except Exception as error:
			return str(error)

	# Bearbeitet eine bestehende Transaktion.
	def edit_transaction(self, transaction_id: int, payload: dict) -> str | None:
		try:
			transaction_service.edit_transaction(transaction_id, payload)
			return None
		except Exception as error:
			return str(error)

	# Loescht eine bestehende Transaktion.
	def delete_transaction(self, transaction_id: int, confirm: bool) -> str | None:
		try:
			transaction_service.delete_transaction(transaction_id, confirm)
			return None
		except Exception as error:
			return str(error)

	# Filtert Transaktionen und gibt Liste oder Fehlermeldung zurueck.
	def filter_transactions(
		self,
		start_date: date | None = None,
		end_date: date | None = None,
		category_id: int | None = None,
		user_id: int | None = None,
	) -> list | str:
		try:
			return transaction_service.filter_transactions(
				start_date=start_date,
				end_date=end_date,
				category_id=category_id,
				user_id=user_id,
			)
		except Exception as error:
			return str(error)


transaction_controller = TransactionController()
