from __future__ import annotations

from dataclasses import dataclass

from .account_status import AccountStatus
from .account_type import AccountType


@dataclass
class Account:
    account_id: int
    user_id: int
    account_type: AccountType
    iban: str
    balance: float = 0.0
    status: AccountStatus = AccountStatus.OPEN

    def can_be_closed(self) -> bool:
        return self.balance == 0.0
