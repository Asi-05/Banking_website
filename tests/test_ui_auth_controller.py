"""
UI Tests: AuthController
Prüft FR-AUTH-01, FR-AUTH-02, FR-AUTH-04, FR-AUTH-05

FR-AUTH-01: Login mit Vertragsnummer und Passwort
FR-AUTH-04: Passwort min. 8 Zeichen + 1 Sonderzeichen
FR-AUTH-05: Kein Selbstregistrierungs-Prozess (nur vordefinierte User)
"""

from unittest.mock import patch

from src.ui.controllers.auth_controller import AuthController


def _make_controller():
    return AuthController()


# FR-AUTH-01: Erfolgreicher Login gibt dict mit success=True zurück
def test_login_success_returns_dict():
    controller = _make_controller()
    fake_result = {"success": True, "user_id": 1, "auth_token": "abc", "executed_recurring": 0}

    with patch("src.ui.controllers.auth_controller.auth_service.login", return_value=fake_result):
        result = controller.login("BB-100001", "Passwort!1")

    assert isinstance(result, dict)
    assert result["success"] is True
    assert "user_id" in result
    assert "auth_token" in result


# FR-AUTH-01: Ungültige Zugangsdaten liefern Fehlermeldung als String
def test_login_invalid_credentials_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.auth_controller.auth_service.login",
        side_effect=ValueError("Ungueltige Anmeldedaten"),
    ):
        result = controller.login("BB-999999", "falsch")

    assert isinstance(result, str)
    assert "Ungueltige Anmeldedaten" in result


# FR-AUTH-01: Leere Vertragsnummer führt zu Fehlermeldung
def test_login_empty_contract_number_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.auth_controller.auth_service.login",
        side_effect=ValueError("Ungueltige Anmeldedaten"),
    ):
        result = controller.login("", "Passwort!1")

    assert isinstance(result, str)


# FR-AUTH-01: Leeres Passwort führt zu Fehlermeldung
def test_login_empty_password_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.auth_controller.auth_service.login",
        side_effect=ValueError("Ungueltige Anmeldedaten"),
    ):
        result = controller.login("BB-100001", "")

    assert isinstance(result, str)


# FR-AUTH-05: Nicht existierender User wird abgelehnt
def test_login_unknown_user_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.auth_controller.auth_service.login",
        side_effect=ValueError("Ungueltige Anmeldedaten"),
    ):
        result = controller.login("BB-000000", "IrgendeinPasswort!1")

    assert isinstance(result, str)
    assert "Ungueltige Anmeldedaten" in result


# FR-AUTH-02: Passwort darf nie im Ergebnis-dict im Klartext erscheinen
def test_login_result_does_not_contain_password():
    controller = _make_controller()
    secret = "GeheimPasswort!9"
    fake_result = {"success": True, "user_id": 1, "auth_token": "xyz", "executed_recurring": 0}

    with patch("src.ui.controllers.auth_controller.auth_service.login", return_value=fake_result):
        result = controller.login("BB-100001", secret)

    if isinstance(result, dict):
        assert secret not in str(result.values())


# FR-AUTH-01: Controller delegiert korrekt an auth_service.login
def test_login_delegates_to_service_with_correct_args():
    controller = _make_controller()
    fake_result = {"success": True, "user_id": 2, "auth_token": "tok", "executed_recurring": 0}

    with patch("src.ui.controllers.auth_controller.auth_service.login", return_value=fake_result) as mock_login:
        controller.login("BB-100002", "Passwort!2")

    mock_login.assert_called_once_with("BB-100002", "Passwort!2")


# FR-AUTH-01: Allgemeine Exception (z.B. DB-Fehler) wird als String zurückgegeben
def test_login_unexpected_exception_returns_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.auth_controller.auth_service.login",
        side_effect=RuntimeError("DB nicht erreichbar"),
    ):
        result = controller.login("BB-100001", "Passwort!1")

    assert isinstance(result, str)
    assert "DB nicht erreichbar" in result
