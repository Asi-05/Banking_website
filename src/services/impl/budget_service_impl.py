from __future__ import annotations

"""Budgetlogik fuer Erstellen/Aktualisieren und Berechnung des Ausgabestands."""

from typing import Optional

from ...exceptions import ValidationError
from ...models import Budget, TransactionType
from ..interface.budget_service import BudgetService
from .shared import InMemoryStore, ensure_category


class InMemoryBudgetService(BudgetService):
    """Implementiert monatliche Budgetoperationen auf In-Memory-Daten."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def set_budget(
        self,
        user_id: int,
        limit_amount: float,
        month: int,
        year: int,
        category_id: Optional[int] = None,
    ) -> Budget:
        """Erstellt oder aktualisiert genau ein Budget pro Nutzer/Monat/Jahr/Kategorie."""

        if user_id not in self.store.users:
            raise ValidationError(f"Unknown user_id: {user_id}")
        if limit_amount <= 0:
            raise ValidationError("limit_amount must be greater than 0")
        if month < 1 or month > 12:
            raise ValidationError("month must be between 1 and 12")
        if year < 1970:
            raise ValidationError("year is out of range")
        if category_id is not None:
            ensure_category(self.store, category_id)

        existing = self._find_existing_budget(user_id, month, year, category_id)
        if existing is None:
            budget = Budget(
                budget_id=self.store.next_budget_id(),
                user_id=user_id,
                limit_amount=limit_amount,
                month=month,
                year=year,
                category_id=category_id,
            )
            self.store.budgets[budget.budget_id] = budget
        else:
            existing.limit_amount = limit_amount
            budget = existing

        budget.current_spending = self._calculate_spending(user_id, month, year, category_id)
        return budget

    def check_budget_status(self, budget_id: int) -> Budget:
        """Berechnet Ausgaben neu und gibt den aktuellen Budgetzustand zurueck."""

        budget = self.store.budgets.get(budget_id)
        if budget is None:
            raise ValidationError(f"Unknown budget_id: {budget_id}")
        budget.current_spending = self._calculate_spending(
            budget.user_id, budget.month, budget.year, budget.category_id
        )
        return budget

    def _find_existing_budget(
        self, user_id: int, month: int, year: int, category_id: Optional[int]
    ) -> Optional[Budget]:
        """Sucht ein bestehendes Budget anhand des Eindeutigkeitsschluessels."""

        for budget in self.store.budgets.values():
            if (
                budget.user_id == user_id
                and budget.month == month
                and budget.year == year
                and budget.category_id == category_id
            ):
                return budget
        return None

    def _calculate_spending(self, user_id: int, month: int, year: int, category_id: Optional[int]) -> float:
        """Summiert Ausgabebuchungen fuer den angegebenen Monat und optional die Kategorie."""

        expenses = [
            tx
            for tx in self.store.transactions.values()
            if tx.user_id == user_id
            and tx.transaction_type == TransactionType.EXPENSE
            and tx.date_value.month == month
            and tx.date_value.year == year
        ]
        if category_id is None:
            return sum(tx.amount for tx in expenses)
        return sum(tx.amount for tx in expenses if tx.category_id == category_id)
