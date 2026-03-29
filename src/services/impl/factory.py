from __future__ import annotations

"""Factory zum Verdrahten aller In-Memory-Finanzservices in ein App-Buendel."""

from pathlib import Path

from ..banking_application import BankingApplication
from .account_service_impl import InMemoryAccountService
from .auth_service_impl import InMemoryAuthService
from .budget_service_impl import InMemoryBudgetService
from .credit_card_service_impl import InMemoryCreditCardService
from .dashboard_service_impl import InMemoryDashboardService
from .debit_card_service_impl import InMemoryDebitCardService
from .payment_service_impl import InMemoryPaymentService
from .recurring_payment_service_impl import InMemoryRecurringPaymentService
from .shared import InMemoryStore, bootstrap_default_categories
from .transaction_service_impl import InMemoryTransactionService


class InMemoryServiceBundle:
    """Container mit gemeinsamem Speicher, konkreten Services und zusammengesetzter App."""

    def __init__(self, base_path: Path) -> None:
        """Erzeugt und verdrahtet alle konkreten Service-Implementierungen.

        Alle Services teilen sich dieselbe Store-Instanz. Dadurch sind Daten,
        die ein Service schreibt, sofort fuer die anderen sichtbar.
        """

        self.store = InMemoryStore()
        bootstrap_default_categories(self.store)

        self.transaction_service = InMemoryTransactionService(self.store)
        self.budget_service = InMemoryBudgetService(self.store)
        self.recurring_payment_service = InMemoryRecurringPaymentService(self.store, self.transaction_service)
        self.account_service = InMemoryAccountService(self.store, self.transaction_service)
        self.debit_card_service = InMemoryDebitCardService(self.store)
        self.credit_card_service = InMemoryCreditCardService(self.store)
        self.payment_service = InMemoryPaymentService(self.store, self.transaction_service, base_path)
        self.dashboard_service = InMemoryDashboardService(self.store)
        self.auth_service = InMemoryAuthService(self.store)
        self.auth_service.set_recurring_service(self.recurring_payment_service)

        self.app = BankingApplication(
            auth_service=self.auth_service,
            transaction_service=self.transaction_service,
            dashboard_service=self.dashboard_service,
            budget_service=self.budget_service,
            recurring_payment_service=self.recurring_payment_service,
            account_service=self.account_service,
            debit_card_service=self.debit_card_service,
            credit_card_service=self.credit_card_service,
            payment_service=self.payment_service,
        )


def create_in_memory_application(base_path: Path | None = None) -> InMemoryServiceBundle:
    """Bequemer Konstruktor fuer schnellen Start in Skripten oder Tests."""

    resolved_base = base_path if base_path is not None else Path.cwd()
    return InMemoryServiceBundle(base_path=resolved_base)
