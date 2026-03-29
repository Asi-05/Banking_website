from __future__ import annotations

from .account_service import AccountService
from .auth_service import AuthService
from .budget_service import BudgetService
from .credit_card_service import CreditCardService
from .dashboard_service import DashboardService
from .debit_card_service import DebitCardService
from .payment_service import PaymentService
from .recurring_payment_service import RecurringPaymentService
from .transaction_service import TransactionService


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
