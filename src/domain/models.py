

"""SQLModel-Datenmodelle der Betterbank-Anwendung.

Dieses Modul definiert alle persistenten Tabellen sowie DTO-Modelle,
die vom Service- und UI-Layer für aggregierte Dashboard-Daten verwendet werden.
"""

from datetime import date
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

class ChartData(SQLModel, table=False):
	"""Transportmodell fuer Balken-/Linienwerte im Dashboard.

	Attributes:
		label: Beschriftung der dargestellten Periode oder Kategorie.
		income: Summierte Einnahmen im betrachteten Segment.
		expenses: Summierte Ausgaben im betrachteten Segment.
	"""

	label: str
	income: float
	expenses: float


class DashboardSummary(SQLModel, table=False):
	"""DTO fuer aggregierte Kennzahlen des Dashboards.

	Attributes:
		total_balance: Gesamtbilanz ueber alle relevanten Konten/Karten.
		total_income: Gesamteinnahmen im abgefragten Zeitraum.
		total_expenses: Gesamtausgaben im abgefragten Zeitraum.
		chart_data: Liste vorbereiteter Diagrammwerte.
	"""

	total_balance: float
	total_income: float
	total_expenses: float
	chart_data: list[ChartData] = Field(default_factory=list)


class User(SQLModel, table=True):
	"""Persistentes Benutzerkonto der Betterbank.

	Der Benutzer ist Eigentuemer von Konten, Kreditkarten und Budgets und
	wird fuer den Login ueber die Vertragsnummer identifiziert.
	"""

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
		"""Prueft vereinfacht, ob ein Passwort zum gespeicherten Hash passt.

		Args:
			password: Eingegebenes Passwort im Login-Prozess.

		Returns:
			True, wenn ein nicht-leeres Passwort dem gespeicherten Wert entspricht.
		"""

		return bool(password) and self.password_hash == password


class Account(SQLModel, table=True):
	"""Bankkonto eines Benutzers (z. B. Privat- oder Sparkonto)."""

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
		"""Setzt den Kontostatus auf aktiv."""

		self.status = "aktiv"

	def close(self) -> None:
		"""Setzt den Kontostatus auf geschlossen."""

		self.status = "geschlossen"


class DebitCard(SQLModel, table=True):
	"""Debitkarte, die einem Konto zugeordnet ist."""

	__tablename__ = "debit_cards"

	card_id: Optional[int] = Field(default=None, primary_key=True)
	card_number: str
	expire_date: date
	status: str = "aktiv"
	account_id: int = Field(foreign_key="accounts.account_id")

	account: "Account" = Relationship(back_populates="debit_cards")
	transactions: list["Transaction"] = Relationship(back_populates="card")

	def block(self) -> None:
		"""Markiert die Karte als gesperrt."""

		self.status = "gesperrt"

	def replace(self) -> None:
		"""Markiert die Karte als ersetzt."""

		self.status = "ersetzt"


class CreditCard(SQLModel, table=True):
	"""Unabhaengige Kreditkarte, die direkt am Benutzer haengt."""

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
		"""Setzt den Kartenstatus auf aktiv nach Erstellung."""

		self.status = "aktiv"

	def block(self) -> None:
		"""Markiert die Kreditkarte als gesperrt."""

		self.status = "gesperrt"

	def replace(self) -> None:
		"""Markiert die Kreditkarte als ersetzt."""

		self.status = "ersetzt"


class Category(SQLModel, table=True):
	"""Stammdatenkategorie fuer Transaktionen und Budgets."""

	__tablename__ = "categories"

	category_id: Optional[int] = Field(default=None, primary_key=True)
	name: str

	transactions: list["Transaction"] = Relationship(back_populates="category")
	budgets: list["Budget"] = Relationship(back_populates="category")
	recurring_transactions: list["RecurringTransaction"] = Relationship(
		back_populates="category"
	)

class Transaction(SQLModel, table=True):
	"""Basistabelle fuer alle Buchungen (income/expense)."""

	__tablename__ = "transactions"

	transaction_id: Optional[int] = Field(default=None, primary_key=True)
	amount: float
	date: date
	type: str
	note: str
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
		"""Platzhalter fuer Erstellungslogik auf Service-Ebene."""

		return None

	def edit(self) -> None:
		"""Platzhalter fuer Aenderungslogik auf Service-Ebene."""

		return None

	def filter(self) -> None:
		"""Platzhalter fuer Filterlogik auf Service-/Repository-Ebene."""

		return None

	def delete(self) -> None:
		"""Platzhalter fuer Loeschlogik auf Service-Ebene."""

		return None


class Transfer(SQLModel, table=True):
	"""Spezialisierung fuer Umbuchungen zwischen eigenen Konten.

	Die Beziehung zur Basistabelle erfolgt ueber ``transaction_id``.
	"""

	__tablename__ = "transfers"

	transfer_id: Optional[int] = Field(default=None, primary_key=True)
	from_account_id: int = Field(foreign_key="accounts.account_id")
	to_account_id: int = Field(foreign_key="accounts.account_id")
	status: str
	transaction_id: int = Field(foreign_key="transactions.transaction_id")

	transaction: "Transaction" = Relationship(back_populates="transfer")
	# Zwei FKs zeigen auf dieselbe Tabelle, daher wird die FK-Spalte explizit angegeben.
	from_account: "Account" = Relationship(
		back_populates="outgoing_transfers",
		sa_relationship_kwargs={"foreign_keys": "[Transfer.from_account_id]"},
	)
	# Zwei FKs zeigen auf dieselbe Tabelle, daher wird die FK-Spalte explizit angegeben.
	to_account: "Account" = Relationship(
		back_populates="incoming_transfers",
		sa_relationship_kwargs={"foreign_keys": "[Transfer.to_account_id]"},
	)


class Payment(SQLModel, table=True):
	"""Spezialisierung fuer Inlandszahlungen mit Empfaenger-IBAN."""

	__tablename__ = "payments"

	payment_id: Optional[int] = Field(default=None, primary_key=True)
	target_iban: str
	purpose: str
	status: str
	transaction_id: int = Field(foreign_key="transactions.transaction_id")

	transaction: "Transaction" = Relationship(back_populates="payment")

class Budget(SQLModel, table=True):
	"""Monats-/Jahresbudget eines Benutzers, optional je Kategorie.

	Hinweis:
		Die fachliche Eindeutigkeit wird ueber den Unique-Constraint auf
		``(user_id, month, year, category_id)`` sichergestellt.
	"""

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
		"""Platzhalter fuer Budgetpruefung gegen reale Ist-Ausgaben."""

		return False


class RecurringTransaction(SQLModel, table=True):
	"""Wiederkehrende Zahlung mit Intervall und Ausfuehrungsstand.

	Die Entitaet ist eine eigene Tabelle und referenziert die
	Transaktions-Basistabelle ueber ``transaction_id``.
	"""

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

class Dashboard(SQLModel, table=True):
	"""Persistente Huelle fuer Dashboard-bezogene Datenpunkte.

	Aktuell wird ein reines Summary-DTO zurueckgegeben; die eigentliche
	Aggregation ist in der Service-Schicht vorgesehen.
	"""

	__tablename__ = "dashboard"

	dashboard_id: Optional[int] = Field(default=None, primary_key=True)

	def dashboard(self) -> DashboardSummary:
		"""Erzeugt ein leeres DashboardSummary-Objekt als Ausgangswert.

		Returns:
			DashboardSummary: Nullsummen und leere Chart-Liste.
		"""

		return DashboardSummary(
			total_balance=0.0,
			total_income=0.0,
			total_expenses=0.0,
			chart_data=[],
		)
