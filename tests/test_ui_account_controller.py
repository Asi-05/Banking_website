"""
UI Tests: AccountController
Prüft FR-ACC-01, FR-ACC-02

FR-ACC-01: Konten eröffnen und schließen, Statusanzeige
FR-ACC-02: Kontoschließung nur bei Kontostand = 0 zulässig
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.ui.controllers.account_controller import AccountController


def _make_controller():
    return AccountController()


def _valid_open_payload():
    return {
        "user_id": 1,
        "account_type": "privat",
        "iban": "CH5604835012345678009",
    }


# FR-ACC-01: Sidebar-Namenauflösung gibt Vor- und Nachnamen zurück
def test_get_current_user_display_name_returns_full_name():
    controller = _make_controller()

    fake_user = SimpleNamespace(first_name="Hermann", last_name="Muster")
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = False

    with patch("src.ui.controllers.account_controller.Session", return_value=mock_session), patch(
        "src.ui.controllers.account_controller.UserRepository.get_by_id",
        return_value=fake_user,
    ):
        result = controller.get_current_user_display_name(1)

    assert result == "Hermann Muster"


# FR-ACC-01: Unbekannter User liefert keinen Namen zurück
def test_get_current_user_display_name_returns_none_for_unknown_user():
    controller = _make_controller()

    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session.__exit__.return_value = False

    with patch("src.ui.controllers.account_controller.Session", return_value=mock_session), patch(
        "src.ui.controllers.account_controller.UserRepository.get_by_id",
        return_value=None,
    ):
        result = controller.get_current_user_display_name(999)

    assert result is None


# FR-ACC-01: Erfolgreiche Kontoeröffnung gibt None zurück
def test_open_account_success_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.account_controller.account_service.open_account", return_value=None):
        result = controller.open_account(_valid_open_payload())

    assert result is None


# FR-ACC-01: Kontoeröffnung ohne gültige Login-Daten (user_id) wird abgelehnt
def test_open_account_invalid_user_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.account_controller.account_service.open_account",
        side_effect=ValueError("Ungültiger User"),
    ):
        result = controller.open_account({**_valid_open_payload(), "user_id": None})

    assert isinstance(result, str)


# FR-ACC-01: open_account delegiert korrekt an account_service
def test_open_account_delegates_to_service():
    controller = _make_controller()
    payload = _valid_open_payload()

    with patch("src.ui.controllers.account_controller.account_service.open_account") as mock_open:
        controller.open_account(payload)

    mock_open.assert_called_once_with(payload)


# FR-ACC-02: Kontoschließung bei Kontostand = 0 gibt None zurück
def test_close_account_zero_balance_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.account_controller.account_service.close_account", return_value=None):
        result = controller.close_account(account_id=1)

    assert result is None


# FR-ACC-02: Kontoschließung bei Kontostand != 0 wird abgelehnt
def test_close_account_nonzero_balance_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.account_controller.account_service.close_account",
        side_effect=ValueError("Kontostand muss 0 sein"),
    ):
        result = controller.close_account(account_id=2)

    assert isinstance(result, str)
    assert "0" in result or "Kontostand" in result or result != ""


# FR-ACC-02: close_account delegiert korrekt an account_service
def test_close_account_delegates_to_service():
    controller = _make_controller()

    with patch("src.ui.controllers.account_controller.account_service.close_account") as mock_close:
        controller.close_account(account_id=5)

    mock_close.assert_called_once_with(5)


# FR-ACC-01: Kontoliste gibt Liste von Konten zurück
def test_list_accounts_returns_list():
    controller = _make_controller()
    fake_accounts = [
        SimpleNamespace(account_id=1, iban="CH5604835012345678009", account_type="privat", balance=1000.0),
        SimpleNamespace(account_id=2, iban="CH9300762011623852957", account_type="sparkonto", balance=500.0),
    ]

    with patch("src.ui.controllers.account_controller.account_service.list_accounts", return_value=fake_accounts):
        result = controller.list_accounts(user_id=1)

    assert isinstance(result, list)
    assert len(result) == 2


# FR-ACC-01: Kontoliste bei unbekanntem User gibt Fehlermeldung zurück
def test_list_accounts_unknown_user_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.account_controller.account_service.list_accounts",
        side_effect=ValueError("User nicht gefunden"),
    ):
        result = controller.list_accounts(user_id=9999)

    assert isinstance(result, str)


# FR-ACC-01: list_accounts übergibt user_id korrekt an Service
def test_list_accounts_passes_user_id_to_service():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.account_controller.account_service.list_accounts",
        return_value=[],
    ) as mock_list:
        controller.list_accounts(user_id=7)

    mock_list.assert_called_once_with(7)
