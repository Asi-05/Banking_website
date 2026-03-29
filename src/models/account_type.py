from __future__ import annotations

from enum import Enum


class AccountType(str, Enum):
    PRIVATE = "private"
    SAVINGS = "savings"