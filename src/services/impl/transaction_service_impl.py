from __future__ import annotations

"""Konkrete Transaktionslogik mit Saldo- und Kreditlimit-Effekten."""

from datetime import date
from typing import Optional

from ...exceptions import (
    BusinessRuleViolation,
    CreditLimitExceededError,
    InsufficientFundsError,
    NotFoundError,
    ValidationError,
)
from ...models import AccountStatus, Transaction, TransactionType
from ..interface.transaction_service import TransactionService
from .shared import InMemoryStore, ensure_category


class InMemoryTransactionService(TransactionService):
    """Implementiert Transaktions-Anwendungsfaelle auf dem In-Memory-Store."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def create_transaction(
        self,
        user_id: int,
        amount: float,
        transaction_type: TransactionType,
        date_value: date,
        category_id: int,
        account_id: Optional[int] = None,
        card_id: Optional[int] = None,
        creditcard_id: Optional[int] = None,
        note: str = "",
    ) -> Transaction:
        """Erstellt und speichert eine validierte Transaktion.

        Die Methode validiert Eingaben, wendet finanzielle Seiteneffekte an
        (Saldo oder Kreditnutzung), speichert die Transaktion und aktualisiert
        die Budgetauslastung.
        """

        if isinstance(transaction_type, str):
            try:
                transaction_type = TransactionType(transaction_type)
            except ValueError as exc:
                raise ValidationError("transaction_type must be 'income' or 'expense'") from exc

        self._validate_common(user_id, amount, date_value, category_id)

        transaction = Transaction(
            transaction_id=self.store.next_transaction_id(),
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            date_value=date_value,
            category_id=category_id,
            note=note,
            account_id=account_id,
            card_id=card_id,
            creditcard_id=creditcard_id,
        )
        transaction.validate_charge_source()

        # Seiteneffekte vor dem Speichern anwenden, damit ungueltige Buchungen nicht persistiert werden.
        self._apply_transaction_effect(transaction, reverse=False)
        self.store.transactions[transaction.transaction_id] = transaction
        self._recalculate_budgets_for_month(user_id, date_value.month, date_value.year)
        return transaction

    def update_transaction(self, transaction_id: int, new_values: dict) -> Transaction:
        """Aktualisiert eine bestehende Transaktion bei konsistentem Kontozustand."""

        current = self.store.transactions.get(transaction_id)
        if current is None:
            raise NotFoundError(f"Transaction {transaction_id} not found")

        # Das Update wird atomar angewendet: erst alte Buchung rueckgaengig,
        # dann neue anwenden. Bei ungueltigen Daten wird der alte Zustand wiederhergestellt.
        self._apply_transaction_effect(current, reverse=True)

        updated = Transaction(
            transaction_id=current.transaction_id,
            user_id=int(new_values.get("user_id", current.user_id)),
            amount=float(new_values.get("amount", current.amount)),
            transaction_type=self._parse_transaction_type(
                new_values.get("transaction_type", current.transaction_type)
            ),
            date_value=new_values.get("date_value", current.date_value),
            category_id=int(new_values.get("category_id", current.category_id)),
            note=str(new_values.get("note", current.note)),
            account_id=new_values.get("account_id", current.account_id),
            card_id=new_values.get("card_id", current.card_id),
            creditcard_id=new_values.get("creditcard_id", current.creditcard_id),
        )

        try:
            updated.validate_charge_source()
            self._validate_common(updated.user_id, updated.amount, updated.date_value, updated.category_id)
            self._apply_transaction_effect(updated, reverse=False)
            self.store.transactions[transaction_id] = updated
        except Exception:
            self._apply_transaction_effect(current, reverse=False)
            raise

        self._recalculate_budgets_for_month(current.user_id, current.date_value.month, current.date_value.year)
        if (current.date_value.month, current.date_value.year) != (updated.date_value.month, updated.date_value.year):
            self._recalculate_budgets_for_month(updated.user_id, updated.date_value.month, updated.date_value.year)
        return updated

    def delete_transaction(self, transaction_id: int) -> bool:
        """Loescht eine Transaktion und macht ihre Seiteneffekte rueckgaengig."""

        transaction = self.store.transactions.get(transaction_id)
        if transaction is None:
            raise NotFoundError(f"Transaction {transaction_id} not found")

        self._apply_transaction_effect(transaction, reverse=True)
        del self.store.transactions[transaction_id]
        self._recalculate_budgets_for_month(transaction.user_id, transaction.date_value.month, transaction.date_value.year)
        return True

    def filter_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
    ) -> list[Transaction]:
        """Gibt Transaktionen gefiltert nach optionalem Zeitraum und Kategorie zurueck."""

        if start_date and end_date and start_date > end_date:
            raise ValidationError("start_date must not be greater than end_date")

        result: list[Transaction] = []
        for transaction in self.store.transactions.values():
            if transaction.user_id != user_id:
                continue
            if start_date and transaction.date_value < start_date:
                continue
            if end_date and transaction.date_value > end_date:
                continue
            if category_id and transaction.category_id != category_id:
                continue
            result.append(transaction)

        result.sort(key=lambda item: item.date_value)
        return result

    def _validate_common(self, user_id: int, amount: float, date_value: date, category_id: int) -> None:
        """Validiert Nutzer, Betrag, Datumstyp und Existenz der Kategorie."""

        if user_id not in self.store.users:
            raise NotFoundError(f"User {user_id} not found")
        if amount <= 0:
            raise ValidationError("amount must be greater than 0")
        if not isinstance(date_value, date):
            raise ValidationError("date_value must be a date instance")
        ensure_category(self.store, category_id)

    def _parse_transaction_type(self, value) -> TransactionType:
        """Akzeptiert Enum oder String und normalisiert auf TransactionType."""

        if isinstance(value, TransactionType):
            return value
        if isinstance(value, str):
            try:
                return TransactionType(value)
            except ValueError as exc:
                raise ValidationError("transaction_type must be 'income' or 'expense'") from exc
        raise ValidationError("transaction_type has invalid type")

    def _apply_transaction_effect(self, transaction: Transaction, reverse: bool) -> None:
        """Wendet finanzielle Effekte je nach Belastungsquelle an oder macht sie rueckgaengig."""

        sign = -1 if reverse else 1

        if transaction.account_id is not None:
            self._apply_account_effect(transaction, transaction.account_id, sign)
            return

        if transaction.card_id is not None:
            card = self.store.debit_cards.get(transaction.card_id)
            if card is None:
                raise NotFoundError(f"Card {transaction.card_id} not found")
            if card.account_id not in self.store.accounts:
                raise NotFoundError(f"Account {card.account_id} not found")
            self._apply_account_effect(transaction, card.account_id, sign)
            return

        if transaction.creditcard_id is not None:
            credit_card = self.store.credit_cards.get(transaction.creditcard_id)
            if credit_card is None:
                raise NotFoundError(f"CreditCard {transaction.creditcard_id} not found")
            if credit_card.user_id != transaction.user_id:
                raise BusinessRuleViolation("Credit card does not belong to this user")
            self._apply_credit_card_effect(transaction, credit_card, sign)
            return

        raise ValidationError("No charge source set")

    def _apply_account_effect(self, transaction: Transaction, account_id: int, sign: int) -> None:
        """Wendet Saldoaenderungen fuer Einnahme-/Ausgabe-Transaktionen auf Konten an."""

        account = self.store.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")
        if account.user_id != transaction.user_id:
            raise BusinessRuleViolation("Account does not belong to this user")
        if account.status != AccountStatus.OPEN:
            raise BusinessRuleViolation("Account is not open")

        if transaction.transaction_type == TransactionType.INCOME:
            account.balance += sign * transaction.amount
            return

        if sign > 0 and account.balance < transaction.amount:
            raise InsufficientFundsError("Insufficient account balance")
        account.balance -= sign * transaction.amount

    def _apply_credit_card_effect(self, transaction: Transaction, credit_card, sign: int) -> None:
        """Wendet Aenderungen der Kreditkartennutzung fuer Ausgaben und Rueckzahlungen an."""

        if transaction.transaction_type == TransactionType.EXPENSE:
            delta = sign * transaction.amount
            if sign > 0 and transaction.amount > credit_card.available_limit:
                raise CreditLimitExceededError("Credit limit exceeded")
            credit_card.used_balance += delta
            if credit_card.used_balance < 0:
                credit_card.used_balance = 0.0
            return

        # Einnahmen auf der Kreditkarte werden als Rueckzahlung interpretiert.
        delta = sign * transaction.amount
        credit_card.used_balance -= delta
        if credit_card.used_balance < 0:
            credit_card.used_balance = 0.0

    def _recalculate_budgets_for_month(self, user_id: int, month: int, year: int) -> None:
        """Berechnet die aktuellen Ausgaben fuer alle passenden Monatsbudgets neu."""

        relevant = [
            budget
            for budget in self.store.budgets.values()
            if budget.user_id == user_id and budget.month == month and budget.year == year
        ]

        month_transactions = [
            transaction
            for transaction in self.store.transactions.values()
            if transaction.user_id == user_id
            and transaction.transaction_type == TransactionType.EXPENSE
            and transaction.date_value.month == month
            and transaction.date_value.year == year
        ]

        for budget in relevant:
            if budget.category_id is None:
                budget.current_spending = sum(item.amount for item in month_transactions)
            else:
                budget.current_spending = sum(
                    item.amount for item in month_transactions if item.category_id == budget.category_id
                )
