# Erlaubt moderne Typ-Hinweise (z. B. Klassenname als Text),
# auch wenn die Klasse im Code erst weiter unten definiert wird.
from __future__ import annotations

# Datentypen fuer Datum und Zeitstempel.
from datetime import date, datetime

# SQLAlchemy-Bausteine fuer Tabellen, Spalten, Regeln und Standardwerte.
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
# ORM-Hilfen fuer Klassen als Tabellen und Beziehungen zwischen Klassen.
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Base ist die gemeinsame Elternklasse fuer alle ORM-Modelle.
# Jede Klasse, die von Base erbt, wird spaeter eine Datenbanktabelle.
class Base(DeclarativeBase):
    pass


# Tabelle fuer Benutzerkonten.
class User(Base):
    # Name der Tabelle in der Datenbank.
    __tablename__ = "users"

    # Eindeutige interne ID (Primärschluessel).
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Vertragsnummer fuer Login, muss eindeutig sein.
    contract_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    # Passwort nur als Hash speichern, nie als Klartext.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Anzeigename des Benutzers.
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # E-Mail des Benutzers, ebenfalls eindeutig.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Gibt an, ob der Account aktiv ist.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Zaehlt fehlgeschlagene Login-Versuche.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Optionaler Zeitstempel bis wann ein Benutzer gesperrt ist.
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Zeitpunkt der Erstellung, automatisch von der DB gesetzt.
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Beziehungen zu anderen Tabellen.
    # Ein User kann mehrere Konten, Kreditkarten, Budgets usw. besitzen.
    accounts: Mapped[list[Account]] = relationship(back_populates="user")
    credit_cards: Mapped[list[CreditCard]] = relationship(back_populates="user")
    budget_limits: Mapped[list[BudgetLimit]] = relationship(back_populates="user")
    recurring_transactions: Mapped[list[RecurringTransaction]] = relationship(back_populates="user")
    session_tokens: Mapped[list[SessionToken]] = relationship(back_populates="user")


# Tabelle fuer Bankkonten.
class Account(Base):
    __tablename__ = "accounts"
    # __table_args__ enthaelt Zusatzregeln fuer die ganze Tabelle.
    __table_args__ = (
        # Kontotyp darf nur private oder savings sein.
        CheckConstraint("account_type IN ('private', 'savings')", name="ck_accounts_account_type"),
        # Status darf nur active oder closed sein.
        CheckConstraint("status IN ('active', 'closed')", name="ck_accounts_status"),
    )

    # Interne Konto-ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Verknuepfung zum Besitzer (User).
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    # IBAN muss eindeutig sein.
    iban: Mapped[str] = mapped_column(String(34), unique=True, nullable=False, index=True)
    # Kontoart: private oder savings.
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Konto-Status.
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    # Aktueller Kontostand.
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Zeitstempel fuer Kontoeroeffnung.
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    # Wird gesetzt, wenn Konto geschlossen wird.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Rueckbeziehungen fuer bequemes Navigieren im Python-Code.
    user: Mapped[User] = relationship(back_populates="accounts")
    debit_cards: Mapped[list[DebitCard]] = relationship(back_populates="account")
    account_transactions: Mapped[list[Transaction]] = relationship(back_populates="account", foreign_keys="Transaction.account_id")
    payments: Mapped[list[Payment]] = relationship(back_populates="source_account")
    statements: Mapped[list[Statement]] = relationship(back_populates="account")
    outgoing_transfers: Mapped[list[Transfer]] = relationship(
        back_populates="from_account",
        foreign_keys="Transfer.from_account_id",
    )
    incoming_transfers: Mapped[list[Transfer]] = relationship(
        back_populates="to_account",
        foreign_keys="Transfer.to_account_id",
    )
    recurring_transactions: Mapped[list[RecurringTransaction]] = relationship(back_populates="account")


# Basistabelle fuer Karten.
# Diese Klasse ist abstrakt im fachlichen Sinn: konkrete Typen sind DebitCard und CreditCard.
class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (CheckConstraint("status IN ('active', 'blocked', 'replaced')", name="ck_cards_status"),)

    # Gemeinsame Karten-ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Maskierte Kartennummer (z. B. **** **** **** 1234).
    card_number_masked: Mapped[str] = mapped_column(String(32), nullable=False)
    # Kartenstatus.
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    # Ausgabedatum der Karte.
    issued_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    # Sperrdatum, falls Karte gesperrt wurde.
    blocked_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Technischer Typ fuer Vererbung in SQLAlchemy.
    card_type: Mapped[str] = mapped_column(String(16), nullable=False)

    # Hier wird die Vererbung konfiguriert.
    # SQLAlchemy erkennt anhand card_type, welcher Untertyp gemeint ist.
    __mapper_args__ = {
        "polymorphic_on": card_type,
        "polymorphic_identity": "card",
    }


# Debitkarte: gehoert genau zu einem Konto.
class DebitCard(Card):
    __tablename__ = "debit_cards"

    # Gleiche ID wie in cards (joined-table inheritance).
    id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    # Konto, an das die Debitkarte gebunden ist.
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Beziehungen.
    account: Mapped[Account] = relationship(back_populates="debit_cards")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="debit_card")

    # Kennzeichnung dieses Untertyps.
    __mapper_args__ = {
        "polymorphic_identity": "debit",
    }


# Unabhaengige Kreditkarte mit eigenem Limit.
class CreditCard(Card):
    __tablename__ = "credit_cards"
    __table_args__ = (
        # Kreditlimit darf nie negativ sein.
        CheckConstraint("credit_limit >= 0", name="ck_credit_cards_credit_limit_non_negative"),
        # Bereits genutzter Betrag darf nie negativ sein.
        CheckConstraint("used_balance >= 0", name="ck_credit_cards_used_balance_non_negative"),
    )

    # Gleiche ID wie in cards.
    id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    # Besitzer der Kreditkarte.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Maximal verfuegbarer Kreditrahmen.
    credit_limit: Mapped[float] = mapped_column(Float, nullable=False)
    # Bereits genutzter Teil des Kreditrahmens.
    used_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Beziehungen.
    user: Mapped[User] = relationship(back_populates="credit_cards")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="credit_card")

    # Kennzeichnung dieses Untertyps.
    __mapper_args__ = {
        "polymorphic_identity": "credit",
    }


# Kategorien fuer Transaktionen (z. B. Miete, Freizeit).
class Category(Base):
    __tablename__ = "categories"

    # Kategorie-ID (vorgegebene IDs 1..10 werden geseedet).
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Name der Kategorie, eindeutig.
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Beziehungen zu fachlichen Objekten.
    transactions: Mapped[list[Transaction]] = relationship(back_populates="category")
    budget_limits: Mapped[list[BudgetLimit]] = relationship(back_populates="category")
    recurring_transactions: Mapped[list[RecurringTransaction]] = relationship(back_populates="category")


# Einzelne Buchung: Einnahme oder Ausgabe.
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Nur income oder expense erlaubt.
        CheckConstraint("type IN ('income', 'expense')", name="ck_transactions_type"),
        # Betrag muss positiv sein.
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        # Kernregel aus den Anforderungen:
        # Genau eine Quelle muss gesetzt sein (Konto ODER Debitkarte ODER Kreditkarte).
        CheckConstraint(
            "((account_id IS NOT NULL) + (debit_card_id IS NOT NULL) + (credit_card_id IS NOT NULL)) = 1",
            name="ck_transactions_exactly_one_source",
        ),
    )

    # Primärschluessel und Fachfelder.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True, index=True)
    debit_card_id: Mapped[int | None] = mapped_column(ForeignKey("debit_cards.id", ondelete="RESTRICT"), nullable=True, index=True)
    credit_card_id: Mapped[int | None] = mapped_column(ForeignKey("credit_cards.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Beziehungen zur Kategorie und zur jeweils gesetzten Zahlungsquelle.
    category: Mapped[Category] = relationship(back_populates="transactions")
    account: Mapped[Account | None] = relationship(back_populates="account_transactions", foreign_keys=[account_id])
    debit_card: Mapped[DebitCard | None] = relationship(back_populates="transactions")
    credit_card: Mapped[CreditCard | None] = relationship(back_populates="transactions")


# Monatliches Budgetlimit, optional je Kategorie.
class BudgetLimit(Base):
    __tablename__ = "budget_limits"
    __table_args__ = (
        # Monat muss 1..12 sein.
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_budget_limits_month"),
        # Einfacher Schutz gegen unplausible Jahreswerte.
        CheckConstraint("year >= 2000", name="ck_budget_limits_year"),
        # Limit darf nicht negativ sein.
        CheckConstraint("limit_amount >= 0", name="ck_budget_limits_limit_non_negative"),
        # Pro User + Kategorie + Monat + Jahr darf es nur ein Budget geben.
        UniqueConstraint("user_id", "category_id", "month", "year", name="uq_budget_limit_scope"),
    )

    # Kernfelder.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    limit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Beziehungen.
    user: Mapped[User] = relationship(back_populates="budget_limits")
    category: Mapped[Category | None] = relationship(back_populates="budget_limits")
    alerts: Mapped[list[BudgetAlert]] = relationship(back_populates="budget_limit")


# Ein gespeicherter Warnhinweis zu einem Budget.
class BudgetAlert(Base):
    __tablename__ = "budget_alerts"

    # Felder des Warnereignisses.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    budget_limit_id: Mapped[int] = mapped_column(ForeignKey("budget_limits.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    spent_amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_exceeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)

    # Rueckbeziehung zum betroffenen Budget.
    budget_limit: Mapped[BudgetLimit] = relationship(back_populates="alerts")


# Wiederkehrende Buchung (z. B. monatliche Miete).
class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        # Betrag muss positiv sein.
        CheckConstraint("amount > 0", name="ck_recurring_transactions_amount_positive"),
        # Nur die zwei erlaubten Intervalle.
        CheckConstraint("interval IN ('monthly', 'yearly')", name="ck_recurring_transactions_interval"),
        # Guelte Statuswerte.
        CheckConstraint("status IN ('active', 'paused', 'stopped')", name="ck_recurring_transactions_status"),
    )

    # Fachfelder.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    # Beziehungen.
    user: Mapped[User] = relationship(back_populates="recurring_transactions")
    category: Mapped[Category] = relationship(back_populates="recurring_transactions")
    account: Mapped[Account] = relationship(back_populates="recurring_transactions")


# Externe Inlandszahlung (z. B. an fremde IBAN).
class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        # Betrag muss positiv sein.
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        # Definierte Statuswerte fuer den Zahlungsprozess.
        CheckConstraint("status IN ('pending', 'success', 'failed')", name="ck_payments_status"),
    )

    # Felder der Zahlung.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_iban: Mapped[str] = mapped_column(String(34), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    purpose: Mapped[str] = mapped_column(String(140), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Konto, von dem die Zahlung abgeht.
    source_account: Mapped[Account] = relationship(back_populates="payments")


# Umbuchung zwischen zwei eigenen Konten.
class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        # Betrag muss positiv sein.
        CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
        # Quelle und Ziel duerfen nicht gleich sein.
        CheckConstraint("from_account_id <> to_account_id", name="ck_transfers_distinct_accounts"),
        # Eindeutige technische Referenz der Umbuchung.
        UniqueConstraint("booking_reference", name="uq_transfers_booking_reference"),
    )

    # Felder der Umbuchung.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    to_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    booking_reference: Mapped[str] = mapped_column(String(64), nullable=False)

    # Beziehungen zu Quell- und Zielkonto.
    from_account: Mapped[Account] = relationship(back_populates="outgoing_transfers", foreign_keys=[from_account_id])
    to_account: Mapped[Account] = relationship(back_populates="incoming_transfers", foreign_keys=[to_account_id])


# Metadaten fuer erzeugte Kontoauszuege.
class Statement(Base):
    __tablename__ = "statements"
    __table_args__ = (
        # Zeitraum muss gueltig sein: Ende nicht vor Start.
        CheckConstraint("end_date >= start_date", name="ck_statements_date_range"),
        # Pro Konto und Zeitraum nur ein Auszug.
        UniqueConstraint("account_id", "start_date", "end_date", name="uq_statement_scope"),
    )

    # Felder des Auszugs.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Zugehoeriges Konto.
    account: Mapped[Account] = relationship(back_populates="statements")


# Session-Token fuer angemeldete Benutzer.
class SessionToken(Base):
    __tablename__ = "session_tokens"

    # Felder fuer Token-Verwaltung.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    auth_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Zu welchem Benutzer gehoert der Token.
    user: Mapped[User] = relationship(back_populates="session_tokens")
