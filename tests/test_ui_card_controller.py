"""
UI Tests: CardController
Prüft FR-CARD-01, FR-CARD-02, FR-CARD-03, FR-CC-01, FR-CC-02, FR-CC-03

FR-CARD-01: Karte sofort sperren, Status sofort sichtbar
FR-CARD-02: Ersatzkarte aus gesperrtem Kontext bestellen
FR-CARD-03: Karte verpflichtend einem Konto zugeordnet, nur für Privatkonten
FR-CC-01: Unabhängige Kreditkarte pro User mit Kreditrahmen
FR-CC-02: Kreditkartenbuchung prüft available_limit; used_balance aktualisieren
FR-CC-03: Kreditkarte sperren und ersetzen
"""

from unittest.mock import patch

from src.ui.controllers.card_controller import CardController


def _make_controller():
    return CardController()


# FR-CARD-03: Debitkarte für Privatkonto bestellen gibt None zurück
def test_order_debit_card_success_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.order_debit_card", return_value=None):
        result = controller.order_debit_card(account_id=1)

    assert result is None


# FR-CARD-03: Debitkarte für Sparkonto wird abgelehnt
def test_order_debit_card_savings_account_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.card_controller.card_service.order_debit_card",
        side_effect=ValueError("Nur für Privatkonten"),
    ):
        result = controller.order_debit_card(account_id=2)

    assert isinstance(result, str)
    assert "Privat" in result or result != ""


# FR-CARD-03: order_debit_card delegiert korrekt an card_service
def test_order_debit_card_delegates_to_service():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.order_debit_card") as mock_order:
        controller.order_debit_card(account_id=3)

    mock_order.assert_called_once_with(3)


# FR-CARD-01: Debitkarte sperren gibt None zurück
def test_block_debit_card_success_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.block_debit_card", return_value=None):
        result = controller.block_debit_card(card_id=1)

    assert result is None


# FR-CARD-01: Sperren einer nicht-existenten Karte gibt Fehlermeldung
def test_block_debit_card_not_found_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.card_controller.card_service.block_debit_card",
        side_effect=ValueError("Karte nicht gefunden"),
    ):
        result = controller.block_debit_card(card_id=9999)

    assert isinstance(result, str)


# FR-CARD-02: Ersatzkarte bestellen gibt None zurück
def test_replace_debit_card_success_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.replace_debit_card", return_value=None):
        result = controller.replace_debit_card(card_id=1)

    assert result is None


# FR-CARD-02: Ersatzkarte für nicht-gesperrte Karte gibt Fehlermeldung
def test_replace_debit_card_not_blocked_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.card_controller.card_service.replace_debit_card",
        side_effect=ValueError("Karte ist nicht gesperrt"),
    ):
        result = controller.replace_debit_card(card_id=1)

    assert isinstance(result, str)


# FR-CC-01: Kreditkarte anlegen gibt None zurück
def test_create_credit_card_success_returns_none():
    controller = _make_controller()
    payload = {"user_id": 1, "credit_limit": 5000.0}

    with patch("src.ui.controllers.card_controller.card_service.create_credit_card", return_value=None):
        result = controller.create_credit_card(payload)

    assert result is None


# FR-CC-01: create_credit_card delegiert Payload korrekt an card_service
def test_create_credit_card_delegates_to_service():
    controller = _make_controller()
    payload = {"user_id": 1, "credit_limit": 3000.0}

    with patch("src.ui.controllers.card_controller.card_service.create_credit_card") as mock_create:
        controller.create_credit_card(payload)

    mock_create.assert_called_once_with(payload)


# FR-CC-02: Kreditkarte mit unzureichendem Limit wird abgelehnt
def test_create_credit_card_invalid_limit_returns_error_string():
    controller = _make_controller()
    payload = {"user_id": 1, "credit_limit": -100.0}

    with patch(
        "src.ui.controllers.card_controller.card_service.create_credit_card",
        side_effect=ValueError("Ungültiger Kreditrahmen"),
    ):
        result = controller.create_credit_card(payload)

    assert isinstance(result, str)


# FR-CC-03: Kreditkarte sperren gibt None zurück
def test_block_credit_card_success_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.block_credit_card", return_value=None):
        result = controller.block_credit_card(creditcard_id=1)

    assert result is None


# FR-CC-03: Kreditkarte sperren delegiert korrekt an card_service
def test_block_credit_card_delegates_to_service():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.block_credit_card") as mock_block:
        controller.block_credit_card(creditcard_id=4)

    mock_block.assert_called_once_with(4)


# FR-CC-03: Kreditkarte ersetzen gibt None zurück
def test_replace_credit_card_success_returns_none():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.replace_credit_card", return_value=None):
        result = controller.replace_credit_card(creditcard_id=1)

    assert result is None


# FR-CC-03: Ersetzen einer nicht-gesperrten Kreditkarte gibt Fehlermeldung
def test_replace_credit_card_not_blocked_returns_error_string():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.card_controller.card_service.replace_credit_card",
        side_effect=ValueError("Kreditkarte ist nicht gesperrt"),
    ):
        result = controller.replace_credit_card(creditcard_id=1)

    assert isinstance(result, str)
