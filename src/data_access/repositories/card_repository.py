"""src.data_access.repositories.card_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS SPEICHERT DIESES REPOSITORY? ===
Zwei Kartentypen:
    1. DebitCard  (Debitkarte)  - gehoert zu einem Konto (account_id)
    2. CreditCard (Kreditkarte) - gehoert zu einem User (user_id)

Beide haben einen Status: "aktiv", "gesperrt" oder "ersetzt".

=== UNTERSCHIED DEBITKARTE VS. KREDITKARTE ===
DEBITKARTE:
    - Direkt mit einem Konto verbunden (account_id)
    - Zahlung belastet sofort das Konto
    - Max. 1 aktive Debitkarte pro Konto (Regel im card_service.py)
    - Zuordnung: DebitCard.account_id → Account.account_id → Account.user_id

KREDITKARTE:
    - Direkt mit einem User verbunden (user_id), nicht mit einem Konto
    - Hat eigenen "Kredit-Saldo" (.balance = bisher genutzer Kredit, nicht Kontostand!)
    - Hat ein Abrechnungskonto (billing_account_id) fuer monatliche Abbuchung
    - Max. 1 aktive Kreditkarte pro User (Regel im card_service.py)

=== WARUM "via Account JOIN" fuer Debitkarten? ===
Um alle Debitkarten EINES USERS zu finden, muss man ueber die Account-Tabelle gehen:
User → Accounts → DebitCards (weil DebitCard kein user_id-Feld hat).
Das SQL sieht so aus: JOIN accounts ON accounts.account_id = debit_cards.account_id
                      WHERE accounts.user_id = :user_id

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank

    Aufgerufen von: card_service.py und creditcard_billing_service.py
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import CreditCard, DebitCard


# Kapselt reine Datenbankzugriffe fuer Debit- und Kreditkarten.
class CardRepository:
    """Datenbankzugriffe fuer DebitCard und CreditCard.

    Enthaelt Methoden zum Laden, Erstellen und Aktualisieren beider Kartentypen.
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        self.session = session

    # ===== DEBITKARTEN =====

    def get_debit_by_id(self, card_id: int) -> DebitCard | None:
        """Laedt eine Debitkarte anhand ihrer ID.

        AUFRUF-KETTE:
            card_service.block_debit_card(card_id)
            → CardRepository.get_debit_by_id(card_id)
            → SQL: SELECT * FROM debit_cards WHERE card_id = :card_id

        Args:
            card_id: Primaerschluessel der Debitkarte.

        Returns:
            DebitCard-Objekt wenn gefunden, None wenn nicht existent.
        """
        return self.session.get(DebitCard, card_id)

    def list_debit_by_account(self, account_id: int) -> list[DebitCard]:
        """Laedt ALLE Debitkarten eines Kontos (inkl. gesperrter/ersetzter).

        AUFRUF-KETTE:
            card_service (prueft ob Karte vorhanden)
            → CardRepository.list_debit_by_account(account_id)
            → SQL: SELECT * FROM debit_cards WHERE account_id = :account_id

        WARUM AUCH INAKTIVE?
            Fuer die Regel "max. 1 aktive Karte pro Konto" wird
            list_active_debit_by_account() verwendet. Diese Methode gibt
            ALLE zurueck (fuer historische Uebersichten).

        Args:
            account_id: ID des Kontos.

        Returns:
            Alle Debitkarten dieses Kontos (egal welchen Status).
        """
        statement = select(DebitCard).where(DebitCard.account_id == account_id)
        return list(self.session.exec(statement).all())

    def list_active_debit_by_account(self, account_id: int) -> list[DebitCard]:
        """Laedt nur die aktiven Debitkarten eines Kontos.

        AUFRUF-KETTE:
            card_service.order_debit_card() (prueft: gibt es schon eine aktive?)
            → CardRepository.list_active_debit_by_account(account_id)
            → SQL: SELECT * FROM debit_cards WHERE account_id=? AND status='aktiv'

        GESCHAEFTSREGEL:
            Diese Methode wird genutzt, um die Regel "max. 1 aktive Debitkarte
            pro Konto" zu erzwingen. Wenn diese Liste nicht leer ist, darf
            keine neue bestellt werden.

        Args:
            account_id: ID des Kontos.

        Returns:
            Liste der aktiven Debitkarten (in den meisten Faellen 0 oder 1 Element).
        """
        statement = select(DebitCard).where(
            DebitCard.account_id == account_id,
            DebitCard.status == "aktiv",
        )
        return list(self.session.exec(statement).all())

    def create_debit(self, card: DebitCard) -> DebitCard:
        """Legt eine neue Debitkarte in der Datenbank an.

        AUFRUF-KETTE:
            card_service.order_debit_card(account_id)
            → CardRepository.create_debit(new_card)
            → SQL: INSERT INTO debit_cards (card_number, expire_date, status, account_id) VALUES (...)

        Args:
            card: Neues DebitCard-Objekt (card_id noch nicht gesetzt).

        Returns:
            Gespeicherte DebitCard mit card_id aus der Datenbank.
        """
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card

    def save_debit(self, card: DebitCard) -> DebitCard:
        """Speichert Aenderungen an einer Debitkarte (z.B. Status-Aenderung).

        AUFRUF-KETTE:
            card_service.block_debit_card() oder replace_debit_card()
            → CardRepository.save_debit(card)
            → SQL: UPDATE debit_cards SET status=... WHERE card_id=...

        WANN GENUTZT:
            - Karte sperren: card.status = "gesperrt" → save_debit(card)
            - Karte ersetzen: alte card.status = "ersetzt" → save_debit(card)

        Args:
            card: DebitCard-Objekt mit geaenderten Feldern.

        Returns:
            Aktualisierte DebitCard nach dem Speichern.
        """
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card

    def list_debit_by_user(self, user_id: int) -> list[DebitCard]:
        """Laedt alle Debitkarten eines Users (via Account-Tabelle).

        AUFRUF-KETTE:
            card_service.list_debit_cards(user_id)
            → CardRepository.list_debit_by_user(user_id)
            → SQL: SELECT dc.* FROM debit_cards dc
                   JOIN accounts a ON a.account_id = dc.account_id
                   WHERE a.user_id = :user_id

        WARUM JOIN?
            Debitkarten haben keine direkte user_id. Sie gehoeren einem Konto,
            und Konten gehoeren einem User. Der Weg ist:
            User → Account (via Account.user_id)
            Account → DebitCard (via DebitCard.account_id)

        Args:
            user_id: ID des Users, dessen Debitkarten geladen werden sollen.

        Returns:
            Alle Debitkarten des Users (egal welchen Status).
        """
        from src.domain.models import Account
        # JOIN: debit_cards mit accounts verbinden, um User-Zugehoerigkeit zu pruefen
        statement = (
            select(DebitCard)
            .join(Account, Account.account_id == DebitCard.account_id)
            .where(Account.user_id == user_id)
        )
        return list(self.session.exec(statement).all())

    # ===== KREDITKARTEN =====

    def get_credit_by_id(self, creditcard_id: int) -> CreditCard | None:
        """Laedt eine Kreditkarte anhand ihrer ID.

        Args:
            creditcard_id: Primaerschluessel der Kreditkarte.

        Returns:
            CreditCard-Objekt wenn gefunden, None wenn nicht existent.
        """
        return self.session.get(CreditCard, creditcard_id)

    def list_credit_by_user(self, user_id: int) -> list[CreditCard]:
        """Laedt alle Kreditkarten eines Users.

        AUFRUF-KETTE:
            card_service.list_credit_cards(user_id)
            → CardRepository.list_credit_by_user(user_id)
            → SQL: SELECT * FROM credit_cards WHERE user_id = :user_id

        EINFACHER ALS DEBITKARTEN:
            Kreditkarten haben eine direkte user_id, daher brauchen wir keinen JOIN.

        Args:
            user_id: ID des Users.

        Returns:
            Alle Kreditkarten des Users (egal welchen Status).
        """
        statement = select(CreditCard).where(CreditCard.user_id == user_id)
        return list(self.session.exec(statement).all())

    def create_credit(self, card: CreditCard) -> CreditCard:
        """Legt eine neue Kreditkarte in der Datenbank an.

        AUFRUF-KETTE:
            card_service.create_credit_card(payload)
            → CardRepository.create_credit(new_card)
            → SQL: INSERT INTO credit_cards (...) VALUES (...)

        Args:
            card: Neues CreditCard-Objekt (creditcard_id noch nicht gesetzt).

        Returns:
            Gespeicherte CreditCard mit creditcard_id aus der Datenbank.
        """
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card

    def save_credit(self, card: CreditCard) -> CreditCard:
        """Speichert Aenderungen an einer Kreditkarte (Status, Saldo, Abrechnungskonto).

        AUFRUF-KETTE:
            card_service.block_credit_card() / set_billing_account() / etc.
            → CardRepository.save_credit(card)
            → SQL: UPDATE credit_cards SET status=..., balance=... WHERE creditcard_id=...

        WANN GENUTZT:
            - Karte sperren: card.status = "gesperrt"
            - Abrechnungskonto setzen: card.billing_account_id = account_id
            - Saldo aktualisieren (nach Abrechnung): card.balance = 0.0

        Args:
            card: CreditCard-Objekt mit geaenderten Feldern.

        Returns:
            Aktualisierte CreditCard nach dem Speichern.
        """
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card
