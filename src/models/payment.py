from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .payment_status import PaymentStatus


@dataclass
class Payment:
    payment_id: int
    source_account_id: int
    target_iban: str
    amount: float
    purpose: str
    created_at: datetime
    status: PaymentStatus = PaymentStatus.PENDING
