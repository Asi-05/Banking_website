from __future__ import annotations

from datetime import date

from src.services.dashboard_service import dashboard_service


class DashboardController:
    def get_dashboard(self, user_id: int, start_date: date, end_date: date):
        try:
            return dashboard_service.dashboard(user_id, start_date, end_date)
        except Exception as error:
            return str(error)


dashboard_controller = DashboardController()
