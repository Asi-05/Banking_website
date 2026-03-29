from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChartData:
    label: str
    income: float
    expenses: float
