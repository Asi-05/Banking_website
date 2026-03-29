from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class AccountType(str, Enum):
    PRIVATE = "private"
    SAVINGS = "savings"


class AccountStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class CardStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    REPLACED = "replaced"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class RecurrenceInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class CategoryCode(str, Enum):
    TRANSPORT = "Transport"
    SHOPPING = "Einkaeufe"
    INSURANCE = "Versicherungen"
    RENT = "Miete"
    TAXES = "Steuern"
    LEISURE = "Freizeit"
    SAVINGS = "Sparen"
    WELL_BEING = "Well being"
    INTERNAL_TRANSFER = "Kontuebertrag"
    OTHER = "Sonstiges"


@dataclass
class User:
    user_id: int
    contract_number: str
    password_hash: str
    full_name: str


@dataclass
class Session:
    token: str
    user_id: int
    created_at: datetime
    expires_at: datetime


@dataclass
class Category:
    category_id: int
    code: CategoryCode
    display_name: str


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


@dataclass
class DebitCard:
    card_id: int
    account_id: int
    card_number_masked: str
    status: CardStatus = CardStatus.ACTIVE


@dataclass
class CreditCard:
    creditcard_id: int
    user_id: int
    card_number_masked: str
    credit_limit: float
    used_balance: float = 0.0
    status: CardStatus = CardStatus.ACTIVE

    @property
    def available_limit(self) -> float:
        return self.credit_limit - self.used_balance


@dataclass
class Transaction:
    transaction_id: int
    user_id: int
    amount: float
    transaction_type: TransactionType
    date_value: date
    category_id: int
    note: str = ""
    account_id: Optional[int] = None
    card_id: Optional[int] = None
    creditcard_id: Optional[int] = None

    def validate_charge_source(self) -> None:
        source_count = sum(
            [
                self.account_id is not None,
                self.card_id is not None,
                self.creditcard_id is not None,
            ]
        )
        if source_count != 1:
            raise ValueError(
                "Exactly one charge source must be set: account_id, card_id, or creditcard_id."
            )


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


@dataclass
class RecurringTransaction:
    recurring_id: int
    user_id: int
    amount: float
    category_id: int
    account_id: int
    target_iban: str
    interval: RecurrenceInterval
    start_date: date
    is_active: bool = True
    last_generated_at: Optional[date] = None


@dataclass
class Payment:
    payment_id: int
    source_account_id: int
    target_iban: str
    amount: float
    purpose: str
    created_at: datetime
    status: PaymentStatus = PaymentStatus.PENDING


@dataclass
class StatementRequest:
    statement_id: int
    account_id: int
    start_date: date
    end_date: date
    generated_file_path: Optional[str] = None


@dataclass
class ChartData:
    label: str
    income: float
    expenses: float


@dataclass
class DashboardSummary:
    total_balance: float
    total_income: float
    total_expenses: float
    chart_data: list[ChartData] = field(default_factory=list)
