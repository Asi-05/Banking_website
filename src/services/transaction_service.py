from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..models import Transaction, TransactionType


class TransactionService(ABC):
    @abstractmethod
    def create_transaction(
        self,
        user_id: int,
        amount: float,
        transaction_type: TransactionType,
        date_value: date,
        category_id: int,
        account_id: Optional[int] = None,
        card_id: Optional[int] = None,
        creditcard_id: Optional[int] = None,
        note: str = "",
    ) -> Transaction:
        raise NotImplementedError

    @abstractmethod
    def update_transaction(self, transaction_id: int, new_values: dict) -> Transaction:
        raise NotImplementedError

    @abstractmethod
    def delete_transaction(self, transaction_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def filter_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
    ) -> list[Transaction]:
        raise NotImplementedError
