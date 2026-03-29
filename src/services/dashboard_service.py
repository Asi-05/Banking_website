from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models import ChartData, DashboardSummary


class DashboardService(ABC):
    @abstractmethod
    def build_summary(self, user_id: int, start_date: date, end_date: date) -> DashboardSummary:
        raise NotImplementedError

    @abstractmethod
    def build_chart_data(self, user_id: int, start_date: date, end_date: date) -> list[ChartData]:
        raise NotImplementedError
