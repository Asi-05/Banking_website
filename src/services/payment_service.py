from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models import Payment, StatementRequest


class PaymentService(ABC):
    @abstractmethod
    def create_domestic_payment(
        self,
        source_account_id: int,
        target_iban: str,
        amount: float,
        purpose: str,
    ) -> Payment:
        raise NotImplementedError

    @abstractmethod
    def generate_account_statement(
        self, account_id: int, start_date: date, end_date: date
    ) -> StatementRequest:
        raise NotImplementedError
