from __future__ import annotations

from dataclasses import dataclass

from .card_status import CardStatus


@dataclass
class CreditCard:
    creditcard_id: int
    user_id: int
    card_number_masked: str
    credit_limit: float
    used_balance: float = 0.0
    status: CardStatus = CardStatus.ACTIVE

    @property
    def available_limit(self) -> float:
        return self.credit_limit - self.used_balance
