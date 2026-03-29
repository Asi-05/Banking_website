from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Account, AccountType


class AccountService(ABC):
    @abstractmethod
    def open_account(self, user_id: int, account_type: AccountType) -> Account:
        raise NotImplementedError

    @abstractmethod
    def close_account(self, account_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def transfer_between_own_accounts(self, from_account_id: int, to_account_id: int, amount: float) -> bool:
        raise NotImplementedError
