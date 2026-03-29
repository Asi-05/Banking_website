from __future__ import annotations

"""Dashboard-Aggregationslogik (Summen und Diagrammdaten)."""

from datetime import date

from ...models import ChartData, DashboardSummary, TransactionType
from ..interface.dashboard_service import DashboardService
from .shared import InMemoryStore, month_key


class InMemoryDashboardService(DashboardService):
    """Erzeugt Dashboard-Kennzahlen aus In-Memory-Transaktionen und Konten."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def build_summary(self, user_id: int, start_date: date, end_date: date) -> DashboardSummary:
        """Gibt uebergeordnete KPIs fuer den ausgewaehlten Zeitraum zurueck."""

        if start_date > end_date:
            raise ValueError("start_date must not be greater than end_date")

        txs = [
            tx
            for tx in self.store.transactions.values()
            if tx.user_id == user_id and start_date <= tx.date_value <= end_date
        ]

        total_income = sum(tx.amount for tx in txs if tx.transaction_type == TransactionType.INCOME)
        total_expenses = sum(tx.amount for tx in txs if tx.transaction_type == TransactionType.EXPENSE)
        total_balance = sum(
            account.balance for account in self.store.accounts.values() if account.user_id == user_id
        )

        return DashboardSummary(
            total_balance=total_balance,
            total_income=total_income,
            total_expenses=total_expenses,
            chart_data=self.build_chart_data(user_id, start_date, end_date),
        )

    def build_chart_data(self, user_id: int, start_date: date, end_date: date) -> list[ChartData]:
        """Aggregiert Einnahmen/Ausgaben pro Monat fuer die Diagrammdarstellung."""

        grouped: dict[tuple[int, int], dict[str, float]] = {}

        for tx in self.store.transactions.values():
            if tx.user_id != user_id or tx.date_value < start_date or tx.date_value > end_date:
                continue

            key = month_key(tx.date_value)
            if key not in grouped:
                grouped[key] = {"income": 0.0, "expenses": 0.0}

            if tx.transaction_type == TransactionType.INCOME:
                grouped[key]["income"] += tx.amount
            else:
                grouped[key]["expenses"] += tx.amount

        chart_data: list[ChartData] = []
        for year, month in sorted(grouped.keys()):
            label = f"{year}-{month:02d}"
            chart_data.append(
                ChartData(label=label, income=grouped[(year, month)]["income"], expenses=grouped[(year, month)]["expenses"])
            )

        return chart_data
