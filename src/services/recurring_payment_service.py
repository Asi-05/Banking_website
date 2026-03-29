from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models import RecurrenceInterval, RecurringTransaction, Transaction


class RecurringPaymentService(ABC):
    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def process_due_recurring_payments(self, user_id: int, current_date: date) -> list[Transaction]:
        raise NotImplementedError
