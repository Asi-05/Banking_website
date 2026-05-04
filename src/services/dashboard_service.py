from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.domain.models import ChartData, DashboardSummary
from src.utils.validators import validate_date_range


# Implementiert die Geschaeftslogik fuer Dashboard-Aggregationen.
class DashboardService:
	# Berechnet Bilanz, Summen und Chartdaten fuer einen Zeitraum.
	def dashboard(self, user_id: int, start_date: date, end_date: date) -> DashboardSummary:
		validate_date_range(start_date, end_date)

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			transaction_repository = TransactionRepository(session)

			accounts = account_repository.list_by_user(user_id)
			total_balance = sum(account.balance for account in accounts)

			transactions = transaction_repository.filter_transactions(
				start_date=start_date,
				end_date=end_date,
				user_id=user_id,
			)
			
			# Filter out internal transfers (Kontoumbuchungen) from income/expense calculations
			# but keep them for balance calculation
			# Some test fixtures return SimpleNamespace without 'note'; be defensive.
			non_transfer_transactions = [
				t for t in transactions
				if not (getattr(t, "note", None) and "Kontoumbuchung" in getattr(t, "note", ""))
			]
			
			total_income = sum(t.amount for t in non_transfer_transactions if t.type == "income")
			total_expenses = sum(abs(t.amount) for t in non_transfer_transactions if t.type == "expense")

			grouped: dict[str, dict[str, float]] = defaultdict(
				lambda: {"income": 0.0, "expenses": 0.0}
			)
			for transaction in non_transfer_transactions:
				label = transaction.date.strftime("%Y-%m")
				if transaction.type == "income":
					grouped[label]["income"] += transaction.amount
				else:
					grouped[label]["expenses"] += abs(transaction.amount)

			chart_data = [
				ChartData(
					label=label,
					income=values["income"],
					expenses=values["expenses"],
				)
				for label, values in sorted(grouped.items())
			]

			return DashboardSummary(
				total_balance=total_balance,
				total_income=total_income,
				total_expenses=total_expenses,
				chart_data=chart_data,
			)


dashboard_service = DashboardService()
