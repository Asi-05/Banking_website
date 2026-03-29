from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .recurrence_interval import RecurrenceInterval


@dataclass
class RecurringTransaction:
    recurring_id: int
    user_id: int
    amount: float
    category_id: int
    account_id: int
    target_iban: str
    interval: RecurrenceInterval
    start_date: date
    is_active: bool = True
    last_generated_at: Optional[date] = None
