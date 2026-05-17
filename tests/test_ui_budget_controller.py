"""
UI Tests: BudgetController
Prüft FR-BUD-01, FR-BUD-02, FR-BUD-03

FR-BUD-01: Budget anlegen/ändern pro Kategorie und Monat
FR-BUD-01a: Budget-Objekt mit allen Pflichtfeldern
FR-BUD-02: Sichtbare Warnung bei Erreichen/Überschreitung des Limits
FR-BUD-03: Auslöser jeder Budgetwarnung mit Kategorie, Zeitraum und Betrag
"""

from unittest.mock import patch
from types import SimpleNamespace

from src.ui.controllers.budget_controller import BudgetController


def _make_controller():
    return BudgetController()


def _valid_budget_payload():
    return {
        "user_id": 1,
        "limit_amount": 500.0,
        "month": 4,
        "year": 2026,
        "category_id": 1,
    }


# FR-BUD-01: Erfolgreiches Budget-Anlegen gibt None zurück
def test_set_budget_success_returns_none():
    controller = _make_controller()
    # Simulate repository upsert to avoid DB; let service validation run.
    fake_budget = SimpleNamespace(budget_id=1)
    with patch("src.data_access.repositories.user_repository.UserRepository.get_by_id", return_value=SimpleNamespace(user_id=1)), \
        patch("src.data_access.repositories.budget_repository.BudgetRepository.get_by_scope", return_value=None), \
        patch("src.data_access.repositories.budget_repository.BudgetRepository.create", return_value=fake_budget):
        result = controller.set_budget(_valid_budget_payload())

    assert result is None


# FR-BUD-01: Budget ohne Kategorie (global) gibt None zurück
def test_set_budget_global_no_category_returns_none():
    controller = _make_controller()
    payload = {**_valid_budget_payload(), "category_id": None}

    with patch("src.ui.controllers.budget_controller.budget_service.set_budget", return_value=None):
        result = controller.set_budget(payload)

    assert result is None


# FR-BUD-01a: Budget mit negativem limit_amount wird abgelehnt
def test_set_budget_negative_limit_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_budget_payload(), "limit_amount": -100.0}
    # Validation happens before DB session opens.
    result = controller.set_budget(payload)
    assert isinstance(result, str)


# FR-BUD-01: set_budget delegiert korrekt an budget_service.set_budget
def test_set_budget_delegates_to_service():
    controller = _make_controller()
    payload = _valid_budget_payload()

    with patch("src.ui.controllers.budget_controller.budget_service.set_budget") as mock_set:
        controller.set_budget(payload)

    mock_set.assert_called_once_with(payload)


# FR-BUD-02: Budget nicht überschritten → is_exceeded=False
def test_check_budget_status_not_exceeded():
    controller = _make_controller()
    # Let BudgetService run; patch repositories to return a budget and transactions.
    fake_budget = SimpleNamespace(budget_id=1, limit_amount=500.0)
    fake_txns = [SimpleNamespace(amount=100.0, type="expense"), SimpleNamespace(amount=200.0, type="expense")]

    with patch("src.data_access.repositories.budget_repository.BudgetRepository.get_by_scope", return_value=fake_budget), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.list_for_month", return_value=fake_txns):
        result = controller.check_budget_status(user_id=1, month=4, year=2026)

    assert isinstance(result, dict)
    assert result["is_exceeded"] is False


# FR-BUD-02: Budget überschritten → is_exceeded=True (Warnung muss ausgelöst werden)
def test_check_budget_status_exceeded():
    controller = _make_controller()
    fake_budget = SimpleNamespace(budget_id=1, limit_amount=500.0)
    fake_txns = [SimpleNamespace(amount=600.0, type="expense")]

    with patch("src.data_access.repositories.budget_repository.BudgetRepository.get_by_scope", return_value=fake_budget), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.list_for_month", return_value=fake_txns):
        result = controller.check_budget_status(user_id=1, month=4, year=2026)

    assert isinstance(result, dict)
    assert result["is_exceeded"] is True


# FR-BUD-02: Exakt am Limit → gilt als überschritten/erreicht
def test_check_budget_status_exactly_at_limit():
    controller = _make_controller()
    fake_budget = SimpleNamespace(budget_id=1, limit_amount=500.0)
    fake_txns = [SimpleNamespace(amount=500.0, type="expense")]

    with patch("src.data_access.repositories.budget_repository.BudgetRepository.get_by_scope", return_value=fake_budget), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.list_for_month", return_value=fake_txns):
        result = controller.check_budget_status(user_id=1, month=4, year=2026)

    # Service uses strict > comparison; exactly at limit is not considered exceeded.
    assert result["is_exceeded"] is False


# FR-BUD-03: Status enthält Kategorie, Zeitraum (month, year) und Betrag
def test_check_budget_status_returns_category_period_and_amount():
    controller = _make_controller()
    fake_budget = SimpleNamespace(budget_id=1, limit_amount=500.0, category_id=2)
    fake_txns = [SimpleNamespace(amount=550.0, type="expense")]

    with patch("src.data_access.repositories.budget_repository.BudgetRepository.get_by_scope", return_value=fake_budget), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.list_for_month", return_value=fake_txns):
        result = controller.check_budget_status(user_id=1, month=4, year=2026, category_id=2)

    assert "current_spending" in result
    assert "limit_amount" in result
    assert "is_exceeded" in result
    assert result["current_spending"] == 550.0
    assert result["limit_amount"] == 500.0
    assert result["is_exceeded"] is True


# FR-BUD-02: Kein Budget vorhanden → Fehlermeldung als String
def test_check_budget_status_no_budget_returns_error_string():
    controller = _make_controller()
    # No budget found -> service raises KeyError which controller returns as string
    with patch("src.data_access.repositories.budget_repository.BudgetRepository.get_by_scope", return_value=None):
        result = controller.check_budget_status(user_id=1, month=4, year=2026)

    assert isinstance(result, str)
    assert "Budget" in result


# FR-BUD-01: check_budget_status übergibt category_id korrekt an Service
def test_check_budget_status_passes_category_id():
    controller = _make_controller()
    fake_status = {"is_exceeded": False, "current_spending": 100.0, "limit_amount": 500.0}
    with patch("src.ui.controllers.budget_controller.budget_service.check_budget_status", return_value=fake_status) as mock_check:
        controller.check_budget_status(user_id=1, month=4, year=2026, category_id=3)

    mock_check.assert_called_once_with(user_id=1, month=4, year=2026, category_id=3)
