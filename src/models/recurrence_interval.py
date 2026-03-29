from __future__ import annotations

from enum import Enum


class RecurrenceInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
