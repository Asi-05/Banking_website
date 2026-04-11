from types import SimpleNamespace
from unittest.mock import patch

from src.services.budget_service import budget_service


def test_budget_exceeded_true():
    fake_budget = SimpleNamespace(budget_id=1, limit_amount=500.0)
    fake_transactions = [SimpleNamespace(amount=501.0, type="expense")]

    with patch("src.services.budget_service.Session") as mock_session_cls, patch(
        "src.services.budget_service.BudgetRepository.get_by_scope",
        return_value=fake_budget,
    ), patch(
        "src.services.budget_service.TransactionRepository.list_for_month",
        return_value=fake_transactions,
    ):
        mock_session = mock_session_cls.return_value.__enter__.return_value
        result = budget_service.check_budget_status(user_id=1, month=4, year=2026)

    assert mock_session is not None
    assert result["is_exceeded"] is True


def test_budget_exceeded_false():
    scenarios = [
        [SimpleNamespace(amount=499.0, type="expense")],
        [SimpleNamespace(amount=500.0, type="expense")],
       
    ]

    for fake_transactions in scenarios:
        fake_budget = SimpleNamespace(budget_id=1, limit_amount=500.0)
        with patch("src.services.budget_service.Session"), patch(
            "src.services.budget_service.BudgetRepository.get_by_scope",
            return_value=fake_budget,
        ), patch(
            "src.services.budget_service.TransactionRepository.list_for_month",
            return_value=fake_transactions,
        ):
            result = budget_service.check_budget_status(user_id=1, month=4, year=2026)

        assert result["is_exceeded"] is False
