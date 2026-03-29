from __future__ import annotations

"""Logik fuer Dauerauftraege und deren Ausfuehrung bei Faelligkeit."""

from datetime import date

from ...exceptions import BusinessRuleViolation, NotFoundError, ValidationError
from ...models import AccountStatus, RecurrenceInterval, RecurringTransaction, Transaction, TransactionType
from ..interface.recurring_payment_service import RecurringPaymentService
from .shared import InMemoryStore, shift_interval, validate_iban


class InMemoryRecurringPaymentService(RecurringPaymentService):
    """Implementiert Dauerauftraege, die bei Faelligkeit zu normalen Buchungen werden."""

    def __init__(self, store: InMemoryStore, transaction_service) -> None:
        self.store = store
        self.transaction_service = transaction_service

    def create_recurring_payment(
        self,
        user_id: int,
        amount: float,
        category_id: int,
        account_id: int,
        target_iban: str,
        interval: RecurrenceInterval,
        start_date: date,
    ) -> RecurringTransaction:
        """Speichert eine Dauerauftragsdefinition nach erfolgreicher Validierung."""

        if isinstance(interval, str):
            try:
                interval = RecurrenceInterval(interval)
            except ValueError as exc:
                raise ValidationError("interval must be 'monthly' or 'yearly'") from exc

        if user_id not in self.store.users:
            raise NotFoundError(f"User {user_id} not found")
        if amount <= 0:
            raise ValidationError("amount must be greater than 0")
        account = self.store.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")
        if account.user_id != user_id:
            raise BusinessRuleViolation("Recurring payment account does not belong to user")
        if account.status != AccountStatus.OPEN:
            raise BusinessRuleViolation("Recurring payment account must be open")

        validate_iban(target_iban)

        recurring = RecurringTransaction(
            recurring_id=self.store.next_recurring_id(),
            user_id=user_id,
            amount=amount,
            category_id=category_id,
            account_id=account_id,
            target_iban=target_iban,
            interval=interval,
            start_date=start_date,
            is_active=True,
            last_generated_at=None,
        )
        self.store.recurring_transactions[recurring.recurring_id] = recurring
        return recurring

    def process_due_recurring_payments(self, user_id: int, current_date: date) -> list[Transaction]:
        """Erzeugt alle Dauerauftrags-Buchungen, die bis current_date faellig sind."""

        generated: list[Transaction] = []

        for recurring in self.store.recurring_transactions.values():
            if recurring.user_id != user_id or not recurring.is_active:
                continue

            next_due = recurring.start_date if recurring.last_generated_at is None else recurring.last_generated_at
            if recurring.last_generated_at is not None:
                next_due = shift_interval(next_due, recurring.interval.value)

            # Holt alle verpassten Ausfuehrungen nach (z.B. monatelang kein Login).
            while next_due <= current_date:
                tx = self.transaction_service.create_transaction(
                    user_id=user_id,
                    amount=recurring.amount,
                    transaction_type=TransactionType.EXPENSE,
                    date_value=next_due,
                    category_id=recurring.category_id,
                    account_id=recurring.account_id,
                    note=f"Recurring payment to {recurring.target_iban}",
                )
                generated.append(tx)
                recurring.last_generated_at = next_due
                next_due = shift_interval(next_due, recurring.interval.value)

        return generated
