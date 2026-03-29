from __future__ import annotations

from enum import Enum


class AccountStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
