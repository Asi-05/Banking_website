"""
UI Tests: TransactionController
Prüft FR-FIN-01, FR-FIN-02, FR-FIN-03, FR-FIN-05, FR-FIN-06

FR-FIN-01: Manuelle Erfassung mit amount, type, date, category_id, note + Quellenfelder
FR-FIN-02: Validierung + Exactly-one-Regel (account_id ODER card_id ODER creditcard_id)
FR-FIN-03: Kategorie aus fester Liste
FR-FIN-05: Bearbeiten und Löschen mit Bestätigung
FR-FIN-06: Filter nach Datumsbereich und Kategorie
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from src.ui.controllers.transaction_controller import TransactionController


def _make_controller():
    return TransactionController()


def _valid_account_payload():
    return {
        "amount": 50.0,
        "type": "expense",
        "date": "2026-04-01",
        "category_id": 1,
        "note": "Test",
        "account_id": 1,
        "card_id": None,
        "creditcard_id": None,
    }


# FR-FIN-01: Erfolgreiche Transaktion mit Konto-Quelle gibt None zurück
def test_create_transaction_with_account_returns_none():
    controller = _make_controller()
    # Success path: mock repositories used by the service, let service logic run.
    fake_account = SimpleNamespace(account_id=1, balance=1000.0, status="aktiv")
    fake_tx = SimpleNamespace(transaction_id=1, amount=50.0, type="expense", account_id=1, card_id=None, creditcard_id=None)

    with patch("sqlmodel.Session.get", return_value=SimpleNamespace(category_id=1)), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account), \
        patch("src.data_access.repositories.account_repository.AccountRepository.save", return_value=fake_account), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.create", return_value=fake_tx):
        result = controller.create_transaction(_valid_account_payload())

    assert result is None


# FR-FIN-01: Erfolgreiche Transaktion mit Debitkarte gibt None zurück
def test_create_transaction_with_debit_card_returns_none():
    controller = _make_controller()
    payload = {**_valid_account_payload(), "account_id": None, "card_id": 5}
    fake_debit = SimpleNamespace(card_id=5, account_id=1, status="aktiv")
    fake_account = SimpleNamespace(account_id=1, balance=1000.0, status="aktiv")
    fake_tx = SimpleNamespace(transaction_id=2, amount=50.0, type="expense", account_id=None, card_id=5, creditcard_id=None)

    with patch("sqlmodel.Session.get", return_value=SimpleNamespace(category_id=1)), \
        patch("src.data_access.repositories.card_repository.CardRepository.get_debit_by_id", return_value=fake_debit), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account), \
        patch("src.data_access.repositories.account_repository.AccountRepository.save", return_value=fake_account), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.create", return_value=fake_tx):
        result = controller.create_transaction(payload)

    assert result is None


# FR-FIN-01: Erfolgreiche Transaktion mit Kreditkarte gibt None zurück
def test_create_transaction_with_credit_card_returns_none():
    controller = _make_controller()
    payload = {**_valid_account_payload(), "account_id": None, "creditcard_id": 3}
    fake_credit = SimpleNamespace(creditcard_id=3, status="aktiv", balance=0.0, limit=1000.0, user_id=1)
    fake_tx = SimpleNamespace(transaction_id=3, amount=50.0, type="expense", account_id=None, card_id=None, creditcard_id=3)

    with patch("sqlmodel.Session.get", return_value=SimpleNamespace(category_id=1)), \
        patch("src.data_access.repositories.card_repository.CardRepository.get_credit_by_id", return_value=fake_credit), \
        patch("src.data_access.repositories.card_repository.CardRepository.save_credit", return_value=fake_credit), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.create", return_value=fake_tx):
        result = controller.create_transaction(payload)

    assert result is None


# FR-FIN-02: Exactly-one-Verletzung (alle None) wird als Fehlermeldung zurückgegeben
def test_create_transaction_no_source_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_account_payload(), "account_id": None, "card_id": None, "creditcard_id": None}
    # Let the real TransactionService validation run (Exactly-One rule).
    result = controller.create_transaction(payload)
    assert isinstance(result, str)
    assert "Quelle" in result or "erforderlich" in result.lower()


# FR-FIN-02: Betrag <= 0 wird als Fehler zurückgegeben
def test_create_transaction_invalid_amount_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_account_payload(), "amount": -5.0}
    # Let real validation run for negative amount.
    result = controller.create_transaction(payload)
    assert isinstance(result, str)


# FR-FIN-02: Ungültiger Typ (nicht income/expense) wird abgelehnt
def test_create_transaction_invalid_type_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_account_payload(), "type": "unknown"}
    result = controller.create_transaction(payload)
    assert isinstance(result, str)


# FR-FIN-05: Erfolgreiches Bearbeiten gibt None zurück
def test_edit_transaction_success_returns_none():
    controller = _make_controller()
    # Let the real service run but mock repository methods it uses.
    fake_tx = SimpleNamespace(transaction_id=1, amount=50.0, type="expense", account_id=1, card_id=None, creditcard_id=None, category_id=1, date="2026-04-01", note="Test", is_settled=False)
    fake_account = SimpleNamespace(account_id=1, balance=1000.0, status="aktiv")

    with patch("sqlmodel.Session.get", return_value=SimpleNamespace(category_id=1)), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.get_by_id", return_value=fake_tx), \
        patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account), \
        patch("src.data_access.repositories.account_repository.AccountRepository.save", return_value=fake_account), \
        patch("src.data_access.repositories.transaction_repository.TransactionRepository.save", return_value=fake_tx):
        result = controller.edit_transaction(1, _valid_account_payload())

    assert result is None


# FR-FIN-05: Bearbeiten einer nicht-existenten Transaktion gibt Fehlermeldung
def test_edit_transaction_not_found_returns_error_string():
    controller = _make_controller()
    with patch(
        "src.ui.controllers.transaction_controller.transaction_service.edit_transaction",
        side_effect=ValueError("Transaktion nicht gefunden"),
    ):
        result = controller.edit_transaction(9999, _valid_account_payload())

    assert isinstance(result, str)


# FR-FIN-05: Löschen mit confirm=True gibt None zurück
def test_delete_transaction_confirmed_returns_none():
    controller = _make_controller()
    with patch("src.ui.controllers.transaction_controller.transaction_service.delete_transaction", return_value=None):
        result = controller.delete_transaction(1, confirm=True)

    assert result is None


# FR-FIN-05: Löschen ohne Bestätigung (confirm=False) wird abgelehnt
def test_delete_transaction_not_confirmed_returns_error_string():
    controller = _make_controller()
    with patch(
        "src.ui.controllers.transaction_controller.transaction_service.delete_transaction",
        side_effect=ValueError("Löschen nicht bestätigt"),
    ):
        result = controller.delete_transaction(1, confirm=False)

    assert isinstance(result, str)


# FR-FIN-06: Filter nach Datum gibt Liste zurück
def test_filter_transactions_by_date_returns_list():
    controller = _make_controller()
    fake_txn = SimpleNamespace(
        transaction_id=1,
        amount=100.0,
        date=date(2026, 4, 1),
        type="expense",
        note="Test",
        category_id=1,
        account_id=1,
        card_id=None,
        creditcard_id=None,
    )

    with patch(
        "src.ui.controllers.transaction_controller.transaction_service.filter_transactions",
        return_value=[fake_txn],
    ):
        result = controller.filter_transactions(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["transaction_id"] == 1
    assert result[0]["amount"] == 100.0


# FR-FIN-06: Filter ohne Ergebnis gibt leere Liste zurück
def test_filter_transactions_empty_result():
    controller = _make_controller()
    with patch(
        "src.ui.controllers.transaction_controller.transaction_service.filter_transactions",
        return_value=[],
    ):
        result = controller.filter_transactions(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
        )

    assert result == []


# FR-FIN-06: Ungültiger Datumsbereich (von > bis) gibt Fehlermeldung zurück
def test_filter_transactions_invalid_date_range_returns_error_string():
    controller = _make_controller()
    # Let the real service validate the date range
    result = controller.filter_transactions(
        start_date=date(2026, 4, 30),
        end_date=date(2026, 4, 1),
    )

    assert isinstance(result, str)


# FR-FIN-06: Filter nach Kategorie übergibt category_id korrekt an Service
def test_filter_transactions_passes_category_id_to_service():
    controller = _make_controller()

    with patch(
        "src.ui.controllers.transaction_controller.transaction_service.filter_transactions",
        return_value=[],
    ) as mock_filter:
        controller.filter_transactions(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            category_id=3,
            user_id=1,
        )

    mock_filter.assert_called_once_with(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        category_id=3,
        user_id=1,
        is_settled=None,
    )
