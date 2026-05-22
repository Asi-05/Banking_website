"""src.data_access.repositories.transaction_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS IST DIE TRANSACTION-TABELLE? ===
Die `transactions`-Tabelle ist die ZENTRALE Tabelle der App. Jede Geldbewegung
(Einnahme, Ausgabe, egal ob per Konto, Debitkarte oder Kreditkarte) landet hier.

Jede Transaktion hat GENAU EINE Belastungsquelle (Exactly-One-Regel):
    - account_id     → Direkte Kontozahlung
    - card_id        → Zahlung via Debitkarte
    - creditcard_id  → Zahlung via Kreditkarte

=== WARUM SIND JOINS SO KOMPLEX? ===
Um alle Transaktionen EINES USERS zu finden, muss man alle drei Quelltypen pruefen:

    account_id:     Transaction.account_id → Account.user_id
    card_id:        Transaction.card_id → DebitCard.account_id → Account.user_id
    creditcard_id:  Transaction.creditcard_id → CreditCard.user_id

    SQL dafuer:
    SELECT t.* FROM transactions t
    LEFT JOIN accounts a         ON a.account_id = t.account_id
    LEFT JOIN credit_cards cc    ON cc.creditcard_id = t.creditcard_id
    LEFT JOIN debit_cards dc     ON dc.card_id = t.card_id
    LEFT JOIN accounts a2        ON a2.account_id = dc.account_id  ← ALIAS noetig!
    WHERE a.user_id = :uid OR cc.user_id = :uid OR a2.user_id = :uid

    Ein ALIAS (AccountViaCard) ist noetig, weil `accounts` zweimal gejoint wird.

=== VERWENDUNG ===
Aufgerufen von: transaction_service.py (erstellen, aendern, loeschen, filtern)
               budget_service.py (Verbrauchsberechnung pro Monat)
               payment_service.py (Kontoauszug)

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Transaction


# Kapselt reine Datenbankzugriffe fuer Transaktionen.
class TransactionRepository:
    """Datenbankzugriffe fuer Transaction-Objekte.

    Methoden:
    - create:              Neue Transaktion anlegen
    - get_by_id:           Transaktion per ID laden
    - save:                Transaktion aktualisieren
    - delete:              Transaktion loeschen
    - filter_transactions: Transaktionen mit Filtern laden (komplex, mit Joins)
    - list_for_month:      Transaktionen eines Monats laden (fuer Budgets)
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        self.session = session

    def create(self, transaction: Transaction) -> Transaction:
        """Legt eine neue Transaktion in der Datenbank an.

        AUFRUF-KETTE:
            transaction_service.create_transaction(payload)
            → TransactionRepository.create(transaction)
            → SQL: INSERT INTO transactions (amount, date, type, ...) VALUES (...)

        WAS PASSIERT GLEICHZEITIG IM SERVICE:
            Vor dem Speichern der Transaktion aktualisiert der Service auch den
            Kontosaldo (account.balance += or -= amount). Das passiert im Service,
            nicht hier.

        Args:
            transaction: Neues Transaction-Objekt (transaction_id noch nicht gesetzt).

        Returns:
            Gespeicherte Transaction mit transaction_id aus der Datenbank.
        """
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        """Laedt eine Transaktion anhand ihrer ID.

        AUFRUF-KETTE:
            transaction_service.edit_transaction(transaction_id, payload)
            → TransactionRepository.get_by_id(transaction_id)
            → SQL: SELECT * FROM transactions WHERE transaction_id = :transaction_id

        Args:
            transaction_id: Primaerschluessel der Transaktion.

        Returns:
            Transaction-Objekt wenn gefunden, None wenn nicht existent.
        """
        return self.session.get(Transaction, transaction_id)

    def save(self, transaction: Transaction) -> Transaction:
        """Speichert Aenderungen an einer Transaktion.

        AUFRUF-KETTE:
            transaction_service.edit_transaction()
            → TransactionRepository.save(transaction)
            → SQL: UPDATE transactions SET amount=..., note=... WHERE transaction_id=...

        WAS IM SERVICE DAZU PASSIERT:
            Wenn der Betrag geaendert wird, berechnet der Service die Differenz
            und passt den Kontosaldo entsprechend an (z.B. +10 CHF mehr ausgegeben
            = -10 CHF Kontostand).

        Args:
            transaction: Transaction-Objekt mit geaenderten Feldern.

        Returns:
            Aktualisierte Transaction nach dem Speichern.
        """
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def delete(self, transaction: Transaction) -> None:
        """Loescht eine Transaktion dauerhaft.

        AUFRUF-KETTE:
            transaction_service.delete_transaction(transaction_id, confirm=True)
            → TransactionRepository.delete(transaction)
            → SQL: DELETE FROM transactions WHERE transaction_id = :transaction_id

        HINWEIS: Der Service rueckgaengig macht den Kontosaldo vor dem Loeschen
        (addiert bei Ausgabe den Betrag wieder, subtrahiert bei Einnahme).
        Das passiert vor dem Aufruf dieser Methode.

        Args:
            transaction: Das zu loeschende Transaction-Objekt.
        """
        self.session.delete(transaction)
        self.session.commit()

    def filter_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: int | None = None,
        user_id: int | None = None,
        include_recurring_templates: bool = False,
    ) -> list[Transaction]:
        """Filtert Transaktionen mit optionalen Einschraenkungen.

        AUFRUF-KETTE:
            transaction_service.filter_transactions(...)
            → TransactionRepository.filter_transactions(...)
            → Komplexes SQL mit optionalen Filtern und Joins (wenn user_id gesetzt)

        FILTER-PARAMETER (alle optional - None = kein Filter):
            start_date:  Nur Transaktionen ab diesem Datum (inkl.)
            end_date:    Nur Transaktionen bis zu diesem Datum (inkl.)
            category_id: Nur Transaktionen dieser Kategorie
            user_id:     Nur Transaktionen dieses Users (erfordert 3-fachen JOIN)

        KOMPLEX: DER USER-FILTER MIT 3 JOINS
            Wenn user_id gesetzt ist, muessen alle drei moeglichen Quellwege
            geprueft werden. Dafuer werden LEFT JOINs verwendet:
            - LEFT JOIN accounts a ON a.account_id = t.account_id
            - LEFT JOIN credit_cards cc ON cc.creditcard_id = t.creditcard_id
            - LEFT JOIN debit_cards dc ON dc.card_id = t.card_id
            - LEFT JOIN accounts a2 ON a2.account_id = dc.account_id  (ALIAS)

            "LEFT JOIN" bedeutet: der Join-Partner darf fehlen (NULL).
            Denn eine Transaktion hat NUR EINE Quelle (die anderen sind NULL).

            Der ALIAS "AccountViaCard" ist noetig, weil `accounts` zweimal gejoint
            wird (einmal direkt, einmal via DebitCard). SQL erlaubt keinen doppelten
            Tabellennamen ohne Alias.

        SORTIERUNG:
            Neueste Transaktionen zuerst (date DESC, dann transaction_id DESC).

        Args:
            start_date: Startdatum (inkl.) oder None.
            end_date: Enddatum (inkl.) oder None.
            category_id: Kategorie-ID oder None.
            user_id: User-ID oder None.
            include_recurring_templates: Wenn True, werden Template-Transaktionen
                von Daueraufträgen in das Ergebnis eingeschlossen.

        Returns:
            Liste der passenden Transaktionen (neueste zuerst).
        """
        # Basis-Query ohne Filter: alle Transaktionen
        statement = select(Transaction)

        # Optionaler Datumsfilter
        if start_date is not None:
            statement = statement.where(Transaction.date >= start_date)
        if end_date is not None:
            statement = statement.where(Transaction.date <= end_date)

        # Optionaler Kategoriefilter
        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)

        # Optionaler User-Filter (erfordert komplexe Joins)
        if user_id is not None:
            from sqlalchemy.orm import aliased
            from src.domain.models import Account, CreditCard, DebitCard

            # Alias fuer accounts-Tabelle (zweiter Join via DebitCard)
            # WARUM ALIAS? SQL kann nicht zweimal "accounts" in einer Query verwenden
            # ohne sie zu unterscheiden.
            AccountViaCard = aliased(Account)

            # LEFT JOINs: jeder Join-Partner darf fehlen (NULL), weil eine Transaktion
            # nur EINE der drei Quellen haben kann
            statement = statement.join(
                Account,
                isouter=True,  # LEFT JOIN: erlaubt NULL wenn account_id nicht gesetzt
                onclause=Account.account_id == Transaction.account_id,
            ).join(
                CreditCard,
                isouter=True,  # LEFT JOIN: erlaubt NULL wenn creditcard_id nicht gesetzt
                onclause=CreditCard.creditcard_id == Transaction.creditcard_id,
            ).join(
                DebitCard,
                isouter=True,  # LEFT JOIN: erlaubt NULL wenn card_id nicht gesetzt
                onclause=DebitCard.card_id == Transaction.card_id,
            ).join(
                AccountViaCard,
                isouter=True,  # LEFT JOIN: via Debitkarte zum Konto (fuer user_id)
                onclause=AccountViaCard.account_id == DebitCard.account_id,
            ).where(
                # EINE dieser Bedingungen muss erfuellt sein:
                # Entweder gehoert das Konto dem User, oder die Kreditkarte, oder
                # das Konto via Debitkarte
                (Account.user_id == user_id)
                | (CreditCard.user_id == user_id)
                | (AccountViaCard.user_id == user_id)
            )

        # Template-Transaktionen von Dauerauftraegen standardmaessig ausblenden.
        # Fuer den Tab "Geplante Zahlungen" kann der Filter diese Eintraege gezielt
        # wieder einschliessen.
        if not include_recurring_templates:
            from src.domain.models import RecurringTransaction

            statement = statement.where(
                ~Transaction.transaction_id.in_(select(RecurringTransaction.transaction_id))
            )

        # Sortierung: neueste zuerst, bei gleichem Datum nach ID
        statement = statement.order_by(Transaction.date.desc(), Transaction.transaction_id.desc())
        return list(self.session.exec(statement).all())

    def list_for_month(
        self,
        user_id: int,
        month: int,
        year: int,
        category_id: int | None = None,
    ) -> list[Transaction]:
        """Laedt alle Transaktionen eines Users fuer einen bestimmten Monat.

        AUFRUF-KETTE:
            budget_service.check_budget_status(user_id, month, year)
            → TransactionRepository.list_for_month(user_id, month, year)
            → SQL: SELECT t.* ... WHERE date >= '2026-05-01' AND date < '2026-06-01'

        WARUM DIESE METHODE STATT filter_transactions?
            Diese Methode ist speziell fuer Monatsabfragen optimiert.
            Der Zeitraum wird als `[Monatsanfang, Monatsanfang-Folgemonat)`
            berechnet (halboffenes Intervall). Das ist robust gegen die
            unterschiedliche Laenge von Monaten (28, 29, 30, 31 Tage).

        BEISPIEL:
            list_for_month(user_id=5, month=2, year=2026)
            Zeitraum: 01.02.2026 bis 28.02.2026 (Februar hat 28 Tage)
            SQL: WHERE date >= '2026-02-01' AND date < '2026-03-01'
            So werden auch Transaktionen am letzten Februartag korrekt erfasst.

        Args:
            user_id: ID des Users, dessen Transaktionen geladen werden sollen.
            month: Monat (1-12).
            year: Jahr (z.B. 2026).
            category_id: Optionaler Kategoriefilter (None = alle Kategorien).

        Returns:
            Alle Transaktionen des Users in diesem Monat.
        """
        from src.domain.models import Account, CreditCard, DebitCard

        # Zeitraum: [1. des Monats, 1. des Folgemonats)
        # month // 12 = 1 wenn month=12, sonst 0 (Jahr-Uebertrag)
        # (month % 12) + 1 = Folgemonat (12 % 12 = 0, + 1 = 1 = Januar des Folgejahres)
        statement = select(Transaction).where(
            Transaction.date >= date(year, month, 1),
            Transaction.date < date(year + (month // 12), ((month % 12) + 1), 1),
        )

        if category_id is not None:
            statement = statement.where(Transaction.category_id == category_id)

        from sqlalchemy.orm import aliased
        # Alias fuer zweiten accounts-Join (gleiche Begruendung wie in filter_transactions)
        AccountViaCard = aliased(Account)

        # Gleicher 3-facher JOIN wie in filter_transactions (user_id-Zuordnung)
        statement = statement.join(
            Account, isouter=True, onclause=Account.account_id == Transaction.account_id,
        ).join(
            CreditCard, isouter=True, onclause=CreditCard.creditcard_id == Transaction.creditcard_id,
        ).join(
            DebitCard, isouter=True, onclause=DebitCard.card_id == Transaction.card_id,
        ).join(
            AccountViaCard, isouter=True, onclause=AccountViaCard.account_id == DebitCard.account_id,
        ).where(
            (Account.user_id == user_id)
            | (CreditCard.user_id == user_id)
            | (AccountViaCard.user_id == user_id)
        )

        # Template-Transaktionen von Dauerauftraegen ausblenden
        from src.domain.models import RecurringTransaction
        statement = statement.where(
            ~Transaction.transaction_id.in_(select(RecurringTransaction.transaction_id))
        )

        return list(self.session.exec(statement).all())
