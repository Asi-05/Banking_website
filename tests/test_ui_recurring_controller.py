"""
UI Tests: RecurringController
Prüft FR-BUD-04

FR-BUD-04: Daueraufträge anlegen (amount, category_id, account_id, target_iban,
           interval monthly/yearly, start_date) und automatisch beim Login buchen.
           target_iban muss vor dem Speichern validiert werden.
"""

from datetime import date
from unittest.mock import patch
from types import SimpleNamespace

from src.ui.controllers.recurring_controller import RecurringController


def _make_controller():
    return RecurringController()


def _valid_recurring_payload():
    return {
        "user_id": 1,
        "amount": 1200.0,
        "category_id": 3,
        "account_id": 1,
        "target_iban": "CH5604835012345678009",
        "interval": "monthly",
        "start_date": date.today().isoformat(),
    }


# FR-BUD-04: Erfolgreicher Dauerauftrag gibt None zurück
def test_create_recurring_success_returns_none():
    controller = _make_controller()
    fake_recurring = SimpleNamespace(recurring_id=1)
    with patch("sqlmodel.Session.get", return_value=SimpleNamespace(category_id=3)), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=SimpleNamespace(account_id=1, status="aktiv")), \
        patch("src.data_access.repositories.recurring_repository.RecurringRepository.create", return_value=fake_recurring):
        result = controller.create_recurring(_valid_recurring_payload())

    assert result is None


# FR-BUD-04: Ungültige IBAN beim Dauerauftrag wird abgelehnt
def test_create_recurring_invalid_iban_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_recurring_payload(), "target_iban": "DE12345678"}
    # IBAN validation happens in RecurringService before DB access.
    result = controller.create_recurring(payload)

    assert isinstance(result, str)
    assert "IBAN" in result


# FR-BUD-04: Ungültiges Intervall (nicht monthly/yearly) wird abgelehnt
def test_create_recurring_invalid_interval_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_recurring_payload(), "interval": "weekly"}
    # Interval validation happens before DB access.
    result = controller.create_recurring(payload)
    assert isinstance(result, str)


# FR-BUD-04: Dauerauftrag mit interval="yearly" gibt None zurück
def test_create_recurring_yearly_interval_returns_none():
    controller = _make_controller()
    payload = {**_valid_recurring_payload(), "interval": "yearly"}
    fake_recurring = SimpleNamespace(recurring_id=2)
    with patch("sqlmodel.Session.get", return_value=SimpleNamespace(category_id=3)), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=SimpleNamespace(account_id=1, status="aktiv")), \
        patch("src.data_access.repositories.recurring_repository.RecurringRepository.create", return_value=fake_recurring):
        result = controller.create_recurring(payload)

    assert result is None


# FR-BUD-04: create_recurring delegiert Payload korrekt an recurring_service
def test_create_recurring_delegates_to_service():
    controller = _make_controller()
    payload = _valid_recurring_payload()

    with patch("src.ui.controllers.recurring_controller.recurring_service.create_recurring") as mock_create:
        controller.create_recurring(payload)

    mock_create.assert_called_once_with(payload)


# FR-BUD-04: process_due_on_login gibt Anzahl gebuchter Daueraufträge zurück
def test_process_due_on_login_returns_int():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.recurring_controller.recurring_service.process_due_recurring_on_login",
        return_value=3,
    ):
        result = controller.process_due_on_login(user_id=1, login_date=date(2026, 4, 19))

    assert isinstance(result, int)
    assert result == 3


# FR-BUD-04: process_due_on_login gibt 0 zurück wenn keine fälligen Daueraufträge
def test_process_due_on_login_no_due_returns_zero():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.recurring_controller.recurring_service.process_due_recurring_on_login",
        return_value=0,
    ):
        result = controller.process_due_on_login(user_id=1, login_date=date(2026, 4, 19))

    assert result == 0


# FR-BUD-04: process_due_on_login übergibt user_id und login_date korrekt an Service
def test_process_due_on_login_delegates_to_service():
    controller = _make_controller()
    login_date = date(2026, 4, 19)

    with patch(
        "src.ui.controllers.recurring_controller.recurring_service.process_due_recurring_on_login",
        return_value=0,
    ) as mock_process:
        controller.process_due_on_login(user_id=2, login_date=login_date)

    mock_process.assert_called_once_with(2, login_date)


# FR-BUD-04: Fehler beim Verarbeiten gibt Fehlermeldung zurück
def test_process_due_on_login_error_returns_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.recurring_controller.recurring_service.process_due_recurring_on_login",
        side_effect=RuntimeError("DB-Fehler"),
    ):
        result = controller.process_due_on_login(user_id=1, login_date=date(2026, 4, 19))

    assert isinstance(result, str)
    assert "DB-Fehler" in result
