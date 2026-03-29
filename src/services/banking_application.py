from __future__ import annotations

from .interface.account_service import AccountService
from .interface.auth_service import AuthService
from .interface.budget_service import BudgetService
from .interface.credit_card_service import CreditCardService
from .interface.dashboard_service import DashboardService
from .interface.debit_card_service import DebitCardService
from .interface.payment_service import PaymentService
from .interface.recurring_payment_service import RecurringPaymentService
from .interface.transaction_service import TransactionService


class BankingApplication:
    """Composition root for wiring concrete service implementations later."""

    def __init__(
        self,
        auth_service: AuthService,
        transaction_service: TransactionService,
        dashboard_service: DashboardService,
        budget_service: BudgetService,
        recurring_payment_service: RecurringPaymentService,
        account_service: AccountService,
        debit_card_service: DebitCardService,
        credit_card_service: CreditCardService,
        payment_service: PaymentService,
    ) -> None:
        self.auth_service = auth_service
        self.transaction_service = transaction_service
        self.dashboard_service = dashboard_service
        self.budget_service = budget_service
        self.recurring_payment_service = recurring_payment_service
        self.account_service = account_service
        self.debit_card_service = debit_card_service
        self.credit_card_service = credit_card_service
        self.payment_service = payment_service
