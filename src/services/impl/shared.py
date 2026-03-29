from __future__ import annotations

"""Gemeinsame Hilfsfunktionen und In-Memory-Persistenzbausteine.

Dieses Modul zentralisiert kleine wiederverwendbare Funktionen (Validierung,
Hashing, Datumslogik) sowie den In-Memory-Store, den alle konkreten
Service-Implementierungen gemeinsam nutzen.
"""

from dataclasses import dataclass, field
from datetime import date
import hashlib
import re
from typing import Optional

from ...exceptions import NotFoundError, ValidationError
from ...models import (
    Account,
    Budget,
    CardStatus,
    Category,
    CategoryCode,
    CreditCard,
    DebitCard,
    Payment,
    RecurringTransaction,
    Session,
    StatementRequest,
    Transaction,
    User,
)


IBAN_REGEX = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")
PASSWORD_SPECIAL_REGEX = re.compile(r"[^A-Za-z0-9]")


@dataclass
class InMemoryStore:
    """Einfache In-Memory-Alternative zu einer Datenbank.

    Jedes Dictionary repraesentiert eine tabellenartige Sammlung mit ID als
    Schluessel. Die *_seq-Zaehler simulieren auto-increment Primarschluessel.
    """

    users: dict[int, User] = field(default_factory=dict)
    users_by_contract: dict[str, int] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)

    categories: dict[int, Category] = field(default_factory=dict)

    accounts: dict[int, Account] = field(default_factory=dict)
    debit_cards: dict[int, DebitCard] = field(default_factory=dict)
    credit_cards: dict[int, CreditCard] = field(default_factory=dict)

    transactions: dict[int, Transaction] = field(default_factory=dict)
    budgets: dict[int, Budget] = field(default_factory=dict)
    recurring_transactions: dict[int, RecurringTransaction] = field(default_factory=dict)
    payments: dict[int, Payment] = field(default_factory=dict)
    statements: dict[int, StatementRequest] = field(default_factory=dict)

    _user_id_seq: int = 1
    _account_id_seq: int = 1
    _debit_card_id_seq: int = 1
    _credit_card_id_seq: int = 1
    _transaction_id_seq: int = 1
    _budget_id_seq: int = 1
    _recurring_id_seq: int = 1
    _payment_id_seq: int = 1
    _statement_id_seq: int = 1

    def next_user_id(self) -> int:
        current = self._user_id_seq
        self._user_id_seq += 1
        return current

    def next_account_id(self) -> int:
        current = self._account_id_seq
        self._account_id_seq += 1
        return current

    def next_debit_card_id(self) -> int:
        current = self._debit_card_id_seq
        self._debit_card_id_seq += 1
        return current

    def next_credit_card_id(self) -> int:
        current = self._credit_card_id_seq
        self._credit_card_id_seq += 1
        return current

    def next_transaction_id(self) -> int:
        current = self._transaction_id_seq
        self._transaction_id_seq += 1
        return current

    def next_budget_id(self) -> int:
        current = self._budget_id_seq
        self._budget_id_seq += 1
        return current

    def next_recurring_id(self) -> int:
        current = self._recurring_id_seq
        self._recurring_id_seq += 1
        return current

    def next_payment_id(self) -> int:
        current = self._payment_id_seq
        self._payment_id_seq += 1
        return current

    def next_statement_id(self) -> int:
        current = self._statement_id_seq
        self._statement_id_seq += 1
        return current


def bootstrap_default_categories(store: InMemoryStore) -> None:
    """Legt den festen Kategoriesatz genau einmal an.

    Die Anforderungen definieren eine feste Kategorieliste. Diese Funktion
    befuellt sie, wenn der Store noch leer ist.
    """

    if store.categories:
        return

    ordered_codes = [
        CategoryCode.TRANSPORT,
        CategoryCode.SHOPPING,
        CategoryCode.INSURANCE,
        CategoryCode.RENT,
        CategoryCode.TAXES,
        CategoryCode.LEISURE,
        CategoryCode.SAVINGS,
        CategoryCode.WELL_BEING,
        CategoryCode.INTERNAL_TRANSFER,
        CategoryCode.OTHER,
    ]

    for idx, code in enumerate(ordered_codes, start=1):
        store.categories[idx] = Category(category_id=idx, code=code, display_name=code.value)


def ensure_category(store: InMemoryStore, category_id: int) -> Category:
    """Gibt die Kategorie zurueck oder wirft einen Validierungsfehler."""

    category = store.categories.get(category_id)
    if category is None:
        raise ValidationError(f"Unknown category_id: {category_id}")
    return category


def find_category_id(store: InMemoryStore, code: CategoryCode) -> int:
    """Findet eine Kategorie-ID anhand des Enum-Codes."""

    for category_id, category in store.categories.items():
        if category.code == code:
            return category_id
    raise NotFoundError(f"Category {code.value} not found")


def validate_iban(iban: str) -> str:
    """Normalisiert und validiert ein einfaches IBAN-Format."""

    normalized = iban.replace(" ", "").upper()
    if not IBAN_REGEX.match(normalized):
        raise ValidationError("Invalid IBAN format")
    return normalized


def validate_password_policy(password: str) -> None:
    """Erzwingt die Passwortregeln aus den Sicherheitsanforderungen."""

    if len(password) < 8:
        raise ValidationError("Password must contain at least 8 characters")
    if not PASSWORD_SPECIAL_REGEX.search(password):
        raise ValidationError("Password must contain at least one special character")


def hash_password(password: str) -> str:
    """Gibt den SHA-256-Hash des Passwort-Strings zurueck."""

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def mask_card_number(raw_suffix: Optional[int] = None) -> str:
    """Erzeugt eine lesbare, maskierte Kartennummer."""

    suffix = raw_suffix if raw_suffix is not None else 0
    return f"**** **** **** {suffix:04d}"


def month_key(value: date) -> tuple[int, int]:
    """Wandelt ein Datum in einen Gruppierungsschluessel (Jahr, Monat) um."""

    return (value.year, value.month)


def shift_interval(base_date: date, interval: str) -> date:
    """Verschiebt ein Datum um einen Wiederholungsschritt (monatlich/jaehrlich)."""

    if interval == "monthly":
        year = base_date.year + (base_date.month // 12)
        month = (base_date.month % 12) + 1
        day = min(base_date.day, days_in_month(year, month))
        return date(year, month, day)

    year = base_date.year + 1
    day = min(base_date.day, days_in_month(year, base_date.month))
    return date(year, base_date.month, day)


def days_in_month(year: int, month: int) -> int:
    """Gibt die Tageszahl eines Monats inklusive Schaltjahrlogik zurueck."""

    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def is_card_active(status: CardStatus) -> bool:
    """Hilfsfunktion fuer die Pruefung, ob eine Karte aktiv ist."""

    return status == CardStatus.ACTIVE
