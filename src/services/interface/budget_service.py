from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ...models import Budget


class BudgetService(ABC):
    @abstractmethod
    def set_budget(
        self,
        user_id: int,
        limit_amount: float,
        month: int,
        year: int,
        category_id: Optional[int] = None,
    ) -> Budget:
        raise NotImplementedError

    @abstractmethod
    def check_budget_status(self, budget_id: int) -> Budget:
        raise NotImplementedError
