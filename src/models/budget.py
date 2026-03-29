from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Budget:
    budget_id: int
    user_id: int
    limit_amount: float
    month: int
    year: int
    current_spending: float = 0.0
    category_id: Optional[int] = None

    @property
    def is_exceeded(self) -> bool:
        return self.current_spending >= self.limit_amount
