"""src.services.card_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der CardService verwaltet zwei Kartentypen:
    1. Debitkarte (DebitCard): gebunden an ein Konto
    2. Kreditkarte (CreditCard): gebunden an einen User

Aktionen:
    - Debitkarte bestellen, sperren, ersetzen
    - Kreditkarte beantragen, sperren, ersetzen
    - Abrechnungskonto fuer Kreditkarte setzen
    - Karten auflisten (Debit/Kredit)

=== DEBITKARTE vs. KREDITKARTE - DER UNTERSCHIED ===

DEBITKARTE:
    - Gehoert zu einem KONTO (account_id)
    - Beim Bezahlen wird sofort vom Konto abgebucht
    - Nur fuer Privatkonten (nicht Sparkonten)
    - Maximal 1 aktive Debitkarte pro User (global ueber alle Konten!)

KREDITKARTE:
    - Gehoert zu einem USER (user_id) - nicht direkt an ein Konto
    - Hat einen Kreditrahmen (limit) und einen offenen Betrag (balance)
    - balance = GENUTZTER KREDIT (nicht Kontostand!)
    - Monatliche Abrechnung: balance wird vom Abrechnungskonto abgezogen
    - Abrechnungskonto muss separat gesetzt werden (set_billing_account)

=== KARTENNUMMER-GENERIERUNG ===
    16 zufaellige Ziffern (reine Demo, keine echte Luhn-Pruefsumme).

=== ARCHITEKTUR-KETTE ===
    View (card_view.py) → Controller (card_controller.py)
    → **CardService (du bist hier)**
    → CardRepository (Karten laden/speichern)
    → AccountRepository (Konto validieren / Benutzer-IDs pruefen)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `card_service = CardService()`
"""

from __future__ import annotations

import random
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import CreditCard, DebitCard
from src.utils.validators import validate_positive_amount


class CardService:
    """Service fuer Debitkarten und Kreditkarten-Verwaltung."""

    def list_debit_cards(self, user_id: int) -> list[DebitCard]:
        """Listet alle Debitkarten eines Users (inkl. gesperrter/ersetzter).

        AUFRUF-KETTE:
            card_controller.list_debit_cards(user_id)
            → CardService.list_debit_cards(user_id)
            → CardRepository.list_debit_by_user(user_id)
            → SQL: SELECT dc.* FROM debit_cards dc
                   JOIN accounts a ON a.account_id = dc.account_id
                   WHERE a.user_id = :user_id

        RUECKGABE-KETTE:
            DB → CardRepository → CardService → card_controller
            → View zeigt Tabelle: Kartennummer, Ablaufdatum, Status

        WARUM JOIN UEBER ACCOUNTS?
            Debitkarten haben keine direkte user_id.
            Sie haengen an Konten, und Konten haengen an Users.
            Weg: User → Konten → Debitkarten

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            Liste aller DebitCard-Objekte des Users.
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            return card_repository.list_debit_by_user(user_id)

    def list_credit_cards(self, user_id: int) -> list[dict]:
        """Listet Kreditkarten und loest das Abrechnungskonto (IBAN) auf.

        AUFRUF-KETTE:
            card_controller.list_credit_cards(user_id)
            → CardService.list_credit_cards(user_id)
            → CardRepository.list_credit_by_user(user_id)           [Karten laden]
            → AccountRepository.get_by_id(billing_account_id)       [IBAN laden, falls vorhanden]

        RUECKGABE-KETTE:
            DB → CardService (dict erstellen) → card_controller
            → View zeigt: Kartennummer, Limit, Verbrauch, Abrechnungskonto-IBAN

        WARUM DICT STATT CREDITCARD-OBJEKT?
            Die View will zusaetzliche, "aufgeloeste" Daten anzeigen:
            billing_account (IBAN des Abrechnungskontos).
            Das ist einfacher als in der View selbst mehrere DB-Calls zu machen.
            Der Service erledigt alle noetigen Datenbankzugriffe und gibt
            ein flaches Dictionary zurueck.

        RUECKGABE-DICT (pro Karte):
            - creditcard_id, card_number, expire_date
            - limit:          Kreditrahmen (z.B. 5000.00)
            - balance:        Genutzter Kredit (z.B. 230.50)
            - status:         "aktiv", "gesperrt", "ersetzt" oder "beantragt"
            - user_id
            - billing_account_id: Konto-ID fuer Monatsabrechnung (oder None)
            - billing_account:    {"iban": "CH..."} (oder None wenn nicht gesetzt)
            - last_billed:        Datum der letzten Abrechnung (oder None)

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            Liste von Dictionaries (ein Dict pro Kreditkarte).
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            account_repository = AccountRepository(session)
            cards = card_repository.list_credit_by_user(user_id)
            result = []
            for card in cards:
                billing_account = None
                if card.billing_account_id is not None:
                    # Abrechnungskonto ist optional. Wenn gesetzt, laden wir die IBAN fuer die Anzeige.
                    acc = account_repository.get_by_id(card.billing_account_id)
                    if acc is not None:
                        billing_account = {"iban": acc.iban}
                result.append({
                    "creditcard_id": card.creditcard_id,
                    "card_number": card.card_number,
                    "expire_date": card.expire_date,
                    "limit": card.limit,
                    # `balance` = genutzter Kredit (nicht Kontostand!).
                    "balance": card.balance,
                    "status": card.status,
                    "user_id": card.user_id,
                    "billing_account_id": card.billing_account_id,
                    "billing_account": billing_account,
                    "last_billed": card.last_billed,
                })
            return result

    def order_debit_card(self, account_id: int) -> DebitCard:
        """Bestellt eine neue Debitkarte fuer ein Privatkonto.

        AUFRUF-KETTE:
            card_controller.order_debit_card(account_id)
            → CardService.order_debit_card(account_id)
            → AccountRepository.get_by_id(account_id)                  [Konto laden]
            → list_active_debit_by_account(account_id)                  [1-Karten-Regel]
            → CardRepository.create_debit(card)                         [Karte speichern]
            → SQL: INSERT INTO debit_cards (...) VALUES (...)

        RUECKGABE-KETTE:
            DB → CardRepository → CardService → card_controller
            → View zeigt: "Debitkarte bestellt" + Kartennummer

        GESCHAEFTSREGELN:
            1. Debitkarten nur fuer Privatkonten (nicht Sparkonten)
               → Weil Sparkonten fuer langfristiges Sparen gedacht sind,
                 nicht fuer taegliche Zahlungen
            2. Maximal 1 aktive Debitkarte pro Privatkonto
               → list_active_debit_by_account prueft nur das bestellte Konto

        ABLAUFDATUM:
            Debitkarten laufen 4 Jahre ab heute ab.
            Tag = 1 (immer der Erste des Monats, wie bei echten Karten).

        Args:
            account_id: Datenbank-ID des Kontos, fuer das eine Karte bestellt wird.

        Returns:
            Die neu erstellte DebitCard (mit card_id aus der DB).

        Raises:
            KeyError: Wenn das Konto nicht existiert.
            ValueError: Wenn das Konto kein Privatkonto ist.
            ValueError: Wenn das Konto bereits eine aktive Debitkarte hat.
        """
        with Session(engine) as session:
            account_repository = AccountRepository(session)
            card_repository = CardRepository(session)

            account = account_repository.get_by_id(account_id)
            if account is None:
                raise KeyError(f"Konto {account_id} nicht gefunden")

            # Geschaeftsregel 1: Nur fuer Privatkonten.
            if account.account_type != "privat":
                raise ValueError("Debitkarten koennen nur fuer Privatkonten bestellt werden")

            # Geschaeftsregel 2: Max. eine aktive Debitkarte pro Privatkonto.
            active_cards = card_repository.list_active_debit_by_account(account_id)
            if active_cards:
                raise ValueError("Dieses Konto hat bereits eine aktive Debitkarte")

            card = DebitCard(
                card_number=self._generate_card_number(),
                expire_date=date(date.today().year + 4, date.today().month, 1),
                status="aktiv",
                account_id=account_id,
            )
            return card_repository.create_debit(card)

    def block_debit_card(self, card_id: int) -> DebitCard:
        """Sperrt eine Debitkarte (status = "gesperrt").

        AUFRUF-KETTE:
            card_controller.block_debit_card(card_id)
            → CardService.block_debit_card(card_id)
            → CardRepository.get_debit_by_id(card_id)
            → card.block()                       [Status auf "gesperrt" setzen]
            → CardRepository.save_debit(card)
            → SQL: UPDATE debit_cards SET status='gesperrt' WHERE card_id=:id

        RUECKGABE-KETTE:
            DB → CardRepository → CardService → card_controller
            → View zeigt: "Karte gesperrt"

        WAS MACHT card.block()?
            Methode auf dem DebitCard-Modell (domain/models.py).
            Setzt card.status = "gesperrt".

        Args:
            card_id: Datenbank-ID der Debitkarte.

        Returns:
            Aktualisierte DebitCard mit status="gesperrt".

        Raises:
            KeyError: Wenn keine Debitkarte mit dieser ID existiert.
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            card = card_repository.get_debit_by_id(card_id)
            if card is None:
                raise KeyError(f"Debitkarte {card_id} nicht gefunden")
            card.block()
            return card_repository.save_debit(card)

    def replace_debit_card(self, card_id: int) -> DebitCard:
        """Ersetzt eine Debitkarte: alte wird "ersetzt" markiert, neue wird aktiv.

        AUFRUF-KETTE:
            card_controller.replace_debit_card(card_id)
            → CardService.replace_debit_card(card_id)
            → CardRepository.get_debit_by_id(card_id)            [Alte Karte laden]
            → old_card.replace()                                   [Status = "ersetzt"]
            → CardRepository.save_debit(old_card)                 [Alte Karte speichern]
            → list_active_debit_by_account(account_id)            [Sicherheitscheck]
            → CardRepository.create_debit(new_card)               [Neue Karte anlegen]

        RUECKGABE-KETTE:
            DB → CardRepository → CardService → card_controller
            → View zeigt: "Neue Karte bestellt" + neue Kartennummer

        WARUM SALDO-UEBERNAHME?
            Bei Debitkarten gibt es keinen eigenen Saldo (das Geld liegt im Konto).
            Das Konto wird unveraendert weitergefuehrt. Nur die Karte wird neu ausgestellt.

        Args:
            card_id: Datenbank-ID der zu ersetzenden Debitkarte.

        Returns:
            Die neue DebitCard.

        Raises:
            KeyError: Wenn Karte oder zugehoeriges Konto nicht existiert.
            ValueError: Wenn bereits eine andere aktive Debitkarte vorhanden ist.
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            account_repository = AccountRepository(session)

            old_card = card_repository.get_debit_by_id(card_id)
            if old_card is None:
                raise KeyError(f"Debitkarte {card_id} nicht gefunden")
            old_account = account_repository.get_by_id(old_card.account_id)
            if old_account is None:
                raise KeyError(f"Konto {old_card.account_id} nicht gefunden")

            # Alte Karte als "ersetzt" markieren (nicht "gesperrt"!).
            old_card.replace()
            card_repository.save_debit(old_card)

            # Sicherheitscheck: Gibt es schon eine aktive Karte fuer dieses Konto?
            active_cards = card_repository.list_active_debit_by_account(old_card.account_id)
            if active_cards:
                raise ValueError("Dieses Konto hat bereits eine aktive Debitkarte")

            new_card = DebitCard(
                card_number=self._generate_card_number(),
                expire_date=date(date.today().year + 4, date.today().month, 1),
                status="aktiv",
                account_id=old_card.account_id,
            )
            return card_repository.create_debit(new_card)

    def create_credit_card(self, payload: dict) -> CreditCard:
        """Beantragt eine neue Kreditkarte mit einem gewuenschten Limit.

        AUFRUF-KETTE:
            card_controller.create_credit_card(payload)
            → CardService.create_credit_card(payload)
            → validate_positive_amount(desired_limit)
            → UserRepository.get_by_id(user_id)
            → CardRepository.create_credit(credit_card)
            → SQL: INSERT INTO credit_cards (...) VALUES (...)

        RUECKGABE-KETTE:
            DB → CardRepository → CardService → card_controller
            → View zeigt: "Kreditkarte beantragt" + Kartennummer

        WARUM STATUS "BEANTRAGT" STATT "AKTIV"?
            In einer echten Bank dauert es mehrere Tage, bis eine Kreditkarte
            aktiviert wird (Kreditpruefung, Versand etc.). Der Demo-Status
            "beantragt" bildet diesen Workflow ab. Manche Views zeigen
            "beantragt"-Karten anders an.

        MAXIMALES KREDITLIMIT:
            CHF 10'000. Das ist eine Demo-Grenze. Echte Banken pruefen Bonität.

        PAYLOAD-KEYS:
            - "user_id" (int/str)        → Pflichtfeld
            - "desired_limit" (float/str) → Pflichtfeld, Wunschlimit (max. 10'000)

        Args:
            payload: Dictionary aus Controller/UI.

        Returns:
            Neue CreditCard mit status="beantragt" und balance=0.0.

        Raises:
            ValueError: Wenn desired_limit <= 0 oder > 10'000.
            KeyError: Wenn der User nicht existiert.
        """
        MAX_CREDIT_LIMIT = 10_000.0
        user_id = int(payload["user_id"])
        desired_limit = float(payload["desired_limit"])
        validate_positive_amount(desired_limit)

        # Demo-Grenze: Kein Limit ueber CHF 10'000.
        if desired_limit > MAX_CREDIT_LIMIT:
            raise ValueError(f"Maximales Kreditlimit betraegt CHF {MAX_CREDIT_LIMIT:,.0f}")

        with Session(engine) as session:
            user_repository = UserRepository(session)
            card_repository = CardRepository(session)

            if user_repository.get_by_id(user_id) is None:
                raise KeyError(f"User {user_id} nicht gefunden")

            credit_card = CreditCard(
                card_number=self._generate_card_number(),
                expire_date=date(date.today().year + 4, date.today().month, 1),
                limit=desired_limit,
                balance=0.0,   # Kein genutzter Kredit am Anfang.
                status="beantragt",
                user_id=user_id,
            )
            return card_repository.create_credit(credit_card)

    def block_credit_card(self, creditcard_id: int) -> CreditCard:
        """Sperrt eine Kreditkarte (status = "gesperrt").

        AUFRUF-KETTE:
            card_controller.block_credit_card(creditcard_id)
            → CardService.block_credit_card(creditcard_id)
            → CardRepository.get_credit_by_id(creditcard_id)
            → card.block()
            → CardRepository.save_credit(card)
            → SQL: UPDATE credit_cards SET status='gesperrt' WHERE creditcard_id=:id

        Args:
            creditcard_id: Datenbank-ID der Kreditkarte.

        Returns:
            Aktualisierte CreditCard mit status="gesperrt".

        Raises:
            KeyError: Wenn keine Kreditkarte mit dieser ID existiert.
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            card = card_repository.get_credit_by_id(creditcard_id)
            if card is None:
                raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
            card.block()
            return card_repository.save_credit(card)

    def replace_credit_card(self, creditcard_id: int) -> CreditCard:
        """Ersetzt eine Kreditkarte und uebernimmt den offenen Saldo.

        AUFRUF-KETTE:
            card_controller.replace_credit_card(creditcard_id)
            → CardService.replace_credit_card(creditcard_id)
            → CardRepository.get_credit_by_id(creditcard_id)   [Alte Karte laden]
            → old_card.replace()                                 [Status = "ersetzt"]
            → CardRepository.save_credit(old_card)              [Alte Karte speichern]
            → CardRepository.create_credit(new_card)            [Neue Karte mit Saldo]

        WARUM SALDO UEBERNEHMEN?
            balance = genutzter Kredit. Wenn eine Karte ersetzt wird, soll
            der offene Betrag nicht verschwinden. Die neue Karte erbt den
            Saldo der alten Karte. Auch das Limit wird uebernommen.

        Args:
            creditcard_id: Datenbank-ID der alten Kreditkarte.

        Returns:
            Die neue CreditCard (mit uebernommenem Saldo und Limit).

        Raises:
            KeyError: Wenn keine Kreditkarte mit dieser ID existiert.
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            old_card = card_repository.get_credit_by_id(creditcard_id)
            if old_card is None:
                raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
            old_card.replace()
            card_repository.save_credit(old_card)

            new_card = CreditCard(
                card_number=self._generate_card_number(),
                expire_date=date(date.today().year + 4, date.today().month, 1),
                limit=old_card.limit,         # Limit von alter Karte uebernehmen.
                balance=old_card.balance,     # Offener Saldo von alter Karte uebernehmen.
                status="aktiv",
                user_id=old_card.user_id,
            )
            return card_repository.create_credit(new_card)

    def set_billing_account(self, creditcard_id: int, account_id: int) -> CreditCard:
        """Setzt das Abrechnungskonto einer Kreditkarte.

        AUFRUF-KETTE:
            card_controller.set_billing_account(creditcard_id, account_id)
            → CardService.set_billing_account(creditcard_id, account_id)
            → CardRepository.get_credit_by_id(creditcard_id)   [Kreditkarte laden]
            → AccountRepository.get_by_id(account_id)          [Konto laden]
            → Validierungen (aktiv? gleicher User?)
            → credit_card.billing_account_id = account_id
            → CardRepository.save_credit(credit_card)
            → SQL: UPDATE credit_cards SET billing_account_id=:id WHERE creditcard_id=:id

        RUECKGABE-KETTE:
            DB → CardRepository → CardService → card_controller
            → View zeigt: "Abrechnungskonto gesetzt"

        WAS IST DAS ABRECHNUNGSKONTO?
            Jeden Monat wird der offene Kreditkartenbetrag (balance) vom
            Abrechnungskonto abgebucht. Ohne Abrechnungskonto kann keine
            monatliche Abrechnung stattfinden (creditcard_billing_service
            prueft billing_account_id != None).

        SICHERHEITSREGELN:
            - Abrechnungskonto muss dem GLEICHEN User gehoeren wie die Kreditkarte
              (verhindert, dass man mit einem fremden Konto abrechnet)
            - Konto muss aktiv sein

        Args:
            creditcard_id: Datenbank-ID der Kreditkarte.
            account_id: Datenbank-ID des Kontos als Abrechnungskonto.

        Returns:
            Aktualisierte CreditCard mit gesetztem billing_account_id.

        Raises:
            KeyError: Wenn Kreditkarte oder Konto nicht existiert.
            ValueError: Wenn Konto inaktiv oder anderer User.
        """
        with Session(engine) as session:
            card_repository = CardRepository(session)
            account_repository = AccountRepository(session)

            # Kreditkarte laden.
            credit_card = card_repository.get_credit_by_id(creditcard_id)
            if credit_card is None:
                raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")

            # Konto laden.
            account = account_repository.get_by_id(account_id)
            if account is None:
                raise KeyError(f"Konto {account_id} nicht gefunden")

            # Regel: Konto muss aktiv sein.
            if account.status != "aktiv":
                raise ValueError(f"Konto {account_id} ist nicht aktiv")

            # Sicherheitsregel: Kreditkarte und Konto muessen dem gleichen User gehoeren.
            if credit_card.user_id != account.user_id:
                raise ValueError("Kreditkarte und Konto gehoeren nicht zum selben User")

            # Abrechnungskonto setzen.
            credit_card.billing_account_id = account_id
            return card_repository.save_credit(credit_card)

    def _generate_card_number(self) -> str:
        """Generiert eine zufaellige 16-stellige Kartennummer (Demo).

        ACHTUNG: Keine echte Luhn-Validierung. Reine Demo-Nummern.
        Echte Kreditkarten haben eine Pruefsumme (Luhn-Algorithmus).
        """
        return "".join(str(random.randint(0, 9)) for _ in range(16))



# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.card_service import card_service`
card_service = CardService()
