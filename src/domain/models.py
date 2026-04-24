from datetime import date
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


# DTO for chart values in dashboard views (not a database table)
class ChartData(SQLModel, table=False):
	label: str
	income: float
	expenses: float


# DTO for dashboard result summary (not a database table)
class DashboardSummary(SQLModel, table=False):
	total_balance: float
	total_income: float
	total_expenses: float
	chart_data: list[ChartData] = Field(default_factory=list)


# Stores banking users for authentication and ownership of data
class User(SQLModel, table=True):
	__tablename__ = "users"

	user_id: Optional[int] = Field(default=None, primary_key=True)
	first_name: str
	last_name: str
	password_hash: str
	contract_number: str

	accounts: list["Account"] = Relationship(back_populates="user")
	credit_cards: list["CreditCard"] = Relationship(back_populates="user")
	budgets: list["Budget"] = Relationship(back_populates="user")

	
	def login(self, password: str) -> bool:
		return bool(password) and self.password_hash == password


# Stores user bank accounts like private or savings accounts
class Account(SQLModel, table=True):
	__tablename__ = "accounts"

	account_id: Optional[int] = Field(default=None, primary_key=True)
	account_type: str
	balance: float = 0.0
	status: str = "aktiv"
	iban: str
	user_id: int = Field(foreign_key="users.user_id")

	user: "User" = Relationship(back_populates="accounts")
	debit_cards: list["DebitCard"] = Relationship(back_populates="account")
	transactions: list["Transaction"] = Relationship(back_populates="account")
	outgoing_transfers: list["Transfer"] = Relationship(
		back_populates="from_account",
		sa_relationship_kwargs={"foreign_keys": "[Transfer.from_account_id]"},
	)
	incoming_transfers: list["Transfer"] = Relationship(
		back_populates="to_account",
		sa_relationship_kwargs={"foreign_keys": "[Transfer.to_account_id]"},
	)
	recurring_transactions: list["RecurringTransaction"] = Relationship(
		back_populates="account"
	)

	def open(self) -> None:
		self.status = "aktiv"

	def close(self) -> None:
		self.status = "geschlossen"


# Stores debit cards that belong to one account
class DebitCard(SQLModel, table=True):
	__tablename__ = "debit_cards"

	card_id: Optional[int] = Field(default=None, primary_key=True)
	card_number: str
	expire_date: date
	status: str = "aktiv"
	account_id: int = Field(foreign_key="accounts.account_id")

	account: "Account" = Relationship(back_populates="debit_cards")
	transactions: list["Transaction"] = Relationship(back_populates="card")

	def block(self) -> None:
		self.status = "gesperrt"

	def replace(self) -> None:
		self.status = "ersetzt"


# Stores independent credit cards linked to a user
class CreditCard(SQLModel, table=True):
	__tablename__ = "credit_cards"

	creditcard_id: Optional[int] = Field(default=None, primary_key=True)
	card_number: str
	expire_date: date
	limit: float
	balance: float = 0.0
	status: str = "aktiv"
	user_id: int = Field(foreign_key="users.user_id")

	user: "User" = Relationship(back_populates="credit_cards")
	transactions: list["Transaction"] = Relationship(back_populates="creditcard")

	def create(self) -> None:
		self.status = "aktiv"

	def block(self) -> None:
		self.status = "gesperrt"

	def replace(self) -> None:
		self.status = "ersetzt"


# Stores fixed categories used for transactions and budgets
class Category(SQLModel, table=True):
	__tablename__ = "categories"

	category_id: Optional[int] = Field(default=None, primary_key=True)
	name: str

	transactions: list["Transaction"] = Relationship(back_populates="category")
	budgets: list["Budget"] = Relationship(back_populates="category")
	recurring_transactions: list["RecurringTransaction"] = Relationship(
		back_populates="category"
	)


# Stores all base transaction fields for income and expense records
class Transaction(SQLModel, table=True):
	__tablename__ = "transactions"

	transaction_id: Optional[int] = Field(default=None, primary_key=True)
	amount: float
	date: date
	type: str
	note: Optional[str] = Field(default=None, nullable=True)
	category_id: int = Field(foreign_key="categories.category_id")
	account_id: Optional[int] = Field(default=None, foreign_key="accounts.account_id")
	card_id: Optional[int] = Field(default=None, foreign_key="debit_cards.card_id")
	creditcard_id: Optional[int] = Field(
		default=None,
		foreign_key="credit_cards.creditcard_id",
	)

	category: "Category" = Relationship(back_populates="transactions")
	account: Optional["Account"] = Relationship(back_populates="transactions")
	card: Optional["DebitCard"] = Relationship(back_populates="transactions")
	creditcard: Optional["CreditCard"] = Relationship(back_populates="transactions")
	transfer: Optional["Transfer"] = Relationship(back_populates="transaction")
	payment: Optional["Payment"] = Relationship(back_populates="transaction")
	recurring_transaction: Optional["RecurringTransaction"] = Relationship(
		back_populates="transaction"
	)

	def create(self) -> None:
		return None

	def edit(self) -> None:
		return None

	def filter(self) -> None:
		return None

	def delete(self) -> None:
		return None


# Stores transfer-specific fields and links back to one base transaction
class Transfer(SQLModel, table=True):
	__tablename__ = "transfers"

	transfer_id: Optional[int] = Field(default=None, primary_key=True)
	from_account_id: int = Field(foreign_key="accounts.account_id")
	to_account_id: int = Field(foreign_key="accounts.account_id")
	status: str
	transaction_id: int = Field(foreign_key="transactions.transaction_id")

	transaction: "Transaction" = Relationship(back_populates="transfer")
	from_account: "Account" = Relationship(
		back_populates="outgoing_transfers",
		sa_relationship_kwargs={"foreign_keys": "[Transfer.from_account_id]"},
	)
	to_account: "Account" = Relationship(
		back_populates="incoming_transfers",
		sa_relationship_kwargs={"foreign_keys": "[Transfer.to_account_id]"},
	)


# Stores domestic payment-specific fields and links back to one base transaction
class Payment(SQLModel, table=True):
	__tablename__ = "payments"

	payment_id: Optional[int] = Field(default=None, primary_key=True)
	target_iban: str
	purpose: str
	status: str
	transaction_id: int = Field(foreign_key="transactions.transaction_id")

	transaction: "Transaction" = Relationship(back_populates="payment")


# Stores monthly/yearly budget settings, optionally per category
class Budget(SQLModel, table=True):
	__tablename__ = "budgets"
	__table_args__ = (
		UniqueConstraint(
			"user_id",
			"month",
			"year",
			"category_id",
			name="uq_budget_user_month_year_category",
		),
	)

	budget_id: Optional[int] = Field(default=None, primary_key=True)
	user_id: int = Field(foreign_key="users.user_id")
	limit_amount: float
	month: int
	year: int
	category_id: Optional[int] = Field(default=None, foreign_key="categories.category_id")

	user: "User" = Relationship(back_populates="budgets")
	category: Optional["Category"] = Relationship(back_populates="budgets")

	def isexceeded(self) -> bool:
		return False


# Stores recurring payment data linked to one base transaction record
class RecurringTransaction(SQLModel, table=True):
	__tablename__ = "recurring_transactions"

	recurring_id: Optional[int] = Field(default=None, primary_key=True)
	amount: float
	target_iban: str
	interval: str
	start_date: date
	end_date: Optional[date] = None
	last_executed: date
	account_id: int = Field(foreign_key="accounts.account_id")
	category_id: int = Field(foreign_key="categories.category_id")
	transaction_id: int = Field(foreign_key="transactions.transaction_id")

	account: "Account" = Relationship(back_populates="recurring_transactions")
	category: "Category" = Relationship(back_populates="recurring_transactions")
	transaction: "Transaction" = Relationship(back_populates="recurring_transaction")


# Table exists as requested by design and can be used for persisted dashboard snapshots
class Dashboard(SQLModel, table=True):
	__tablename__ = "dashboard"

	dashboard_id: Optional[int] = Field(default=None, primary_key=True)

	def dashboard(self) -> DashboardSummary:
		return DashboardSummary(
			total_balance=0.0,
			total_income=0.0,
			total_expenses=0.0,
			chart_data=[],
		)
