"""src.data_access.repositories.payment_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS IST DER UNTERSCHIED ZWISCHEN TRANSAKTION, ZAHLUNG UND UMBUCHUNG? ===

Eine TRANSAKTION (`Transaction`) ist die Basistabelle fuer alle Geldbewegungen.
Sie speichert: Betrag, Datum, Typ (income/expense), Kategorie, Quelle.

Spezifische Geldbewegungstypen koennen ZUSAETZLICHE Informationen haben:

ZAHLUNG (`Payment`):
    Zusaetzlich zu den Basis-Feldern: Ziel-IBAN (wohin das Geld geht).
    Beispiel: Miete ueberweisen → Transaktion (Ausgabe CHF 1200) + Payment (Ziel-IBAN "CH...")

UMBUCHUNG (`Transfer`):
    Zusaetzlich: from_account_id und to_account_id (von welchem auf welches Konto).
    Beispiel: Geld auf Sparkonto: 2 Transaktionen (Ausgabe + Einnahme) + 1 Transfer-Verknuepfung

=== WARUM DIESE STRUKTUR? ===
Die Basis-Felder aller Geldbewegungen (Betrag, Datum, Kategorie) stehen immer
in `transactions`. Nur spezifische Felder kommen in `payments` oder `transfers`.
Das vermeidet Spalten, die fuer viele Zeilen immer NULL waeren.

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank

    Aufgerufen von: payment_service.py
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Payment, Transaction, Transfer


# Kapselt reine Datenbankzugriffe fuer Zahlungsobjekte.
class PaymentRepository:
    """Datenbankzugriffe fuer Payment, Transfer und Transaktionslisten fuer Kontoauszuege.

    Enthaelt drei Gruppen von Methoden:
    1. Zahlung (create_payment): Zusatzdaten zu einer Inlandszahlung speichern
    2. Umbuchung (create_transfer): Zusatzdaten zu einer Kontoumbuchung speichern
    3. Kontoauszug (list_account_transactions_in_range): Transaktionen laden
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        self.session = session

    def create_payment(self, payment: Payment) -> Payment:
        """Speichert ein Payment-Objekt (Zahlungs-Zusatzdaten) in der Datenbank.

        AUFRUF-KETTE:
            payment_service.create_payment(payload)
            → [Zuerst: transaction_service.create_transaction → Basis-Transaktion]
            → PaymentRepository.create_payment(payment)
            → SQL: INSERT INTO payments (transaction_id, target_iban, ...) VALUES (...)

        WAS ENTHAELT EIN PAYMENT?
            - transaction_id: Verbindung zur Basis-Transaktion (der Geldbetrag)
            - target_iban:    Ziel-IBAN wohin das Geld geht
            Weitere Felder je nach Modell (z.B. Verwendungszweck)

        HINWEIS: Vor dem Aufruf dieser Methode muss bereits eine Transaction
        erstellt worden sein, da Payment eine transaction_id braucht.

        Args:
            payment: Payment-Objekt mit gesetzter transaction_id und target_iban.

        Returns:
            Gespeichertes Payment-Objekt mit payment_id aus der Datenbank.
        """
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment

    def create_transfer(self, transfer: Transfer) -> Transfer:
        """Speichert ein Transfer-Objekt (Umbuchungs-Zusatzdaten) in der Datenbank.

        AUFRUF-KETTE:
            payment_service.create_transfer(payload)
            → [Zuerst: 2x transaction_service.create_transaction → Ausgabe + Einnahme]
            → PaymentRepository.create_transfer(transfer)
            → SQL: INSERT INTO transfers (transaction_id, from_account_id, to_account_id) VALUES (...)

        WAS ENTHAELT EIN TRANSFER?
            - transaction_id:    Verbindung zur Ausgabe-Transaktion (vom Quellkonto)
            - from_account_id:   Quellkonto (wird belastet)
            - to_account_id:     Zielkonto (wird gutgeschrieben)
            Die Umbuchung erzeugt intern 2 Transaktionen (Ausgabe + Einnahme).
            Der Transfer-Eintrag verknuepft sie miteinander.

        Args:
            transfer: Transfer-Objekt mit transaction_id, from- und to_account_id.

        Returns:
            Gespeichertes Transfer-Objekt mit transfer_id aus der Datenbank.
        """
        self.session.add(transfer)
        self.session.commit()
        self.session.refresh(transfer)
        return transfer

    def list_account_transactions_in_range(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
    ) -> list[Transaction]:
        """Laedt alle Transaktionen eines Kontos in einem Zeitraum (fuer Kontoauszug).

        AUFRUF-KETTE:
            payment_service.generate_statement(account_id, start_date, end_date)
            → PaymentRepository.list_account_transactions_in_range(...)
            → SQL: SELECT * FROM transactions
                   WHERE account_id = :account_id
                   AND date >= :start_date AND date <= :end_date
                   ORDER BY date ASC, transaction_id ASC

        WARUM AUFSTEIGEND SORTIERT?
            Ein Kontoauszug wird chronologisch gelesen (aelteste Buchung zuerst).
            Deshalb sortieren wir aufsteigend (ASC), nicht absteigend.

        UNTERSCHIED ZU filter_transactions():
            Diese Methode sucht nur nach account_id (direkte Konto-Transaktionen).
            filter_transactions() in transaction_repository.py ist viel komplexer
            (sucht auch via Debitkarten und Kreditkarten).

        Args:
            account_id: ID des Kontos, fuer das der Auszug erstellt werden soll.
            start_date: Erster Tag des Zeitraums (inkl., z.B. date(2026, 5, 1)).
            end_date: Letzter Tag des Zeitraums (inkl., z.B. date(2026, 5, 31)).

        Returns:
            Liste der Transaktionen, chronologisch sortiert (aelteste zuerst).
        """
        statement = (
            select(Transaction)
            .where(Transaction.account_id == account_id)    # Nur dieses Konto
            .where(Transaction.date >= start_date)           # Ab Startdatum
            .where(Transaction.date <= end_date)             # Bis Enddatum
            .order_by(Transaction.date.asc(), Transaction.transaction_id.asc())  # Chronologisch
        )
        return list(self.session.exec(statement).all())
