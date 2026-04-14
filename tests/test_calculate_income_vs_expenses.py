from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from src.services.dashboard_service import dashboard_service


# TC_002: Einnahmen/Ausgaben sollen aus gemischten Vorzeichenwerten getrennt summiert werden.
def test_calculate_income_vs_expenses() -> None:
    transactions = [
        SimpleNamespace(amount=500.0, type="income", date=date(2026, 3, 1)),
        SimpleNamespace(amount=300.0, type="income", date=date(2026, 3, 2)),
        SimpleNamespace(amount=-200.0, type="expense", date=date(2026, 3, 3)),
        SimpleNamespace(amount=-150.0, type="expense", date=date(2026, 3, 4)),
        SimpleNamespace(amount=-50.0, type="expense", date=date(2026, 3, 5)),
    ]

    with patch("src.services.dashboard_service.Session"), patch(
        "src.services.dashboard_service.AccountRepository.list_by_user",
        return_value=[],
    ), patch(
        "src.services.dashboard_service.TransactionRepository.filter_transactions",
        return_value=transactions,
    ):
        result = dashboard_service.dashboard(
            user_id=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )

    assert result.total_income == 800.0
    assert result.total_expenses == 400.0
