"""
UI Tests: PaymentController
Prüft FR-PAY-01, FR-PAY-02, FR-TRF-01, FR-TRF-02, FR-STM-01

FR-PAY-01: Inlandzahlung per IBAN
FR-PAY-02: Validierung von IBAN, Betrag, Quellkonto und Guthaben
FR-TRF-01: Umbuchung zwischen eigenen Konten als Soll-/Haben-Transaktion
FR-TRF-02: Schutz vor unzureichendem Guthaben oder identischem Quell-/Zielkonto
FR-STM-01: Kontoauszug als PDF generieren
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from src.ui.controllers.payment_controller import PaymentController


def _make_controller():
    return PaymentController()


def _valid_payment_payload():
    return {
        "from_account_id": 1,
        "target_iban": "CH5604835012345678009",
        "amount": 100.0,
        "purpose": "Miete April",
        "category_id": 4,
        "date": date.today().isoformat(),
    }


def _valid_transfer_payload():
    return {
        "from_account_id": 1,
        "to_account_id": 2,
        "amount": 200.0,
        "category_id": 9,
        "date": date.today(),
    }


# FR-PAY-01: Erfolgreiche Zahlung gibt None zurück
def test_create_payment_success_returns_none():
    controller = _make_controller()
    # Patch DB/repo/transaction side-effects, but let PaymentService validations run.
    fake_account = SimpleNamespace(account_id=1, balance=10000.0)
    fake_tx = SimpleNamespace(transaction_id=123)
    fake_payment = SimpleNamespace(payment_id=1, transaction_id=123)

    with patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account), \
        patch("src.services.payment_service.transaction_service.create_transaction", return_value=fake_tx), \
        patch("src.data_access.repositories.payment_repository.PaymentRepository.create_payment", return_value=fake_payment):
        result = controller.create_payment(_valid_payment_payload())

    assert result is None


# FR-PAY-02: Ungültige IBAN wird abgelehnt
def test_create_payment_invalid_iban_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_payment_payload(), "target_iban": "DE12345678"}
    # IBAN validation happens before any DB access; no repo patch needed.
    result = controller.create_payment(payload)

    assert isinstance(result, str)
    assert "IBAN" in result


# FR-PAY-02: Betrag = 0 wird abgelehnt
def test_create_payment_zero_amount_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_payment_payload(), "amount": 0.0}
    # Amount validation happens in service before DB access.
    result = controller.create_payment(payload)
    assert isinstance(result, str)


# FR-PAY-02: Unzureichendes Guthaben auf Quellkonto wird abgelehnt
def test_create_payment_insufficient_balance_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_payment_payload(), "amount": 99999.0}
    # Simulate account with low balance via AccountRepository.get_by_id
    fake_account = SimpleNamespace(account_id=1, balance=100.0)

    with patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", return_value=fake_account):
        result = controller.create_payment(payload)

    assert isinstance(result, str)
    assert "Kontosaldo" in result or "Unzureich" in result


# FR-PAY-01: create_payment delegiert korrekt an payment_service
def test_create_payment_delegates_to_service():
    controller = _make_controller()
    payload = _valid_payment_payload()
    # Keep delegation test as-is — it verifies the controller calls the service.
    with patch("src.ui.controllers.payment_controller.payment_service.create_payment") as mock_pay:
        controller.create_payment(payload)

    mock_pay.assert_called_once_with(payload)


# FR-TRF-01: Erfolgreiche Umbuchung gibt None zurück
def test_create_transfer_success_returns_none():
    controller = _make_controller()
    # Patch repositories and transaction service to simulate successful transfer.
    fake_from = SimpleNamespace(account_id=1, balance=1000.0, user_id=1, status="aktiv")
    fake_to = SimpleNamespace(account_id=2, balance=500.0, user_id=1, status="aktiv")
    fake_tx = SimpleNamespace(transaction_id=200)
    fake_transfer = SimpleNamespace(transfer_id=1, transaction_id=200)

    with patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", side_effect=[fake_from, fake_to]), \
        patch("src.services.payment_service.transaction_service.create_transaction", return_value=fake_tx), \
        patch("src.data_access.repositories.payment_repository.PaymentRepository.create_transfer", return_value=fake_transfer):
        result = controller.create_transfer(_valid_transfer_payload())

    assert result is None


# FR-TRF-02: Umbuchung mit identischem Quell- und Zielkonto wird abgelehnt
def test_create_transfer_same_account_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_transfer_payload(), "to_account_id": 1}  # gleich wie from_account_id=1
    # This validation happens in the service before DB access.
    result = controller.create_transfer(payload)
    assert isinstance(result, str)
    assert "identisch" in result or "gleich" in result.lower()


# FR-TRF-02: Umbuchung mit unzureichendem Guthaben wird abgelehnt
def test_create_transfer_insufficient_balance_returns_error_string():
    controller = _make_controller()
    payload = {**_valid_transfer_payload(), "amount": 999999.0}
    fake_from = SimpleNamespace(account_id=1, balance=100.0, user_id=1, status="aktiv")
    fake_to = SimpleNamespace(account_id=2, balance=500.0, user_id=1, status="aktiv")

    with patch("src.data_access.repositories.account_repository.AccountRepository.get_by_id", side_effect=[fake_from, fake_to]):
        result = controller.create_transfer(payload)

    assert isinstance(result, str)


# FR-TRF-01: create_transfer delegiert korrekt an payment_service
def test_create_transfer_delegates_to_service():
    controller = _make_controller()
    payload = _valid_transfer_payload()
    with patch("src.ui.controllers.payment_controller.payment_service.create_transfer") as mock_transfer:
        controller.create_transfer(payload)

    mock_transfer.assert_called_once_with(payload)


# FR-STM-01: Kontoauszug gibt einen String zurück (Pfad oder Inhalt)
def test_generate_statement_returns_string():
    controller = _make_controller()
    fake_pdf_path = "/tmp/kontoauszug_1_2026.pdf"
    # Patch repository listing to avoid DB dependency; let PDF writer run.
    fake_txn = SimpleNamespace(amount=100.0, date=date(2026, 4, 1), type="expense", note="Test")

    with patch("src.data_access.repositories.payment_repository.PaymentRepository.list_account_transactions_in_range", return_value=[fake_txn]):
        result = controller.generate_statement(
            account_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )

    assert isinstance(result, str)


# FR-STM-01: generate_statement übergibt korrekte Parameter an Service
def test_generate_statement_delegates_to_service():
    controller = _make_controller()
    with patch("src.ui.controllers.payment_controller.payment_service.generate_statement", return_value="path.pdf") as mock_stmt:
        controller.generate_statement(
            account_id=2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )

    mock_stmt.assert_called_once_with(2, date(2026, 3, 1), date(2026, 3, 31))


# FR-STM-01: Fehler bei Statement-Generierung gibt Fehlermeldung zurück
def test_generate_statement_error_returns_error_string():
    controller = _make_controller()
    # Simulate underlying service error bubbling up to controller.
    with patch("src.services.payment_service.PaymentService.generate_statement", side_effect=RuntimeError("PDF-Fehler")):
        result = controller.generate_statement(
            account_id=1,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )

    assert isinstance(result, str)
    assert "PDF" in result or "Fehler" in result
