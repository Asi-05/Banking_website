"""src.ui.controllers.dashboard_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Das Dashboard ist eine aggregierte Sicht auf Konten und Transaktionen.
Dieser Controller ruft den `DashboardService` auf und kapselt Fehler so, dass
die View entweder eine Summary oder einen Fehlertext anzeigen kann.
"""

from __future__ import annotations

from datetime import date

from src.services.dashboard_service import dashboard_service


class DashboardController:
    """UI-Controller fuer Dashboard-Daten."""

    def get_dashboard(self, user_id: int, start_date: date, end_date: date):
        """Liefert Dashboard-Aggregationen fuer einen Zeitraum.

        Returns:
            Ein `DashboardSummary`-Objekt oder eine Fehlermeldung als String.
        """
        try:
            return dashboard_service.dashboard(user_id, start_date, end_date)
        except Exception as error:
            return str(error)


dashboard_controller = DashboardController()
