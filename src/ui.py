from __future__ import annotations

from .services import BankingApplication


class LoginPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render login form and call auth service on submit."""


class DashboardPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render KPIs and charts from DashboardService."""


class TransactionsPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render transaction CRUD and filtering interface."""


class BudgetPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render budget setup and budget warning overview."""


class AccountPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render account opening, closing and account overview."""


class CardPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render debit/credit card order, block and replacement flows."""


class PaymentPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render domestic payments and own-account transfers."""


class StatementPage:
    def __init__(self, app: BankingApplication) -> None:
        self.app = app

    def render(self) -> None:
        """Render account statement generation and viewing."""
