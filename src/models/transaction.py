from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .transaction_type import TransactionType


@dataclass
class Transaction:
    transaction_id: int
    user_id: int
    amount: float
    transaction_type: TransactionType
    date_value: date
    category_id: int
    note: str = ""
    account_id: Optional[int] = None
    card_id: Optional[int] = None
    creditcard_id: Optional[int] = None

    def validate_charge_source(self) -> None:
        source_count = sum(
            [
                self.account_id is not None,
                self.card_id is not None,
                self.creditcard_id is not None,
            ]
        )
        if source_count != 1:
            raise ValueError(
                "Exactly one charge source must be set: account_id, card_id, or creditcard_id."
            )
