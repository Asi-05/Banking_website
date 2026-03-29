from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Session:
    token: str
    user_id: int
    created_at: datetime
    expires_at: datetime
