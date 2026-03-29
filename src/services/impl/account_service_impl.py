from __future__ import annotations

"""Konten-Lebenszykluslogik (eröffnen, schließen, interne Überweisung)."""

from datetime import date

from ...exceptions import AccountClosureError, BusinessRuleViolation, NotFoundError, ValidationError
from ...models import Account, AccountStatus, AccountType, CategoryCode, TransactionType
from ..interface.account_service import AccountService
from .shared import InMemoryStore, find_category_id, validate_iban


class InMemoryAccountService(AccountService):
    """Implementiert kontobezogene Anwendungsfälle inklusive Geschäftsregel-Prüfungen."""

    def __init__(self, store: InMemoryStore, transaction_service) -> None:
        self.store = store
        self.transaction_service = transaction_service

    def open_account(self, user_id: int, account_type: AccountType) -> Account:
        """Eröffnet ein neues Konto für einen Nutzer.

        In dieser In-Memory-Implementierung wird die IBAN deterministisch
        aus der nächsten Konto-ID erzeugt.
        """

        if user_id not in self.store.users:
            raise ValidationError(f"Unknown user_id: {user_id}")
        if isinstance(account_type, str):
            try:
                account_type = AccountType(account_type)
            except ValueError as exc:
                raise ValidationError("account_type must be 'private' or 'savings'") from exc
        if not isinstance(account_type, AccountType):
            raise ValidationError("account_type must be AccountType")

        account_id = self.store.next_account_id()
        account = Account(
            account_id=account_id,
            user_id=user_id,
            account_type=account_type,
            iban=validate_iban(f"CH93{account_id:018d}"),
        )
        self.store.accounts[account.account_id] = account
        return account

    def close_account(self, account_id: int) -> bool:
        """Schließt ein Konto nur dann, wenn der Kontostand exakt null ist."""

        account = self.store.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")
        if not account.can_be_closed():
            raise AccountClosureError("Account can only be closed with zero balance")
        account.status = AccountStatus.CLOSED
        return True

    def transfer_between_own_accounts(self, from_account_id: int, to_account_id: int, amount: float) -> bool:
        """Überweist Geld zwischen zwei Konten desselben Nutzers.

        Die Überweisung wird als zwei Buchungen modelliert: Ausgabe auf dem
        Quellkonto, Einnahme auf dem Zielkonto.
        """

        if from_account_id == to_account_id:
            raise BusinessRuleViolation("Source and target account must differ")
        if amount <= 0:
            raise ValidationError("amount must be greater than 0")

        source = self.store.accounts.get(from_account_id)
        target = self.store.accounts.get(to_account_id)
        if source is None or target is None:
            raise NotFoundError("Source or target account not found")
        if source.user_id != target.user_id:
            raise BusinessRuleViolation("Transfers are only allowed between own accounts")

        transfer_category_id = find_category_id(self.store, CategoryCode.INTERNAL_TRANSFER)
        today = date.today()

        self.transaction_service.create_transaction(
            user_id=source.user_id,
            amount=amount,
            transaction_type=TransactionType.EXPENSE,
            date_value=today,
            category_id=transfer_category_id,
            account_id=from_account_id,
            note="Internal transfer - debit",
        )
        self.transaction_service.create_transaction(
            user_id=source.user_id,
            amount=amount,
            transaction_type=TransactionType.INCOME,
            date_value=today,
            category_id=transfer_category_id,
            account_id=to_account_id,
            note="Internal transfer - credit",
        )
        return True
