from __future__ import annotations

from enum import Enum


class CardStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    REPLACED = "replaced"
