"""src.services.transaction_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der TransactionService verwaltet Transaktionen (Geldbewegungen) und ist
die ZENTRALE STELLE fuer Saldoanpassungen. Wenn eine Transaktion erstellt,
geaendert oder geloescht wird, passt dieser Service den Saldo der Quelle an.

=== TYPEN VON TRANSAKTIONEN ===
    - "income":  Einnahme  → Saldo steigt
    - "expense": Ausgabe   → Saldo sinkt

=== EXACTLY-ONE-QUELLEN-REGEL ===
Jede Transaktion MUSS genau EINE Quelle haben:
    - account_id     → Direkte Kontozahlung (Saldo des Kontos wird geaendert)
    - card_id        → Debitkartenzahlung (Saldo des Kontos wird geaendert)
    - creditcard_id  → Kreditkartenzahlung (genutzter Kredit der Karte wird geaendert)

NICHT erlaubt:
    - Keine Quelle   (ValueError: "Genau eine Quelle muss gesetzt sein")
    - Zwei Quellen   (ValueError: "Bei creditcard_id duerfen account_id und card_id nicht gesetzt sein")

=== SALDO-UPDATE-MECHANISMUS (multiplier-Trick) ===
Die Methode `_apply_source_effect(transaction, multiplier)` wird in drei Situationen
aufgerufen:
    - CREATE: multiplier=+1  → Effekt anwenden
    - EDIT:   multiplier=-1  (alten Effekt rueckgaengig machen)
              multiplier=+1  (neuen Effekt anwenden)
    - DELETE: multiplier=-1  → Effekt rueckgaengig machen

Beispiel fuer EDIT:
    Alte Transaktion: CHF 100 expense auf Konto A → Konto A war -100
    Jetzt geaendert auf: CHF 150 expense auf Konto A
    Schritt 1: multiplier=-1: Konto A +100 (rueckgaengig)
    Schritt 2: multiplier=+1: Konto A -150 (neuer Effekt)
    Netto: Konto A -150 (korrekt!)

=== KREDITKARTEN-SALDO vs. KONTO-SALDO ===
    Konto-Saldo (account.balance):    Wieviel Geld liegt auf dem Konto?
    Kreditkarten-Saldo (card.balance): Wieviel genutzter Kredit gibt es?

    Bei expense auf Kreditkarte: card.balance STEIGT (mehr genutzter Kredit)
    Bei income auf Kreditkarte:  card.balance SINKT  (Rueckerstattung / Ruckzahlung)

=== ARCHITEKTUR-KETTE ===
    View (transaction_view.py) → Controller (transaction_controller.py)
    → **TransactionService (du bist hier)**
    → TransactionRepository (Transaktion speichern)
    → AccountRepository / CardRepository (Saldo aktualisieren)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `transaction_service = TransactionService()`
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.domain.models import Category, Transaction
from src.utils.validators import (
    validate_date_range,
    validate_positive_amount,
    validate_transaction_type,
)


class TransactionService:
    """Service fuer Transaktionen inklusive Saldo-Updates."""

    def create_transaction(self, payload: dict) -> Transaction:
        """Erstellt eine Transaktion und wendet den Saldo-Effekt an.

        AUFRUF-KETTE:
            transaction_controller.create_transaction(payload)
            → TransactionService.create_transaction(payload)
            → validate_positive_amount(amount)
            → validate_transaction_type(type)
            → _validate_transaction_source_rule(account_id, card_id, creditcard_id)
            → _ensure_category_exists(session, category_id)
            → _ensure_source_valid(session, account_id, card_id, creditcard_id)
            → TransactionRepository.create(transaction)
            → _apply_source_effect(session, transaction, multiplier=1)
              [Saldo des Kontos/der Karte anpassen]

        RUECKGABE-KETTE:
            DB → TransactionRepository → TransactionService → transaction_controller
            → View zeigt: "Transaktion erstellt" + aktueller Kontostand

        PAYLOAD-KEYS (WAS WIRD ERWARTET?):
            - "amount" (float/str)       → Pflichtfeld, Betrag > 0
            - "type" (str)               → Pflichtfeld: "income" oder "expense"
            - "category_id" (int/str)    → Pflichtfeld
            - "account_id" (int/str)     → Genau eine der drei Quellen muss gesetzt sein:
            - "card_id" (int/str)        → entweder account_id, card_id oder creditcard_id
            - "creditcard_id" (int/str)  → (die anderen beiden muessen None/nicht vorhanden sein)
            - "date" (date/str, opt.)    → Default: heute. ISO-String "YYYY-MM-DD" wird konvertiert.
            - "note" (str, opt.)         → Freitext-Notiz

        DATUM-NORMALISIERUNG:
            NiceGUI-Datepicker liefert manchmal ISO-Strings ("2026-05-10").
            Der Service konvertiert `date.fromisoformat("2026-05-10")` → date(2026, 5, 10).

        Args:
            payload: Dictionary mit Transaktionsdaten aus Controller/UI.

        Returns:
            Die gespeicherte Transaction mit transaction_id aus der DB.

        Raises:
            ValueError: Bei ungueltigem Betrag, Typ, fehlender/mehrfacher Quelle,
                        unzureichendem Saldo oder ueberschrittenem Kreditlimit.
            KeyError: Wenn Konto/Karte/Kategorie nicht existiert.
        """
        amount = float(payload["amount"])
        transaction_type = str(payload["type"])
        transaction_date = payload.get("date") or date.today()

        # NiceGUI Datepicker liefert oft ISO-Strings ("YYYY-MM-DD").
        # Fuer die Datenbank wollen wir echte `date`-Objekte.
        if isinstance(transaction_date, str):
            transaction_date = date.fromisoformat(transaction_date)

        category_id = int(payload["category_id"])
        # Quellen aus Payload lesen (alle koennen None sein, aber genau eine muss gesetzt sein).
        account_id = payload.get("account_id")
        card_id = payload.get("card_id")
        creditcard_id = payload.get("creditcard_id")

        # Typen sicherstellen (int oder None).
        account_id = int(account_id) if account_id is not None else None
        card_id = int(card_id) if card_id is not None else None
        creditcard_id = int(creditcard_id) if creditcard_id is not None else None

        # Validierungen: Grundregeln pruefen bevor DB-Session geoeffnet wird.
        validate_positive_amount(amount)
        validate_transaction_type(transaction_type)

        # Exactly-One-Quellen-Regel: Genau eine der drei Quellen muss gesetzt sein.
        self._validate_transaction_source_rule(account_id, card_id, creditcard_id)

        with Session(engine, expire_on_commit=False) as session:
            transaction_repository = TransactionRepository(session)

            # Kategorie und Quelle existieren und sind aktiv?
            self._ensure_category_exists(session, category_id)
            self._ensure_source_valid(session, account_id, card_id, creditcard_id)

            transaction = Transaction(
                amount=amount,
                date=transaction_date,
                type=transaction_type,
                note=payload.get("note"),
                category_id=category_id,
                account_id=account_id,
                card_id=card_id,
                creditcard_id=creditcard_id,
            )
            created = transaction_repository.create(transaction)

            # Saldo-Update: multiplier=1 → Effekt anwenden.
            self._apply_source_effect(session, created, multiplier=1)
            return created

    def edit_transaction(self, transaction_id: int, payload: dict) -> Transaction:
        """Aendert eine Transaktion und korrigiert den Saldo korrekt.

        AUFRUF-KETTE:
            transaction_controller.edit_transaction(transaction_id, payload)
            → TransactionService.edit_transaction(transaction_id, payload)
            → TransactionRepository.get_by_id(transaction_id)
            → _apply_source_effect(session, old_transaction, multiplier=-1)  [Rueckgaengig]
            → Neue Werte setzen und validieren
            → TransactionRepository.save(transaction)
            → _apply_source_effect(session, updated_transaction, multiplier=1) [Neu anwenden]

        WARUM ZUERST RUECKGAENGIG MACHEN?
            Wenn wir nur den neuen Effekt anwenden wuerden, waere der Saldo falsch.
            Beispiel (CHF 100 expense → CHF 150 expense auf gleichem Konto):
            FALSCH: Konto -100 (aus create) -150 (aus edit) = -250 TOTAL
            RICHTIG: Konto +100 (rueckgaengig) -150 (neu) = -150 NETTO

        Args:
            transaction_id: Datenbank-ID der zu aendernden Transaktion.
            payload: Dictionary mit neuen Werten (koennen teilweise sein).

        Returns:
            Aktualisierte Transaction.

        Raises:
            KeyError: Wenn die Transaktion nicht existiert.
            ValueError: Bei ungueltigem Betrag/Typ/Quelle oder Saldo-Problemen.
        """
        with Session(engine, expire_on_commit=False) as session:
            transaction_repository = TransactionRepository(session)
            transaction = transaction_repository.get_by_id(transaction_id)
            if transaction is None:
                raise KeyError(f"Transaktion {transaction_id} nicht gefunden")

            # Schritt 1: Alten Effekt rueckgaengig machen (multiplier=-1).
            self._apply_source_effect(session, transaction, multiplier=-1)

            # Neue Werte aus Payload holen; falls nicht vorhanden, alte Werte behalten.
            new_amount = float(payload.get("amount", transaction.amount))
            new_type = str(payload.get("type", transaction.type))
            new_date = payload.get("date", transaction.date)
            new_category_id = int(payload.get("category_id", transaction.category_id))
            new_account_id = payload.get("account_id", transaction.account_id)
            new_card_id = payload.get("card_id", transaction.card_id)
            new_creditcard_id = payload.get("creditcard_id", transaction.creditcard_id)
            new_note = payload.get("note", transaction.note)

            new_account_id = int(new_account_id) if new_account_id is not None else None
            new_card_id = int(new_card_id) if new_card_id is not None else None
            new_creditcard_id = int(new_creditcard_id) if new_creditcard_id is not None else None

            validate_positive_amount(new_amount)
            validate_transaction_type(new_type)

            # Auch nach Aenderungen muss die Exactly-One-Regel gelten.
            self._validate_transaction_source_rule(new_account_id, new_card_id, new_creditcard_id)
            self._ensure_category_exists(session, new_category_id)
            self._ensure_source_valid(session, new_account_id, new_card_id, new_creditcard_id)

            # Felder aktualisieren.
            transaction.amount = new_amount
            transaction.type = new_type
            transaction.date = new_date
            transaction.category_id = new_category_id
            transaction.account_id = new_account_id
            transaction.card_id = new_card_id
            transaction.creditcard_id = new_creditcard_id
            transaction.note = new_note

            updated = transaction_repository.save(transaction)

            # Schritt 2: Neuen Effekt anwenden (multiplier=1).
            self._apply_source_effect(session, updated, multiplier=1)
            return updated

    def delete_transaction(self, transaction_id: int, confirm: bool) -> bool:
        """Loescht eine Transaktion und macht den Saldo-Effekt rueckgaengig.

        AUFRUF-KETTE:
            transaction_controller.delete_transaction(transaction_id, confirm=True)
            → TransactionService.delete_transaction(transaction_id, confirm=True)
            → TransactionRepository.get_by_id(transaction_id)
            → _apply_source_effect(session, transaction, multiplier=-1)  [Rueckgaengig]
            → TransactionRepository.delete(transaction)

        RUECKGABE-KETTE:
            True → transaction_controller → View zeigt: "Transaktion geloescht"

        WARUM `confirm`?
            Eine Sicherheitsabfrage. Der Controller muss explizit `confirm=True`
            uebergeben. Das verhindert versehentliche Loeschungen.

        Args:
            transaction_id: Datenbank-ID der Transaktion.
            confirm: Muss True sein, sonst wird abgebrochen.

        Returns:
            True bei Erfolg.

        Raises:
            ValueError: Wenn confirm=False.
            KeyError: Wenn die Transaktion nicht existiert.
        """
        if not confirm:
            raise ValueError("Loeschen abgebrochen: Bestaetigung erforderlich")

        with Session(engine, expire_on_commit=False) as session:
            transaction_repository = TransactionRepository(session)
            transaction = transaction_repository.get_by_id(transaction_id)
            if transaction is None:
                raise KeyError(f"Transaktion {transaction_id} nicht gefunden")

            # Effekt rueckgaengig machen, DANN loeschen.
            self._apply_source_effect(session, transaction, multiplier=-1)
            transaction_repository.delete(transaction)
            return True

    def filter_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: int | None = None,
        user_id: int | None = None,
    ) -> list[Transaction]:
        """Filtert Transaktionen fuer Listen/Tabellen in der UI.

        AUFRUF-KETTE:
            transaction_controller.filter_transactions(...)
            → TransactionService.filter_transactions(...)
            → validate_date_range(start_date, end_date)  [wenn beide gesetzt]
            → TransactionRepository.filter_transactions(...)
            → Komplexes SQL mit optionalen WHERE-Klauseln und JOINs

        RUECKGABE-KETTE:
            DB → TransactionRepository → TransactionService → transaction_controller
            → View zeigt gefilterte Tabelle

        ALLE PARAMETER SIND OPTIONAL:
            - Kein Filter → alle Transaktionen (ACHTUNG: kann sehr viele sein!)
            - user_id=X  → nur Transaktionen dieses Users (empfohlen)
            - start_date und end_date → Zeitraum
            - category_id → nur diese Kategorie

        Args:
            start_date: Optionales Startdatum (inklusive).
            end_date: Optionales Enddatum (inklusive).
            category_id: Optionaler Kategorien-Filter.
            user_id: Optionaler User-Filter (Ownership-Filter ueber alle Quellen).

        Returns:
            Liste der passenden Transaktionen (neueste zuerst sortiert).

        Raises:
            ValueError: Wenn start_date > end_date.
        """
        if start_date is not None and end_date is not None:
            validate_date_range(start_date, end_date)

        with Session(engine, expire_on_commit=False) as session:
            transaction_repository = TransactionRepository(session)
            return transaction_repository.filter_transactions(
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                user_id=user_id,
            )

    def _ensure_category_exists(self, session: Session, category_id: int) -> None:
        """Stellt sicher, dass die Kategorie-ID in der DB existiert.

        Args:
            session: Offene DB-Session.
            category_id: Kategorie-ID, die geprueft wird.

        Raises:
            KeyError: Wenn die Kategorie nicht in der DB gefunden wird.
        """
        if session.get(Category, category_id) is None:
            raise KeyError(f"Kategorie {category_id} nicht gefunden")

    def _validate_transaction_source_rule(
        self,
        account_id: int | None,
        card_id: int | None,
        creditcard_id: int | None,
    ) -> None:
        """Validiert die Exactly-One-Quellen-Regel (genau eine Quelle gesetzt).

        WARUM DIESE REGEL?
            Eine Transaktion darf nicht mehrere Quellen belasten (unklar, wo abgebucht).
            Und eine Transaktion ohne Quelle ist nicht buchbar.

        LOGIK:
            creditcard_id gesetzt + (account_id ODER card_id gesetzt) → Fehler
            creditcard_id nicht gesetzt + account_id und card_id BEIDE nicht gesetzt → Fehler
            creditcard_id nicht gesetzt + account_id und card_id BEIDE gesetzt → Fehler
            (bool(account_id) == bool(card_id) → True bei "beide gesetzt" oder "beide fehlen")

        Args:
            account_id, card_id, creditcard_id: Quell-IDs (int oder None).

        Raises:
            ValueError: Wenn die Exactly-One-Regel verletzt ist.
        """
        # Kreditkarte schliessen andere Quellen aus.
        if creditcard_id is not None and (account_id is not None or card_id is not None):
            raise ValueError(
                "Ungueltige Transaktionsquelle: Bei creditcard_id duerfen account_id und card_id nicht gesetzt sein"
            )

        if creditcard_id is None:
            has_account = account_id is not None
            has_card = card_id is not None
            # `has_account == has_card`: True wenn beide gesetzt ODER beide fehlen → Fehler.
            if has_account == has_card:
                raise ValueError(
                    "Ungueltige Transaktionsquelle: Genau eine Quelle muss gesetzt sein (account_id oder card_id)"
                )

    def _ensure_source_valid(
        self,
        session: Session,
        account_id: int | None,
        card_id: int | None,
        creditcard_id: int | None,
    ) -> None:
        """Prueft, ob die gesetzte Quelle existiert und aktiv ist.

        WARUM AKTIV-CHECK?
            Auf gesperrten Konten/Karten sollen keine neuen Transaktionen
            gebucht werden. Das verhindert, dass ein User mit einer
            gesperrten Karte trotzdem Geld ausgibt.

        Args:
            session: Offene DB-Session.
            account_id, card_id, creditcard_id: Quell-IDs (int oder None).

        Raises:
            KeyError: Wenn Konto/Karte nicht gefunden wird.
            ValueError: Wenn Konto/Karte nicht aktiv ist.
        """
        account_repository = AccountRepository(session)
        card_repository = CardRepository(session)

        if account_id is not None:
            account = account_repository.get_by_id(account_id)
            if account is None:
                raise KeyError(f"Konto {account_id} nicht gefunden")
            if account.status != "aktiv":
                raise ValueError("Transaktion nicht erlaubt: Konto ist nicht aktiv")

        if card_id is not None:
            card = card_repository.get_debit_by_id(card_id)
            if card is None:
                raise KeyError(f"Debitkarte {card_id} nicht gefunden")
            if card.status != "aktiv":
                raise ValueError("Transaktion nicht erlaubt: Debitkarte ist nicht aktiv")

        if creditcard_id is not None:
            credit_card = card_repository.get_credit_by_id(creditcard_id)
            if credit_card is None:
                raise KeyError(f"Kreditkarte {creditcard_id} nicht gefunden")
            if credit_card.status != "aktiv":
                raise ValueError("Transaktion nicht erlaubt: Kreditkarte ist nicht aktiv")

    def _apply_source_effect(
        self,
        session: Session,
        transaction: Transaction,
        multiplier: int,
    ) -> None:
        """Wendet den Geld-Effekt der Transaktion auf Konto/Debit/Kreditkarte an.

        DER MULTIPLIER-TRICK:
            multiplier = +1 → Effekt anwenden (CREATE oder zweiter Schritt von EDIT)
            multiplier = -1 → Effekt rueckgaengig machen (DELETE oder erster Schritt von EDIT)

        VORZEICHEN-REGEL:
            income:  signed_amount = +amount  (positiv = Saldo steigt)
            expense: signed_amount = -amount  (negativ = Saldo sinkt)
            delta = signed_amount * multiplier

        BEISPIEL:
            CREATE expense CHF 100 auf Konto A:
            delta = -100 * 1 = -100
            account.balance += -100 (Saldo sinkt um 100)

            DELETE expense CHF 100 auf Konto A:
            delta = -100 * -1 = +100
            account.balance += +100 (Saldo steigt um 100 = Rueckgaengig)

        KREDITKARTEN-SONDERFALL:
            Kreditkarten haben einen "genutzten Kredit" (balance), keinen Kontostand.
            expense → balance STEIGT (mehr Schulden)
            income  → balance SINKT  (Rueckerstattung)
            Die Logik ist umgekehrt zum Konto!

        Args:
            session: Offene DB-Session.
            transaction: Die Transaktion, deren Effekt angewendet/rueckgaengig gemacht wird.
            multiplier: +1 (anwenden) oder -1 (rueckgaengig machen).

        Raises:
            KeyError: Wenn referenzierte Konten/Karten fehlen.
            ValueError: Bei unzureichendem Kontosaldo oder ueberschrittenem Kreditlimit.
        """
        account_repository = AccountRepository(session)
        card_repository = CardRepository(session)

        # Vorzeichen: income = positiv (Saldo steigt), expense = negativ (Saldo sinkt).
        signed_amount = transaction.amount if transaction.type == "income" else -transaction.amount
        delta = signed_amount * multiplier

        if transaction.account_id is not None:
            # DIREKTES KONTO: Saldo direkt aendern.
            account = account_repository.get_by_id(transaction.account_id)
            if account is None:
                raise KeyError(f"Konto {transaction.account_id} nicht gefunden")
            # Saldo-Schutz: Bei Ausgaben pruefen, ob genug Geld da ist (nur beim "Anwenden").
            if transaction.type == "expense" and multiplier == 1 and account.balance < transaction.amount:
                raise ValueError("Unzureichender Kontosaldo")
            account.balance += delta
            account_repository.save(account)
            return

        if transaction.card_id is not None:
            # DEBITKARTE: Belastet immer das zugehoerige Konto der Karte.
            debit_card = card_repository.get_debit_by_id(transaction.card_id)
            if debit_card is None:
                raise KeyError(f"Debitkarte {transaction.card_id} nicht gefunden")
            # Weg: Debitkarte → account_id → Konto → Saldo aendern.
            account = account_repository.get_by_id(debit_card.account_id)
            if account is None:
                raise KeyError(f"Konto {debit_card.account_id} nicht gefunden")
            if transaction.type == "expense" and multiplier == 1 and account.balance < transaction.amount:
                raise ValueError("Unzureichender Kontosaldo")
            account.balance += delta
            account_repository.save(account)
            return

        if transaction.creditcard_id is not None:
            # KREDITKARTE: Genutzten Kredit (balance) anpassen, NICHT den Kontosaldo.
            credit_card = card_repository.get_credit_by_id(transaction.creditcard_id)
            if credit_card is None:
                raise KeyError(f"Kreditkarte {transaction.creditcard_id} nicht gefunden")

            if transaction.type == "expense":
                # Ausgaben: genutzter Kredit steigt (balance nimmt zu).
                new_balance = credit_card.balance + (transaction.amount * multiplier)
                # Limit-Pruefung: Nur beim Anwenden (nicht beim Rueckgaengig machen).
                if multiplier == 1 and new_balance > credit_card.limit:
                    raise ValueError("Kreditkartenlimit ueberschritten")
                credit_card.balance = max(0.0, new_balance)
            else:
                # Einnahmen (z.B. Rueckerstattung): genutzter Kredit sinkt (balance nimmt ab).
                credit_card.balance = max(
                    0.0,
                    credit_card.balance - (transaction.amount * multiplier),
                )

            card_repository.save_credit(credit_card)


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.transaction_service import transaction_service`
transaction_service = TransactionService()
