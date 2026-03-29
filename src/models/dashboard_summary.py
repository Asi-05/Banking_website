from __future__ import annotations

from dataclasses import dataclass, field

from .chart_data import ChartData


@dataclass
class DashboardSummary:
    total_balance: float
    total_income: float
    total_expenses: float
    chart_data: list[ChartData] = field(default_factory=list)
