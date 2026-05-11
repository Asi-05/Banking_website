"""src.domain.models

Dieses Modul gehoert zur **Domain-Schicht** der BetterBank-Anwendung.

=== WAS MACHT DIESE DATEI? ===
Sie definiert alle zentralen Datenstrukturen der App in zwei Kategorien:

    1. DATENBANKTABELLEN (table=True):
       Jede Python-Klasse mit `table=True` entspricht genau einer Tabelle in der
       SQLite-Datenbank `betterbank.db`. Eine Instanz der Klasse = eine Zeile in
       der Tabelle.

    2. DTOs (table=False):
       "Data Transfer Objects" = einfache Python-Objekte, die NUR zum Transport
       von Daten zwischen Schichten dienen. Sie werden NICHT in der Datenbank
       gespeichert. Beispiel: `ChartData` und `DashboardSummary` werden vom
       `DashboardService` berechnet und an die View weitergegeben.

=== WAS IST SQLMODEL? ===
SQLModel verbindet zwei Python-Bibliotheken:
    - SQLAlchemy: kommuniziert mit der Datenbank (SQL-Abfragen)
    - Pydantic: validiert Python-Typen (int, str, float, Optional[...])

Das Ergebnis: Man schreibt eine Python-Klasse, und SQLModel erstellt daraus
automatisch eine Datenbanktabelle + Python-Objekte zum Arbeiten.

=== ENTITY-RELATIONSHIP-UEBERSICHT ===
Welche Modelle haengen zusammen? (vereinfacht)

    User (1) ─────────────────────────── Account (n)
                  user_id FK                     │
                                                 ├── DebitCard (n) via account_id FK
                                                 ├── Transaction (n) via account_id FK
                                                 ├── RecurringTransaction (n) via account_id FK
                                                 ├── Transfer "Ausgang" (n) via from_account_id FK
                                                 └── Transfer "Eingang" (n) via to_account_id FK

    User (1) ─────────────────────────── CreditCard (n) via user_id FK
                                                 └── Transaction (n) via creditcard_id FK

    User (1) ─────────────────────────── Budget (n) via user_id FK

    Category (1) ─────────────────────── Transaction (n) via category_id FK
    Category (1) ─────────────────────── Budget (n) via category_id FK
    Category (1) ─────────────────────── RecurringTransaction (n) via category_id FK

    Transaction (1) ──────────────────── Transfer (0..1) via transaction_id FK
    Transaction (1) ──────────────────── Payment (0..1) via transaction_id FK
    Transaction (1) ──────────────────── RecurringTransaction (0..1) via transaction_id FK

    DebitCard (1) ────────────────────── Transaction (n) via card_id FK

=== WARUM `Optional[int]` FUER PRIMARY KEYS? ===
    user_id: Optional[int] = Field(default=None, primary_key=True)

    Beim Erstellen eines Objekts in Python (User(...)) ist die ID noch nicht
    bekannt. Die Datenbank vergibt die ID erst nach `session.commit()`.
    Darum ist sie zu Beginn `None` und wird erst nach `session.refresh(obj)`
    gelesen (so laden wir die neue ID aus der DB nach).

=== WAS SIND `Relationship`-FELDER? ===
Relationship-Felder sind KEINE echten Datenbankspalten. Sie sagen SQLModel:
"Falls ich die verwandten Objekte brauche, wie lade ich sie aus der DB?"

    user.accounts    → Laedt alle Account-Objekte, die `user_id == user.user_id` haben
    account.user     → Laedt den User, zu dem dieses Konto gehoert

    back_populates="..." verbindet das Relationship beidseitig:
    user.accounts[0].user → ist dasselbe user-Objekt (kein doppelter DB-Aufruf).

=== WARUM `sa_relationship_kwargs` BEI MEHRFACH-REFERENZEN? ===
Wenn eine Tabelle ZWEI Foreign Keys auf dieselbe andere Tabelle hat
(Beispiel: Transfer hat `from_account_id` UND `to_account_id`, beide auf `accounts`),
muss man SQLModel sagen, welcher FK fuer welches Relationship gilt:

    outgoing_transfers: Relationship(..., foreign_keys="[Transfer.from_account_id]")
    incoming_transfers: Relationship(..., foreign_keys="[Transfer.to_account_id]")

Ohne diese Angabe wuesste SQLModel nicht, welchen FK es nehmen soll.

=== TRANSACTION-QUELLE: EXACTLY-ONE-REGEL ===
Eine Transaktion kann von drei verschiedenen Quellen stammen:
    - account_id     → direkte Kontozahlung
    - card_id        → Debitkartenzahlung
    - creditcard_id  → Kreditkartenzahlung

Die Regel "Genau eine Quelle" wird in `src/utils/validators.py` geprueft
(`validate_exactly_one_source`). Im Model sind alle drei Optional, weil nur
eine davon gesetzt wird.

=== ARCHITEKTUR-KETTE ===
    domain/models.py ← wird importiert von:
    → Repositories (data_access/repositories/*.py): lesen/schreiben Tabellen
    → Services (services/*.py): arbeiten mit Objekten
    → Views (ui/views/*.py): zeigen Daten an (lesen nur, schreiben nie direkt)
    → seed.py: legt Demo-Daten an
    → db.py: SQLModel.metadata.create_all() liest alle Klassen aus diesem Modul
"""

from datetime import date
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


# DTO fuer Diagrammwerte im Dashboard (keine Datenbanktabelle)
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


# DTO fuer die Dashboard-Zusammenfassung (keine Datenbanktabelle)
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


# Speichert Bank-User fuer Login und Besitz (Ownership) von Daten
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


# Speichert Bankkonten (z.B. Privatkonto oder Sparkonto)
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


# Speichert Debitkarten, die zu genau einem Konto gehoeren
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


# Speichert Kreditkarten, die einem User zugeordnet sind
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


# Speichert Kategorien fuer Transaktionen und Budgets
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


# Speichert die Basisdaten einer Transaktion (Einnahme/Ausgabe)
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



# Speichert Umbuchungs-spezifische Felder und verweist auf eine Basis-Transaktion
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


# Speichert Zahlungs-spezifische Felder und verweist auf eine Basis-Transaktion
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


# Speichert Monatsbudgets (optional pro Kategorie)
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



# Speichert Dauerauftraege (wiederkehrende Zahlungen) und verknuepft sie mit einer Basis-Transaktion
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


# Hinweis: Persistierte Dashboard-Snapshots wurden bewusst entfernt (nicht noetig).
# Wenn du das spaeter wieder einfuehren willst, kannst du hier ein Dashboard-Model
# ergaenzen, z.B. mit Feldern wie snapshot_date, total_balance, total_income, total_expenses.
