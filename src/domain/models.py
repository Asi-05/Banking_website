"""Domänenmodelle (Domain-Schicht) der BetterBank-Anwendung.

Dieses Modul definiert die zentralen Datenstrukturen der App: einerseits echte
SQLModel-Tabellen (jede Instanz entspricht einer Datenbankzeile) und andererseits
DTOs ("Data Transfer Objects" = einfache Transport-Objekte) für das Dashboard.
Die Models werden von Repositories (DB-Zugriff) und Services (Fachlogik) genutzt
und sind die gemeinsame "Sprache" zwischen allen Schichten.
"""

from datetime import date
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


# DTO for chart values in dashboard views (not a database table)
class ChartData(SQLModel, table=False):
	"""DTO für einen einzelnen Datenpunkt im Dashboard-Chart.

	Das ist **keine** Datenbanktabelle (table=False), sondern ein reines Python-
	Objekt, das der `dashboard_service` berechnet und an die UI weitergibt.

	Attributes:
		label: X-Achsen-Label, z. B. "2026-04".
		income: Summe der Einnahmen im Zeitraum/Monat.
		expenses: Summe der Ausgaben im Zeitraum/Monat.
	"""
	label: str
	income: float
	expenses: float


# DTO for dashboard result summary (not a database table)
class DashboardSummary(SQLModel, table=False):
	"""DTO für die komplette Dashboard-Zusammenfassung.

	Auch dieses Objekt wird nicht persistiert, sondern beim Laden des Dashboards
	immer neu berechnet. Es bündelt die wichtigsten Kennzahlen, damit die UI nicht
	mehrere einzelne Service-Calls machen muss.

	Attributes:
		total_balance: Gesamtsaldo über alle Konten.
		total_income: Gesamteinnahmen im gewählten Zeitraum.
		total_expenses: Gesamtausgaben im gewählten Zeitraum.
		chart_data: Zeitreihe für Diagramme.
	"""
	total_balance: float
	total_income: float
	total_expenses: float
	chart_data: list[ChartData] = Field(default_factory=list)


# Stores banking users for authentication and ownership of data
class User(SQLModel, table=True):
	"""Benutzerkonto der BetterBank (Datenbanktabelle `users`).

	Jede Instanz entspricht einer Zeile in der Datenbank. Ein User besitzt mehrere
	Konten, Kreditkarten und Budgets. Authentifizierung basiert auf einer
	Vertragsnummer (`contract_number`) und einem gespeicherten Passwort-Hash.

	Wichtig: Das echte Passwort wird nie gespeichert. Stattdessen wird ein Hash
	abgelegt (siehe `src/utils/validators.py` und `auth_service`).
	"""
	__tablename__ = "users"

	user_id: Optional[int] = Field(default=None, primary_key=True)
	first_name: str
	last_name: str
	password_hash: str
	contract_number: str
	phone: Optional[str] = Field(default=None)
	address: Optional[str] = Field(default=None)

	accounts: list["Account"] = Relationship(back_populates="user")
	credit_cards: list["CreditCard"] = Relationship(back_populates="user")
	budgets: list["Budget"] = Relationship(back_populates="user")

	
	def login(self, password: str) -> bool:
		"""(Legacy/Platzhalter) Prüft Login-Daten direkt am Model.

	In einer sauberen Architektur liegt Authentifizierung in der Service-Schicht.
	Diese Methode ist hier als sehr einfacher Platzhalter vorhanden.

	Args:
		password: Passwort-Eingabe.

	Returns:
		True/False je nachdem, ob die Prüfung erfolgreich ist.
	"""
		return bool(password) and self.password_hash == password


# Stores user bank accounts like private or savings accounts
class Account(SQLModel, table=True):
	"""Bankkonto eines Users (Datenbanktabelle `accounts`).

	Ein Account repräsentiert ein echtes Konto (z. B. Privatkonto oder Sparkonto)
	mit IBAN, Saldo (`balance`) und Status. Über Relationships hängen daran
	Transaktionen, Debitkarten, Daueraufträge und Umbuchungen.
	"""
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
	billed_credit_cards: list["CreditCard"] = Relationship(
		back_populates="billing_account",
		sa_relationship_kwargs={"foreign_keys": "[CreditCard.billing_account_id]"},
	)

	def open(self) -> None:
		"""Setzt den Kontostatus auf "aktiv"."""
		self.status = "aktiv"

	def close(self) -> None:
		"""Setzt den Kontostatus auf "geschlossen"."""
		self.status = "geschlossen"


# Stores debit cards that belong to one account
class DebitCard(SQLModel, table=True):
	"""Debitkarte eines Kontos (Datenbanktabelle `debit_cards`).

	Eine Debitkarte ist immer genau einem Konto zugeordnet. Zahlungen über eine
	Debitkarte belasten indirekt den Kontostand (über die Transaktionslogik).
	"""
	__tablename__ = "debit_cards"

	card_id: Optional[int] = Field(default=None, primary_key=True)
	card_number: str
	expire_date: date
	status: str = "aktiv"
	account_id: int = Field(foreign_key="accounts.account_id")

	account: "Account" = Relationship(back_populates="debit_cards")
	transactions: list["Transaction"] = Relationship(back_populates="card")

	def block(self) -> None:
		"""Markiert die Karte als gesperrt (z. B. bei Verlust)."""
		self.status = "gesperrt"

	def replace(self) -> None:
		"""Markiert die Karte als ersetzt (alte Karte ist nicht mehr aktiv)."""
		self.status = "ersetzt"


# Stores independent credit cards linked to a user
class CreditCard(SQLModel, table=True):
	"""Unabhängige Kreditkarte eines Users (Datenbanktabelle `credit_cards`).

	Wichtig für Anfänger: Eine Kreditkarte hat hier **zwei** wichtige Geldwerte:
	- `limit`: der Kreditrahmen (wie viel maximal "auf Kredit" möglich ist)
	- `balance`: der aktuell genutzte Kredit (wie viel schon ausgegeben wurde)

	Dieser `balance` ist **nicht** der Kontostand eines Kontos. Bei der monatlichen
	Abrechnung wird dieser Betrag vom `billing_account` abgebucht und danach wieder
	auf 0 gesetzt (siehe `creditcard_billing_service`).
	"""
	__tablename__ = "credit_cards"

	creditcard_id: Optional[int] = Field(default=None, primary_key=True)
	card_number: str
	expire_date: date
	limit: float
	balance: float = 0.0
	status: str = "aktiv"
	# Konto von dem der monatliche Kreditkartenbetrag abgebucht wird (Lohnkonto)
	billing_account_id: Optional[int] = Field(
		default=None, foreign_key="accounts.account_id"
	)
	# Datum der letzten Monatsabrechnung
	last_billed: Optional[date] = Field(default=None)
	user_id: int = Field(foreign_key="users.user_id")

	user: "User" = Relationship(back_populates="credit_cards")
	billing_account: Optional["Account"] = Relationship(
		sa_relationship_kwargs={"foreign_keys": "[CreditCard.billing_account_id]"}
	)
	transactions: list["Transaction"] = Relationship(back_populates="creditcard")

	def create(self) -> None:
		"""Setzt den Status auf "aktiv" (z. B. nach Bestellung)."""
		self.status = "aktiv"

	def block(self) -> None:
		"""Markiert die Karte als gesperrt."""
		self.status = "gesperrt"

	def replace(self) -> None:
		"""Markiert die Karte als ersetzt."""
		self.status = "ersetzt"


# Stores fixed categories used for transactions and budgets
class Category(SQLModel, table=True):
	"""Kategorie für Ausgaben/Einnahmen (Datenbanktabelle `categories`).

	Kategorien werden in Transaktionen gespeichert (damit man filtern/analysieren
	kann) und optional auch in Budgets (damit Budgets pro Kategorie möglich sind).
	"""
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
	"""Transaktion (Einnahme oder Ausgabe) als Basistabelle `transactions`.

	Diese Tabelle enthält die gemeinsamen Felder für alle Geldbewegungen:
	Betrag, Datum, Typ (income/expense), Kategorie und genau **eine** Quelle
	(Konto, Debitkarte oder Kreditkarte).

	Zusätzliche Details hängen je nach Art über 1:1-Beziehungen dran:
	- `Transfer` (Umbuchung zwischen eigenen Konten)
	- `Payment` (Inlandszahlung mit Ziel-IBAN)
	- `RecurringTransaction` (Dauerauftrag)
	"""
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
		"""(Platzhalter) Erstellung passiert in der Service-/Repository-Schicht."""
		return None

	def edit(self) -> None:
		"""(Platzhalter) Bearbeitung passiert in der Service-/Repository-Schicht."""
		return None

	def filter(self) -> None:
		"""(Platzhalter) Filtern passiert über Repository-Queries."""
		return None

	def delete(self) -> None:
		"""(Platzhalter) Löschen passiert in der Service-/Repository-Schicht."""
		return None


# Stores transfer-specific fields and links back to one base transaction
class Transfer(SQLModel, table=True):
	"""Umbuchung zwischen zwei eigenen Konten (Tabelle `transfers`).

	Eine Umbuchung ist fachlich eine spezielle Transaktion: sie belastet ein Konto
	und erhöht gleichzeitig ein anderes Konto. Darum referenziert `Transfer` immer
	genau eine Zeile in `transactions` über `transaction_id`.
	"""
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
	"""Inlandszahlung mit Empfänger-IBAN (Tabelle `payments`).

	Auch eine Zahlung ist eine spezielle Transaktion: die Basisdaten (Betrag, Datum,
	Typ, Kategorie, Quelle) liegen in `transactions`, und zahlungsspezifische Daten
	(Ziel-IBAN, Verwendungszweck, Status) liegen hier.
	"""
	__tablename__ = "payments"

	payment_id: Optional[int] = Field(default=None, primary_key=True)
	target_iban: str
	purpose: str
	status: str
	transaction_id: int = Field(foreign_key="transactions.transaction_id")

	transaction: "Transaction" = Relationship(back_populates="payment")


# Stores monthly/yearly budget settings, optionally per category
class Budget(SQLModel, table=True):
	"""Monatsbudget eines Users (Tabelle `budgets`).

	Ein Budget kann optional an eine Kategorie gebunden sein. Der UniqueConstraint
	sorgt dafür, dass ein User nicht aus Versehen zwei Budgets für denselben
	Monat/Jahr und dieselbe Kategorie anlegt (doppelte Regeln wären widersprüchlich).
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
		"""(Platzhalter) Ob ein Budget überschritten ist, wird in Services berechnet."""
		return False


# Stores recurring payment data linked to one base transaction record
class RecurringTransaction(SQLModel, table=True):
	"""Dauerauftrag (Tabelle `recurring_transactions`).

	Ein Dauerauftrag beschreibt eine wiederkehrende Zahlung mit Intervall.
	Technisch ist er ebenfalls an eine Basis-Transaktion gekoppelt (`transaction_id`),
	damit die Ausführung als normale Transaktion in der Historie sichtbar ist.
	Die Service-Schicht berechnet beim Login, ob etwas fällig ist und erstellt dann
	entsprechende Transaktionen (siehe `auth_service`/`recurring_service`).
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


# NOTE: Persisted dashboard snapshots were removed by decision (not needed).
# If you want to re-enable persisted snapshots later, add a Dashboard model
# here with fields like snapshot_date, total_balance, total_income, total_expenses.
