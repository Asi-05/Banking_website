from datetime import date
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from src.services import creditcard_billing_service as billing_module


def make_card(**kwargs):
    defaults = dict(
        creditcard_id=1,
        card_number="5100000000000000",
        expire_date=date(2030, 1, 1),
        limit=5000.0,
        balance=0.0,
        status="aktiv",
        billing_account_id=None,
        last_billed=None,
        user_id=1,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.parametrize("months_back,expected", [(1, True), (0, True)])
def test__is_billing_due_various(months_back, expected):
    svc = billing_module.creditcard_billing_service
    # last_billed None -> True
    card = make_card(last_billed=None)
    assert svc._is_billing_due(card, date(2026, 5, 1)) is True

    # different month -> True
    card = make_card(last_billed=date(2026, 1, 1))
    assert svc._is_billing_due(card, date(2026, 2, 1)) is True

    # same month -> False
    card = make_card(last_billed=date(2026, 5, 15))
    assert svc._is_billing_due(card, date(2026, 5, 31)) is False

    # year boundary
    card = make_card(last_billed=date(2025, 12, 31))
    assert svc._is_billing_due(card, date(2026, 1, 1)) is True


def test_process_monthly_billing_normal_case():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card = make_card(creditcard_id=11, balance=500.0, billing_account_id=99, last_billed=date(2026, 4, 30))

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:

        mock_repo = MockCardRepo.return_value
        mock_repo.list_credit_by_user.return_value = [card]

        # get_credit_by_id should return a mutable object that will be updated
        reloaded = make_card(creditcard_id=11, balance=500.0, billing_account_id=99, last_billed=date(2026, 4, 30))
        mock_repo.get_credit_by_id.return_value = reloaded
        mock_repo.save_credit.return_value = reloaded

        # CategoryRepository returns one category
        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        mock_tx_service.create_transaction.return_value = SimpleNamespace(transaction_id=123)

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        assert processed == 1
        # transaction created with proper fields
        mock_tx_service.create_transaction.assert_called()
        args = mock_tx_service.create_transaction.call_args[0][0]
        assert args["amount"] == 500.0
        assert args["account_id"] == 99
        assert args["note"] == "Zahlung Kreditkarte"

        # save_credit should have been called with updated last_billed and balance 0.0
        mock_repo.save_credit.assert_called()
        saved_obj = mock_repo.save_credit.call_args[0][0]
        assert saved_obj.balance == 0.0
        assert saved_obj.last_billed == ref


def test_process_monthly_billing_same_month_skipped():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card = make_card(creditcard_id=12, balance=200.0, billing_account_id=10, last_billed=ref)

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:
        MockCardRepo.return_value.list_credit_by_user.return_value = [card]
        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        assert processed == 0
        mock_tx_service.create_transaction.assert_not_called()


def test_process_monthly_billing_no_billing_account_skipped():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card = make_card(creditcard_id=13, balance=300.0, billing_account_id=None, last_billed=date(2026, 4, 30))

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:
        MockCardRepo.return_value.list_credit_by_user.return_value = [card]
        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        assert processed == 0
        mock_tx_service.create_transaction.assert_not_called()


def test_process_monthly_billing_zero_balance_skipped():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card = make_card(creditcard_id=14, balance=0.0, billing_account_id=10, last_billed=date(2026, 4, 30))

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:
        MockCardRepo.return_value.list_credit_by_user.return_value = [card]
        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        assert processed == 0
        mock_tx_service.create_transaction.assert_not_called()


def test_process_monthly_billing_blocked_card_skipped():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card = make_card(creditcard_id=15, balance=100.0, billing_account_id=10, last_billed=date(2026, 4, 30), status="gesperrt")

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:
        MockCardRepo.return_value.list_credit_by_user.return_value = [card]
        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        assert processed == 0
        mock_tx_service.create_transaction.assert_not_called()


def test_process_monthly_billing_transaction_raises_value_error_is_handled():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card = make_card(creditcard_id=16, balance=250.0, billing_account_id=10, last_billed=date(2026, 4, 30))

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:
        MockCardRepo.return_value.list_credit_by_user.return_value = [card]
        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        # Simulate create_transaction raising due to insufficient funds
        mock_tx_service.create_transaction.side_effect = ValueError("Unzureichender Kontosaldo")

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        # Should be skipped and not raise
        assert processed == 0
        mock_tx_service.create_transaction.assert_called()


def test_process_monthly_billing_multiple_cards_one_due_one_not():
    svc = billing_module.creditcard_billing_service
    ref = date(2026, 5, 31)
    card_due = make_card(creditcard_id=21, balance=200.0, billing_account_id=10, last_billed=date(2026, 4, 30))
    card_not_due = make_card(creditcard_id=22, balance=100.0, billing_account_id=11, last_billed=ref)

    with patch("src.services.creditcard_billing_service.CardRepository") as MockCardRepo, patch(
        "src.services.creditcard_billing_service.CategoryRepository"
    ) as MockCatRepo, patch("src.services.creditcard_billing_service.transaction_service") as mock_tx_service:
        mock_repo = MockCardRepo.return_value
        mock_repo.list_credit_by_user.return_value = [card_due, card_not_due]

        reloaded = make_card(creditcard_id=21, balance=200.0, billing_account_id=10, last_billed=date(2026, 4, 30))
        mock_repo.get_credit_by_id.return_value = reloaded
        mock_repo.save_credit.return_value = reloaded

        MockCatRepo.return_value.list_all.return_value = [SimpleNamespace(category_id=1, name="Sonstiges")]

        processed = svc.process_monthly_billing(user_id=1, reference_date=ref)

        assert processed == 1
        mock_tx_service.create_transaction.assert_called()
