from __future__ import annotations

from dataclasses import dataclass

from .card_status import CardStatus


@dataclass
class DebitCard:
    card_id: int
    account_id: int
    card_number_masked: str
    status: CardStatus = CardStatus.ACTIVE
