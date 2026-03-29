from __future__ import annotations

"""Logik fuer Zahlungen und Kontoauszug-Generierung."""

from datetime import date, datetime
from pathlib import Path

from ...exceptions import NotFoundError, ValidationError
from ...models import CategoryCode, Payment, PaymentStatus, StatementRequest, TransactionType
from ..interface.payment_service import PaymentService
from .shared import InMemoryStore, find_category_id, validate_iban


class InMemoryPaymentService(PaymentService):
    """Implementiert Inlandszahlungen und die Erstellung von Kontoauszuegen."""

    def __init__(self, store: InMemoryStore, transaction_service, base_path: Path) -> None:
        self.store = store
        self.transaction_service = transaction_service
        self.base_path = base_path

    def create_domestic_payment(
        self,
        source_account_id: int,
        target_iban: str,
        amount: float,
        purpose: str,
    ) -> Payment:
        """Erstellt eine Inlandszahlung nach Validierung und Saldenpruefung.

        Die Zahlung wird als Payment gespeichert und finanziell als
        Ausgabebuchung auf dem Quellkonto abgebildet.
        """

        if amount <= 0:
            raise ValidationError("amount must be greater than 0")
        if not purpose.strip():
            raise ValidationError("purpose must not be empty")

        account = self.store.accounts.get(source_account_id)
        if account is None:
            raise NotFoundError(f"Account {source_account_id} not found")

        normalized_iban = validate_iban(target_iban)
        payment_category_id = find_category_id(self.store, CategoryCode.OTHER)

        self.transaction_service.create_transaction(
            user_id=account.user_id,
            amount=amount,
            transaction_type=TransactionType.EXPENSE,
            date_value=date.today(),
            category_id=payment_category_id,
            account_id=source_account_id,
            note=f"Payment to {normalized_iban}: {purpose}",
        )

        payment = Payment(
            payment_id=self.store.next_payment_id(),
            source_account_id=source_account_id,
            target_iban=normalized_iban,
            amount=amount,
            purpose=purpose,
            created_at=datetime.utcnow(),
            status=PaymentStatus.SUCCESS,
        )
        self.store.payments[payment.payment_id] = payment
        return payment

    def generate_account_statement(self, account_id: int, start_date: date, end_date: date) -> StatementRequest:
        """Erzeugt eine einfache Auszugsdatei fuer den gewaehlten Kontozeitraum."""

        account = self.store.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")
        if start_date > end_date:
            raise ValidationError("start_date must not be greater than end_date")

        transactions = [
            tx
            for tx in self.store.transactions.values()
            if tx.account_id == account_id and start_date <= tx.date_value <= end_date
        ]
        transactions.sort(key=lambda tx: tx.date_value)

        statements_dir = self.base_path / "generated" / "statements"
        statements_dir.mkdir(parents=True, exist_ok=True)
        filename = f"statement_{account_id}_{start_date.isoformat()}_{end_date.isoformat()}.pdf"
        file_path = statements_dir / filename

        # Aktuell erzeugen wir eine minimale PDF-aehnliche Textdatei mit .pdf-Endung.
        # So bleibt der Ablauf testbar, bis eine vollstaendige PDF-Bibliothek integriert ist.
        lines = [
            "%PDF-1.4",
            "1 0 obj << /Type /Catalog >> endobj",
            "2 0 obj << /Length 0 >> stream",
            f"Account: {account_id}",
            f"Period: {start_date.isoformat()} - {end_date.isoformat()}",
        ]
        for tx in transactions:
            lines.append(
                f"{tx.date_value.isoformat()} | {tx.transaction_type.value} | {tx.amount:.2f} | {tx.note}"
            )
        lines.extend(["endstream endobj", "xref", "0 3", "0000000000 65535 f", "trailer <<>>", "%%EOF"])
        file_path.write_text("\n".join(lines), encoding="utf-8")

        statement = StatementRequest(
            statement_id=self.store.next_statement_id(),
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            generated_file_path=str(file_path),
        )
        self.store.statements[statement.statement_id] = statement
        return statement
