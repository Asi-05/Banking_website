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
from types import SimpleNamespace

from src.ui.controllers.card_controller import CardController


def _make_controller():
    return CardController()


# FR-CARD-03: Debitkarte für Privatkonto bestellen gibt None zurück
def test_order_debit_card_success_returns_none():
    controller = _make_controller()
    fake_account = SimpleNamespace(account_id=1, user_id=1, account_type="privat", status="aktiv")
    fake_card = SimpleNamespace(card_id=11)

    with patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account), \
        patch("src.data_access.repositories.card_repository.CardRepository.list_active_debit_by_account", return_value=[]), \
        patch("src.data_access.repositories.card_repository.CardRepository.create_debit", return_value=fake_card):
        result = controller.order_debit_card(account_id=1)

    assert result is None


# FR-CARD-03: Debitkarte für Sparkonto wird abgelehnt
def test_order_debit_card_savings_account_returns_error_string():
    controller = _make_controller()
    # Simulate a savings account so the service raises ValueError
    fake_account = SimpleNamespace(account_id=2, account_type="spar", user_id=1)
    with patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account):
        result = controller.order_debit_card(account_id=2)

    assert isinstance(result, str)
    assert "Privat" in result


# FR-CARD-03: order_debit_card delegiert korrekt an card_service
def test_order_debit_card_delegates_to_service():
    controller = _make_controller()

    with patch("src.ui.controllers.card_controller.card_service.order_debit_card") as mock_order:
        controller.order_debit_card(account_id=3)

    mock_order.assert_called_once_with(3)


# FR-CARD-01: Debitkarte sperren gibt None zurück
def test_block_debit_card_success_returns_none():
    controller = _make_controller()
    fake_card = SimpleNamespace(card_id=1, account_id=1, status="aktiv")
    # provide a block() method expected by service
    def _block():
        fake_card.status = "gesperrt"

    fake_card.block = _block

    with patch("src.data_access.repositories.card_repository.CardRepository.get_debit_by_id", return_value=fake_card), \
        patch("src.data_access.repositories.card_repository.CardRepository.save_debit", return_value=fake_card):
        result = controller.block_debit_card(card_id=1)

    assert result is None


# FR-CARD-01: Sperren einer nicht-existenten Karte gibt Fehlermeldung
def test_block_debit_card_not_found_returns_error_string():
    controller = _make_controller()
    # Simulate CardRepository returning None
    with patch("src.data_access.repositories.card_repository.CardRepository.get_debit_by_id", return_value=None):
        result = controller.block_debit_card(card_id=9999)

    assert isinstance(result, str)


# FR-CARD-02: Ersatzkarte bestellen gibt None zurück
def test_replace_debit_card_success_returns_none():
    controller = _make_controller()
    old_card = SimpleNamespace(card_id=1, account_id=1, status="gesperrt")
    # provide replace() method expected by service
    def _replace():
        old_card.status = "ersetzt"

    old_card.replace = _replace
    new_card = SimpleNamespace(card_id=2)

    with patch("src.data_access.repositories.card_repository.CardRepository.get_debit_by_id", return_value=old_card), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=SimpleNamespace(account_id=1, user_id=1)), \
        patch("src.data_access.repositories.card_repository.CardRepository.create_debit", return_value=new_card), \
        patch("src.data_access.repositories.card_repository.CardRepository.save_debit", return_value=old_card), \
        patch("src.data_access.repositories.account_repository.AccountRepository.list_by_user", return_value=[SimpleNamespace(account_id=1)]), \
        patch("src.data_access.repositories.card_repository.CardRepository.list_active_debit_by_account", return_value=[]):
        result = controller.replace_debit_card(card_id=1)

    assert result is None


# FR-CARD-02: Ersatzkarte für nicht-gesperrte Karte gibt Fehlermeldung
def test_replace_debit_card_not_blocked_returns_error_string():
    controller = _make_controller()
    # Simulate old card not blocked -> service should raise ValueError
    old_card = SimpleNamespace(card_id=1, account_id=1, status="aktiv")
    with patch("src.data_access.repositories.card_repository.CardRepository.get_debit_by_id", return_value=old_card), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=SimpleNamespace(account_id=1, user_id=1)):
        result = controller.replace_debit_card(card_id=1)

    assert isinstance(result, str)


# FR-CC-01: Kreditkarte anlegen gibt None zurück
def test_create_credit_card_success_returns_none():
    controller = _make_controller()
    payload = {"user_id": 1, "credit_limit": 5000.0}
    fake_card = SimpleNamespace(creditcard_id=1)
    with patch("src.data_access.repositories.user_repository.UserRepository.get_by_id", return_value=SimpleNamespace(user_id=1)), \
        patch("src.data_access.repositories.card_repository.CardRepository.create_credit", return_value=fake_card):
        result = controller.create_credit_card({"user_id": 1, "desired_limit": 5000.0})

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
    # Let the real service validation run. CardService expects the key
    # "desired_limit" and validates it before DB access.
    payload = {"user_id": 1, "desired_limit": -100.0}

    result = controller.create_credit_card(payload)

    assert isinstance(result, str)


# FR-CC-03: Kreditkarte sperren gibt None zurück
def test_block_credit_card_success_returns_none():
    controller = _make_controller()
    fake_card = SimpleNamespace(creditcard_id=1, user_id=1, status="aktiv")
    def _block():
        fake_card.status = "gesperrt"

    fake_card.block = _block

    with patch("src.data_access.repositories.card_repository.CardRepository.get_credit_by_id", return_value=fake_card), \
        patch("src.data_access.repositories.card_repository.CardRepository.save_credit", return_value=fake_card):
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
    old_card = SimpleNamespace(creditcard_id=1, user_id=1, status="gesperrt", limit=3000.0, balance=100.0)
    def _replace():
        old_card.status = "ersetzt"

    old_card.replace = _replace
    new_card = SimpleNamespace(creditcard_id=2)

    with patch("src.data_access.repositories.card_repository.CardRepository.get_credit_by_id", return_value=old_card), \
        patch("src.data_access.repositories.card_repository.CardRepository.save_credit", return_value=old_card), \
        patch("src.data_access.repositories.card_repository.CardRepository.create_credit", return_value=new_card):
        result = controller.replace_credit_card(creditcard_id=1)

    assert result is None


# FR-CC-03: Ersetzen einer nicht-gesperrten Kreditkarte gibt Fehlermeldung
def test_replace_credit_card_not_blocked_returns_error_string():
    controller = _make_controller()
    # Let the real service run but return a credit card that is not blocked
    # so the service raises the expected ValueError.
    fake_card = SimpleNamespace(creditcard_id=1, user_id=1, status="aktiv", limit=3000.0, balance=0.0)
    with patch("src.data_access.repositories.card_repository.CardRepository.get_credit_by_id", return_value=fake_card):
        result = controller.replace_credit_card(creditcard_id=1)

    assert isinstance(result, str)
