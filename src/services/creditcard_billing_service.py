"""src.services.creditcard_billing_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der CreditCardBillingService fuehrt die monatliche Kreditkarten-Abrechnung durch.

=== WAS IST EINE KREDITKARTEN-ABRECHNUNG? ===
Kreditkarten buchen im Laufe des Monats Ausgaben auf "Kredit" (Schulden):
    - `CreditCard.balance` steigt bei jeder Ausgabe an (genutzter Kredit)
    - `CreditCard.limit` ist der maximale Rahmen

Am Monatsende (oder beim Login) wird abgerechnet:
    1. `balance` (genutzter Kredit) wird vom Abrechnungskonto (`billing_account_id`) abgebucht
    2. `balance` wird auf 0.0 zurueckgesetzt
    3. `last_billed` wird auf das Abrechnungsdatum gesetzt

WICHTIG: `balance` bei Kreditkarten = SCHULDEN (genutzter Kredit)
         `balance` bei Konten       = GUTHABEN (vorhandenes Geld)
         Das ist genau umgekehrt!

=== WANN WIRD ABGERECHNET? ===
Nicht automatisch - sondern beim Login:
    auth_service.login() → creditcard_billing_service.process_monthly_billing(user_id, today)

Pro Monat nur EINMAL pro Kreditkarte (last_billed-Pruefung).

=== DEMO-FUNKTION: seed_historical_billing_demo() ===
Erzeugt fiktive historische Kreditkartenumsaetze fuer vergangene Monate
und rechnet sie dann ab. So sieht das System aus, als ob es schon Monate
lang benutzt worden waere - nuetzlich fuer Vorfuehrungen und Tests.

=== ARCHITEKTUR-KETTE ===
    auth_service.login() → **CreditCardBillingService (du bist hier)**
    → TransactionService (eigentliche Abbuchung vom Abrechnungskonto)
    → CardRepository (Kreditkarte laden/aktualisieren)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `creditcard_billing_service = CreditCardBillingService()`
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import CreditCard
from src.services.transaction_service import transaction_service


class CreditCardBillingService:
    """Fachlogik fuer monatliche Kreditkarten-Abrechnungen."""

    def process_monthly_billing(self, user_id: int, reference_date: date) -> int:
        """Fuehrt Monatsabrechnungen fuer alle Kreditkarten eines Users aus.

        AUFRUF-KETTE (wird von AuthService.login() aufgerufen!):
            auth_service.login(...)
            → creditcard_billing_service.process_monthly_billing(user_id, today)
            → CardRepository.list_credit_by_user(user_id)   [Alle Kreditkarten laden]
            → _is_billing_due(card, reference_date)          [Schon diesen Monat abgerechnet?]
            → CategoryRepository.list_all()                  [Kategorie fuer Buchung]
            → TransactionService.create_transaction(...)     [Abbuchung vom Abrechnungskonto]
            → CardRepository.save_credit(reloaded)           [balance=0, last_billed=heute]

        RUECKGABE-KETTE:
            int (Anzahl abgerechneter Karten) → auth_service.login
            → dict["billed_cards"] → auth_controller → View

        ABRECHNUNGS-BEDINGUNGEN (ALLE muessen erfuellt sein):
            1. _is_billing_due: In diesem Monat noch nicht abgerechnet
            2. status == "aktiv": Gesperrte/ersetzte Karten werden nicht abgerechnet
            3. balance > 0: Kein offener Betrag → nichts zu bezahlen
            4. billing_account_id != None: Abrechnungskonto muss gesetzt sein

        WAS PASSIERT BEI DER ABRECHNUNG?
            1. Transaktion (expense) auf dem Abrechnungskonto:
               "Zahlung Kreditkarte" in Hoehe von credit_card.balance
            2. credit_card.balance = 0.0 (Schulden ausgeglichen)
            3. credit_card.last_billed = reference_date (Abrechnung markiert)

        ROBUSTHEIT:
            Bei Fehler einer einzelnen Karte (z.B. Saldo zu tief) wird der
            Fehler abgefangen und die anderen Karten werden trotzdem abgerechnet.

        Args:
            user_id: Datenbank-ID des Users.
            reference_date: Stichtag (normalerweise heute beim Login).

        Returns:
            Anzahl erfolgreich abgerechneter Kreditkarten.
        """
        processed = 0

        with Session(engine) as session:
            card_repository = CardRepository(session)
            credit_cards = card_repository.list_credit_by_user(user_id)

        for credit_card in credit_cards:
            # Schritt 1: Schon diesen Monat abgerechnet?
            if not self._is_billing_due(credit_card, reference_date):
                continue
            # Schritt 2: Karte muss aktiv sein.
            if credit_card.status != "aktiv":
                continue
            # Schritt 3: Offener Betrag vorhanden?
            if credit_card.balance <= 0.0:
                continue
            # Schritt 4: Abrechnungskonto gesetzt?
            if credit_card.billing_account_id is None:
                continue

            try:
                with Session(engine) as session:
                    category_repository = CategoryRepository(session)
                    categories = category_repository.list_all()
                    # Letzte Kategorie als Fallback fuer die Buchungskategorie.
                    miscellaneous_category = categories[-1] if categories else None
                    if miscellaneous_category is None:
                        continue

                    # Abbuchung vom Abrechnungskonto: TransactionService prueft Saldo.
                    transaction_service.create_transaction({
                        "amount": credit_card.balance,
                        "type": "expense",
                        "date": reference_date,
                        "category_id": miscellaneous_category.category_id,
                        "account_id": credit_card.billing_account_id,
                        "note": "Zahlung Kreditkarte",
                    })
            except (ValueError, KeyError):
                # Fehler (z.B. unzureichender Saldo) → Karte ueberspringen.
                continue

            # Kreditkarte nach erfolgreicher Abrechnung aktualisieren.
            with Session(engine) as session:
                card_repository = CardRepository(session)
                # Frische Session: neu laden, damit ORM-Objekt korrekt verwaltet wird.
                reloaded = card_repository.get_credit_by_id(credit_card.creditcard_id)
                if reloaded is not None:
                    reloaded.balance = 0.0            # Schulden beglichen.
                    reloaded.last_billed = reference_date  # Monats-Marker setzen.
                    card_repository.save_credit(reloaded)

            processed += 1

        return processed

    def seed_historical_billing_demo(
        self,
        user_id: int,
        months_back: int = 3,
        transactions_per_month: int = 3,
        reference_date: date | None = None,
    ) -> dict:
        """Erzeugt Demo-Umsaetze fuer vergangene Monate und rechnet sie ab.

        WOZU WIRD DAS GEBRAUCHT?
            Fuer Demos/Vorfuehrungen soll die App aussehen, als ob sie schon
            mehrere Monate benutzt worden waere. Diese Funktion erstellt
            fiktive Kreditkartenumsaetze fuer die letzten N Monate und rechnet
            sie dann ab, sodass Diagramme und Auswertungen interessante Daten zeigen.

        ABLAUF:
            1. Aktive Kreditkarten des Users laden.
            2. Falls kein Abrechnungskonto gesetzt: Demo-Konto setzen.
            3. Pro vergangenen Monat (von aeltestem zu juengstem):
               a. Fiktive Umsaetze erstellen (bauen balance auf).
               b. Am Monatsende abrechnen (process_monthly_billing).

        WARUM VON ALT NACH NEU?
            Die Umsaetze muessen chronologisch sein. Wenn wir zuerst den
            neuesten Monat abrechnen wuerden, waere die Reihenfolge falsch.

        Args:
            user_id: Besitzer der Kreditkarten.
            months_back: Wie viele Monate zurueck? (>= 1)
            transactions_per_month: Wie viele Demo-Umsaetze pro Monat? (>= 1)
            reference_date: Basisdatum (Default: heute).

        Returns:
            Dict mit Zusammenfassung: created_transactions, processed_billings, etc.

        Raises:
            ValueError: Wenn keine aktive Kreditkarte oder kein Privatkonto vorhanden.
        """
        if months_back < 1:
            raise ValueError("months_back muss mindestens 1 sein")
        if transactions_per_month < 1:
            raise ValueError("transactions_per_month muss mindestens 1 sein")

        reference_date = reference_date or date.today()

        with Session(engine) as session:
            card_repository = CardRepository(session)
            account_repository = AccountRepository(session)
            category_repository = CategoryRepository(session)

            # Nur aktive Kreditkarten fuer die Demo.
            credit_cards = [
                card
                for card in card_repository.list_credit_by_user(user_id)
                if card.status == "aktiv"
            ]
            if not credit_cards:
                raise ValueError("Keine aktive Kreditkarte fuer Demo-Abrechnung gefunden")

            category_id = self._resolve_demo_category_id(category_repository)

            # Abrechnungskonto benoetigt: erstes aktives Privatkonto nehmen.
            user_accounts = account_repository.list_by_user(user_id)
            active_private_account = next(
                (
                    account
                    for account in user_accounts
                    if account.account_type == "privat" and account.status == "aktiv"
                ),
                None,
            )
            if active_private_account is None:
                raise ValueError("Kein aktives Privatkonto fuer Kreditkarten-Abrechnung gefunden")

            updated_cards = 0
            for card in credit_cards:
                if card.billing_account_id is None:
                    # Demo: Abrechnungskonto automatisch setzen.
                    card.billing_account_id = active_private_account.account_id
                    card_repository.save_credit(card)
                    updated_cards += 1

        created_transactions = 0
        processed_billings = 0

        # Monate chronologisch von aeltestem zu juengstem verarbeiten.
        for offset in range(months_back, 0, -1):
            month_start = self._first_day_of_shifted_month(reference_date, -offset)
            month_end = self._last_day_of_month(month_start.year, month_start.month)

            with Session(engine) as session:
                card_repository = CardRepository(session)
                monthly_cards = [
                    card
                    for card in card_repository.list_credit_by_user(user_id)
                    if card.status == "aktiv" and card.billing_account_id is not None
                ]

            for card in monthly_cards:
                for tx_index in range(transactions_per_month):
                    # Umsaetze gleichmaessig im Monat verteilen (nicht am letzten Tag).
                    day = min(3 + (tx_index * 7), month_end.day - 1)
                    tx_date = date(month_start.year, month_start.month, max(1, day))
                    amount = 25.0 + float((offset * 10) + (tx_index * 5))
                    transaction_service.create_transaction(
                        {
                            "amount": amount,
                            "type": "expense",
                            "date": tx_date,
                            "category_id": category_id,
                            "creditcard_id": card.creditcard_id,
                            "note": (
                                f"DEMO Kreditkartenumsatz {month_start.year}-{month_start.month:02d}"
                            ),
                        }
                    )
                    created_transactions += 1

            # Am Monatsende abrechnen.
            processed_billings += self.process_monthly_billing(user_id, month_end)

        return {
            "user_id": user_id,
            "months_back": months_back,
            "transactions_per_month": transactions_per_month,
            "created_transactions": created_transactions,
            "processed_billings": processed_billings,
            "updated_cards_with_billing_account": updated_cards,
        }

    def _is_billing_due(self, credit_card: CreditCard, reference_date: date) -> bool:
        """Prueft, ob fuer diese Karte im aktuellen Monat noch nicht abgerechnet wurde.

        LOGIK:
            last_billed == None     → noch nie abgerechnet → faellig!
            last_billed.month != reference_date.month → anderen Monat → faellig!
            last_billed.year  != reference_date.year  → anderes Jahr  → faellig!
            Sonst: gleicher Monat/Jahr → bereits abgerechnet → nicht faellig.

        Args:
            credit_card: Die zu pruefende Kreditkarte.
            reference_date: Stichtag (Monat/Jahr zaehlen).

        Returns:
            True wenn noch nicht abgerechnet (faellig), False wenn schon erledigt.
        """
        if credit_card.last_billed is None:
            return True
        if credit_card.last_billed.month != reference_date.month:
            return True
        if credit_card.last_billed.year != reference_date.year:
            return True
        return False

    def _resolve_demo_category_id(self, category_repository: CategoryRepository) -> int:
        """Waehlt eine Kategorie fuer Demo-Buchungen aus (bevorzugt "Freizeit").

        Strategie: "Freizeit" ist gut sichtbar in der UI. Falls nicht vorhanden,
        nehmen wir die erste verfuegbare Kategorie.

        Returns:
            category_id (int).

        Raises:
            ValueError: Wenn keine Kategorien vorhanden oder category_id fehlt.
        """
        categories = category_repository.list_all()
        if not categories:
            raise ValueError("Keine Kategorien vorhanden")
        preferred = next((c for c in categories if c.name.lower() == "freizeit"), None)
        selected = preferred or categories[0]
        if selected.category_id is None:
            raise ValueError("Kategorie-ID nicht verfuegbar")
        return selected.category_id

    def _first_day_of_shifted_month(self, base_date: date, month_shift: int) -> date:
        """Gibt den 1. Tag des um `month_shift` verschobenen Monats zurueck.

        Beispiel:
            base_date = 2026-05-11, month_shift = -1 → 2026-04-01
            base_date = 2026-05-11, month_shift = -3 → 2026-02-01

        Args:
            base_date: Ausgangsdatum.
            month_shift: Negative Zahl fuer Vergangenheit (z.B. -1 = Vormonat).

        Returns:
            Erster Tag des Zielmonats.
        """
        # total_month: absoluter Monatszaehler (z.B. 2026*12 + 4 = Mai 2026 = Monat 24316)
        total_month = (base_date.year * 12) + (base_date.month - 1) + month_shift
        year = total_month // 12
        month = (total_month % 12) + 1
        return date(year, month, 1)

    def _last_day_of_month(self, year: int, month: int) -> date:
        """Gibt den letzten Tag eines Monats zurueck (z.B. 28/29/30/31).

        `calendar.monthrange(year, month)` gibt (Wochentag-des-1., Anzahl-Tage) zurueck.
        Index [1] = Anzahl Tage im Monat.

        Args:
            year: Jahr.
            month: Monat (1-12).

        Returns:
            Letzter Tag des Monats als date.
        """
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.creditcard_billing_service import creditcard_billing_service`
creditcard_billing_service = CreditCardBillingService()
