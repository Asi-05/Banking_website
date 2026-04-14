from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from src.services.dashboard_service import dashboard_service


# TC_001: Gesamtsaldo aus gemischten Betraegen muss korrekt summiert werden.
def test_calculate_total_balance() -> None:
    accounts = [
        SimpleNamespace(balance=1000.0),
        SimpleNamespace(balance=-200.0),
        SimpleNamespace(balance=-50.0),
    ]

    with patch("src.services.dashboard_service.Session"), patch(
        "src.services.dashboard_service.AccountRepository.list_by_user",
        return_value=accounts,
    ), patch(
        "src.services.dashboard_service.TransactionRepository.filter_transactions",
        return_value=[],
    ):
        result = dashboard_service.dashboard(
            user_id=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )

    assert result.total_balance == 750.0
