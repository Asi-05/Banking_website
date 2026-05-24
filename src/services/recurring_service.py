"""src.services.recurring_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS IST EIN DAUERAUFTRAG (Recurring Transaction)? ===
Ein Dauerauftrag ist eine wiederkehrende Ausgabe, die in regelmaessigen
Intervallen automatisch ausgefuehrt wird.

Beispiel:
    Miete: CHF 1'200, monatlich, ab 01.06.2026, Ziel-IBAN: CH93...
    → Jeden Monat wird automatisch eine Transaktion fuer CHF 1'200 erstellt.

Felder eines Dauerauftrags:
    - amount:        Betrag (z.B. 1200.00)
    - interval:      "monthly" oder "yearly"
    - start_date:    Ab wann soll er ausgefuehrt werden?
    - end_date:      Bis wann? (optional, None = laeuft ewig)
    - last_executed: Wann wurde er zuletzt ausgefuehrt? (Zustand!)
    - target_iban:   Ziel-Konto (nur gespeichert, keine SEPA-Ueberweisung)
    - account_id:    Von welchem Konto wird abgebucht?

=== WANN WIRD EIN DAUERAUFTRAG AUSGEFUEHRT? ===
NICHT automatisch im Hintergrund (kein Cron-Job)!
Die Ausfuehrung passiert beim LOGIN des Users:
    `process_due_recurring_on_login(user_id, login_date)`
Diese Methode prueft beim Einloggen, welche Dauerauftraege faellig sind,
und fuehrt sie aus.

=== FAELLIGKEITSPRUEFUNG (Algorithmus) ===
1. `last_executed` ist gespeichert (beim Anlegen: Vorgaengerdatum des start_date).
2. `_next_due_date(last_executed, interval)` berechnet das naechste Datum.
3. Wenn next_due_date <= login_date → faellig!

Beim Anlegen wird `last_executed` auf das Vorgaengerdatum gesetzt, damit
`_next_due_date(last_executed)` = start_date ergibt. So wird der Dauerauftrag
genau ab start_date faellig.

=== MONATLICHE DATUMSBERECHNUNG (Warum nicht +30 Tage?) ===
Monate haben unterschiedlich viele Tage (28, 29, 30, 31).
"Jeden Monat am 31." gibt es im Februar nicht.
`calendar.monthrange(year, month)[1]` liefert den letzten Tag des Monats.
`min(from_date.day, ...)` stellt sicher, dass wir nie einen ungueltigen Tag haben.

Beispiel:
    31.01. + 1 Monat = min(31, 28) = 28.02. (im Schaltjahr: 29.02.)
    28.02. + 1 Monat = min(28, 31) = 28.03. (NICHT 31.03.!)

=== TEMPLATE-TRANSAKTION - WAS IST DAS? ===
Beim Anlegen eines Dauerauftrags wird zusaetzlich eine "Template-Transaktion"
gespeichert. Diese ist KEINE echte Buchung - sie bucht kein Geld ab und
aendert keinen Saldo. Sie dient als Referenz/Schablone fuer den Dauerauftrag.
Bei jeder echten Ausfuehrung wird eine NEUE, separate Transaktion erstellt.

=== ARCHITEKTUR-KETTE ===
    View (kein direktes View, via recurring_controller.py)
    → Controller (recurring_controller.py)
    → **RecurringService (du bist hier)**
    → TransactionService (eigentliche Buchung bei Ausfuehrung)
    → RecurringRepository (Dauerauftraege laden/speichern)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `recurring_service = RecurringService()`
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.recurring_repository import RecurringRepository
from src.domain.models import Category, RecurringTransaction, Transaction
from src.services.transaction_service import transaction_service
from src.utils.validators import (
    validate_iban,
    validate_positive_amount,
    validate_recurring_interval,
)


class RecurringService:
    """Fachlogik fuer Dauerauftraege."""

    def create_recurring(self, payload: dict) -> RecurringTransaction:
        """Legt einen neuen Dauerauftrag in der Datenbank an.

        AUFRUF-KETTE:
            recurring_controller.create_recurring(payload)
            → RecurringService.create_recurring(payload)
            → validate_positive_amount, validate_iban, validate_recurring_interval
            → AccountRepository.get_by_id(account_id)     [Konto existiert und aktiv?]
            → session.get(Category, category_id)           [Kategorie existiert?]
            → session.add(template_transaction) + commit   [Template-Transaktion speichern]
            → session.add(recurring) + commit              [Dauerauftrag speichern]

        RUECKGABE-KETTE:
            DB → RecurringService → recurring_controller
            → View zeigt: "Dauerauftrag angelegt"

        LAST_EXECUTED INITIALISIERUNG:
            `last_executed = _previous_due_date(start_date, interval)`
            Das ist das Datum genau 1 Intervall VOR start_date.
            Dadurch gilt: _next_due_date(last_executed) = start_date.
            Der Dauerauftrag wird also genau ab start_date faellig.

        PAYLOAD-KEYS:
            - "amount" (float/str)       → Pflichtfeld
            - "category_id" (int/str)    → Pflichtfeld
            - "account_id" (int/str)     → Pflichtfeld: Von welchem Konto abbuchen
            - "target_iban" (str)        → Pflichtfeld: An welche IBAN
            - "interval" (str)           → Pflichtfeld: "monthly" oder "yearly"
            - "start_date" (date/str)    → Pflichtfeld: Ab wann faellig?
            - "end_date" (date/str, opt) → Bis wann? None = kein Ablaufdatum

        Args:
            payload: Dictionary aus Controller/UI.

        Returns:
            Der gespeicherte RecurringTransaction (mit recurring_id aus DB).

        Raises:
            ValueError: Bei ungueltigem Betrag, IBAN, Intervall, Datum in der Vergangenheit,
                        oder inaktivem Konto.
            KeyError: Wenn Konto oder Kategorie nicht existiert.
        """
        amount = float(payload["amount"])
        category_id = int(payload["category_id"])
        account_id = int(payload["account_id"])
        target_iban = str(payload["target_iban"])
        interval = str(payload["interval"])
        start_date = payload["start_date"]
        end_date = payload.get("end_date")

        # Schnelle Validierungen vor dem DB-Zugriff.
        validate_positive_amount(amount)
        validate_iban(target_iban)
        validate_recurring_interval(interval)

        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if start_date <= date.today():
            raise ValueError("Startdatum muss mindestens morgen sein")

        with Session(engine) as session:
            account_repository = AccountRepository(session)
            account = account_repository.get_by_id(account_id)
            if account is None:
                raise KeyError(f"Konto {account_id} nicht gefunden")
            if account.status != "aktiv":
                raise ValueError(f"Konto {account_id} ist nicht aktiv und kann nicht verwendet werden")

            category = session.get(Category, category_id)
            if category is None:
                raise KeyError(f"Kategorie {category_id} nicht gefunden")

            # Template-Transaktion: Repraesentiert die naechste geplante Ausfuehrung.
            # is_settled=False → erscheint in "Geplante Zahlungen", nicht in "Bewegungen".
            # Das Datum zeigt immer die naechste faellige Ausfuehrung.
            template_transaction = Transaction(
                amount=amount,
                date=start_date,
                type="expense",
                note=f"Dauerauftrag {category.name}",
                category_id=category_id,
                account_id=account_id,
                is_settled=False,
            )
            session.add(template_transaction)
            session.commit()
            session.refresh(template_transaction)

            # Dauerauftrag anlegen.
            # last_executed = Vorgaengerdatum → next_due_date(last_executed) = start_date.
            recurring = RecurringTransaction(
                amount=amount,
                target_iban=target_iban,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                last_executed=self._previous_due_date(start_date, interval),
                account_id=account_id,
                category_id=category_id,
                transaction_id=template_transaction.transaction_id,
            )
            session.add(recurring)
            session.commit()
            session.refresh(recurring)
            return recurring

    def process_due_recurring_on_login(self, user_id: int, login_date: date) -> int:
        """Fuehrt faellige Dauerauftraege beim Login aus.

        AUFRUF-KETTE (wird von AuthService.login() aufgerufen!):
            auth_service.login(...)
            → recurring_service.process_due_recurring_on_login(user_id, login_date)
            → RecurringRepository.list_due_by_user(user_id, login_date)  [Kandidaten laden]
            → _is_due(recurring, login_date)                              [Faelligkeitspruefung]
            → TransactionService.create_transaction(...)                   [Buchung ausfuehren]
            → RecurringRepository.save(reloaded)                          [last_executed aktualisieren]

        RUECKGABE-KETTE:
            int (Anzahl ausgefuehrter Dauerauftraege) → auth_service.login
            → dict["executed_recurring"] → auth_controller → View
              (View kann z.B. anzeigen: "2 Dauerauftraege wurden ausgefuehrt")

        WARUM MEHRERE SESSIONS?
            - Phase 1: Kandidaten laden (eine Session, wird nach Lesen geschlossen).
            - Phase 2: Pro Dauerauftrag:
              - TransactionService.create_transaction() oeffnet eigene Session.
              - last_executed-Update in frischer Session (vermeidet "detached object"-Fehler).
            Diese Trennung ist bewusst: jeder Service verwaltet seine eigene DB-Verbindung.

        ROBUSTHEIT (try/except):
            Wenn ein einzelner Dauerauftrag fehlschlaegt (z.B. zu wenig Saldo),
            wird der Fehler abgefangen und die anderen Dauerauftraege werden trotzdem
            ausgefuehrt. So blockiert ein Problem nicht alle anderen Buchungen.

        Args:
            user_id: ID des eingeloggten Users.
            login_date: Referenzdatum fuer Faelligkeitspruefung (normalerweise heute).

        Returns:
            Anzahl erfolgreich ausgefuehrter Dauerauftraege.
        """
        executed = 0
        with Session(engine) as session:
            recurring_repository = RecurringRepository(session)
            # DB-Query: Kandidaten, die start_date <= login_date haben.
            # Die genaue Faelligkeitspruefung (Intervall) passiert danach im Service.
            due_candidates = recurring_repository.list_due_by_user(
                user_id=user_id,
                reference_date=login_date,
            )

        for recurring in due_candidates:
            # Enddatum-Pruefung: Nach Ablaufdatum nie mehr ausfuehren.
            if recurring.end_date is not None and recurring.end_date < login_date:
                continue

            # Intervall-Pruefung: Ist der naechste Termin schon erreicht?
            if not self._is_due(recurring, login_date):
                continue

            try:
                # Kategoriename fuer die Transaktion-Notiz ermitteln.
                with Session(engine) as cat_session:
                    cat = cat_session.get(Category, recurring.category_id)
                    cat_name = cat.name if cat is not None else str(recurring.category_id)

                # Buchung ausfuehren: TransactionService bucht Geld ab und aktualisiert Saldo.
                transaction_service.create_transaction(
                    {
                        "amount": recurring.amount,
                        "type": "expense",
                        "date": login_date,
                        "category_id": recurring.category_id,
                        "account_id": recurring.account_id,
                        "note": f"Dauerauftrag {cat_name}",
                    }
                )
            except (ValueError, KeyError):
                # Fehler (z.B. zu wenig Saldo) → dieser Dauerauftrag wird uebersprungen,
                # aber die anderen werden weiterhin geprueft.
                continue

            next_due = self._next_due_date(recurring.last_executed, recurring.interval)
            with Session(engine) as session:
                recurring_repository = RecurringRepository(session)
                reloaded = recurring_repository.get_by_id(recurring.recurring_id)
                if reloaded is not None:
                    reloaded.last_executed = next_due
                    recurring_repository.save(reloaded)

                    # Template-Transaktion auf naechstes Ausfuehrungsdatum setzen,
                    # damit sie in "Geplante Zahlungen" mit dem richtigen Datum erscheint.
                    if reloaded.transaction_id:
                        template = session.get(Transaction, reloaded.transaction_id)
                        if template is not None:
                            template.date = self._next_due_date(login_date, recurring.interval)
                            template.is_settled = False
                            session.add(template)
                            session.commit()
            executed += 1

        # Alle Templates auf is_settled=False und korrektes Datum sicherstellen.
        # Noetig fuer bestehende Dauerauftraege, die vor dieser Aenderung angelegt wurden.
        with Session(engine) as session:
            recurring_repository = RecurringRepository(session)
            all_recurring = recurring_repository.list_by_user(user_id)
            for rec in all_recurring:
                if rec.transaction_id is None:
                    continue
                template = session.get(Transaction, rec.transaction_id)
                if template is None:
                    continue
                next_due = self._next_due_date(rec.last_executed, rec.interval)
                if template.is_settled is True or template.date != next_due:
                    template.is_settled = False
                    template.date = next_due
                    session.add(template)
            session.commit()

        return executed

    def list_recurring(self, user_id: int) -> list[RecurringTransaction]:
        """Listet alle Dauerauftraege eines Users.

        AUFRUF-KETTE:
            recurring_controller.list_recurring(user_id)
            → RecurringService.list_recurring(user_id)
            → RecurringRepository.list_by_user(user_id)
            → SQL: SELECT rt.* FROM recurring_transactions rt
                   JOIN accounts a ON a.account_id = rt.account_id
                   WHERE a.user_id = :user_id

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            Liste aller RecurringTransaction-Objekte des Users.
        """
        with Session(engine) as session:
            recurring_repository = RecurringRepository(session)
            return recurring_repository.list_by_user(user_id)

    def update_recurring(self, recurring_id: int, payload: dict) -> RecurringTransaction:
        """Aktualisiert Felder eines Dauerauftrags (Partial Update).

        AUFRUF-KETTE:
            recurring_controller.update_recurring(recurring_id, payload)
            → RecurringService.update_recurring(recurring_id, payload)
            → RecurringRepository.get_by_id(recurring_id)
            → Felder aus payload setzen (nur vorhandene Keys werden veraendert)
            → RecurringRepository.save(recurring)

        PARTIAL UPDATE - WIE FUNKTIONIERT DAS?
            Nur Keys, die im payload-Dict vorhanden sind, werden veraendert.
            `if "amount" in payload:` → nur wenn "amount" mitgesendet wurde.
            Das erlaubt Formulare, die nur bestimmte Felder zeigen.

        Args:
            recurring_id: Datenbank-ID des Dauerauftrags.
            payload: Dictionary mit zu aendernden Feldern.

        Returns:
            Aktualisierter RecurringTransaction.

        Raises:
            KeyError: Wenn der Dauerauftrag nicht existiert.
            ValueError: Bei ungueltigem Betrag, IBAN oder Intervall.
        """
        with Session(engine) as session:
            recurring_repository = RecurringRepository(session)
            recurring = recurring_repository.get_by_id(recurring_id)
            if recurring is None:
                raise KeyError(f"Dauerauftrag {recurring_id} nicht gefunden")

            if "amount" in payload:
                amount = float(payload["amount"])
                validate_positive_amount(amount)
                recurring.amount = amount

            if "interval" in payload:
                interval = str(payload["interval"])
                validate_recurring_interval(interval)
                recurring.interval = interval

            if "target_iban" in payload:
                target_iban = str(payload["target_iban"])
                validate_iban(target_iban)
                recurring.target_iban = target_iban

            if "end_date" in payload:
                end_date_val = payload["end_date"]
                # NiceGUI kann ISO-Strings liefern; normalisieren auf date | None.
                if isinstance(end_date_val, str):
                    end_date_val = date.fromisoformat(end_date_val) if end_date_val else None
                recurring.end_date = end_date_val

            if "category_id" in payload and payload["category_id"] is not None:
                recurring.category_id = int(payload["category_id"])

            if "account_id" in payload and payload["account_id"] is not None:
                recurring.account_id = int(payload["account_id"])

            return recurring_repository.save(recurring)

    def get_by_id(self, recurring_id: int) -> RecurringTransaction | None:
        """Laedt einen einzelnen Dauerauftrag per ID.

        Returns:
            RecurringTransaction oder None wenn nicht gefunden.
        """
        with Session(engine) as session:
            recurring_repository = RecurringRepository(session)
            return recurring_repository.get_by_id(recurring_id)

    def next_execution_date(self, last_executed: date, interval: str) -> date:
        """Berechnet das naechste Ausfuehrungsdatum (oeffentlicher Helper fuer Controller/Views).

        Args:
            last_executed: Letztes Ausfuehrungsdatum.
            interval: "monthly" oder "yearly".

        Returns:
            Naechstes faelliges Datum.
        """
        return self._next_due_date(last_executed, interval)

    def skip_next_execution(self, transaction_id: int) -> bool:
        """Ueberspringt die naechste Ausfuehrung eines Dauerauftrags (eine Periode).

        Aufgerufen wenn der User in "Geplante Zahlungen" auf "Stornieren" klickt.
        Nur DIESE eine Ausfuehrung wird uebersprungen; der Dauerauftrag bleibt aktiv.

        Args:
            transaction_id: transaction_id der Template-Transaktion.

        Returns:
            True wenn es eine Template-Transaktion war (und uebersprungen wurde).
            False wenn es KEINE Template-Transaktion ist (Aufrufer soll normal loeschen).
        """
        from sqlalchemy.orm import Session as _Session
        from sqlmodel import select as _select
        from src.domain.models import RecurringTransaction

        with Session(engine) as session:
            recurring = session.exec(
                _select(RecurringTransaction).where(
                    RecurringTransaction.transaction_id == transaction_id
                )
            ).first()
            if recurring is None:
                return False

            # last_executed auf aktuelles next_due setzen → naechste Faelligkeit rueckt vor.
            current_next_due = self._next_due_date(recurring.last_executed, recurring.interval)
            recurring.last_executed = current_next_due
            session.add(recurring)

            # Template-Datum auf den naechsten Termin setzen.
            template = session.get(Transaction, transaction_id)
            if template is not None:
                template.date = self._next_due_date(current_next_due, recurring.interval)
                template.is_settled = False
                session.add(template)

            session.commit()
            return True

    def delete_recurring(self, recurring_id: int) -> None:
        """Loescht einen Dauerauftrag und die verknuepfte Template-Transaktion.

        AUFRUF-KETTE:
            recurring_controller.delete_recurring(recurring_id)
            → RecurringService.delete_recurring(recurring_id)
            → RecurringRepository.get_by_id(recurring_id)          [Existenzcheck]
            → RecurringRepository.delete(recurring_id)              [Dauerauftrag loeschen]
            → TransactionRepository.delete(template_transaction)    [Template loeschen]

        WARUM AUCH DIE TEMPLATE-TRANSAKTION LOESCHEN?
            Die Template-Transaktion hat keinen eigenstaendigen Zweck mehr,
            wenn der Dauerauftrag geloescht wird. Sie wuerde als "verwaiste"
            Buchung in der DB bleiben.

        Args:
            recurring_id: Datenbank-ID des Dauerauftrags.

        Raises:
            KeyError: Wenn der Dauerauftrag nicht existiert.
        """
        with Session(engine) as session:
            recurring_repository = RecurringRepository(session)
            recurring = recurring_repository.get_by_id(recurring_id)
            if recurring is None:
                raise KeyError(f"Dauerauftrag {recurring_id} nicht gefunden")

            transaction_id = recurring.transaction_id

            # Zuerst Dauerauftrag loeschen, dann Template-Transaktion.
            recurring_repository.delete(recurring_id)

            if transaction_id:
                from src.data_access.repositories.transaction_repository import TransactionRepository
                from src.domain.models import Transaction
                transaction_repository = TransactionRepository(session)
                transaction = session.get(Transaction, transaction_id)
                if transaction is not None:
                    transaction_repository.delete(transaction)

    def _is_due(self, recurring: RecurringTransaction, reference_date: date) -> bool:
        """Prueft, ob ein Dauerauftrag zum Referenzdatum faellig ist.

        LOGIK:
            1. Vor dem Startdatum → niemals faellig.
            2. next_due_date(last_executed, interval) berechnen.
            3. Wenn next_due_date <= reference_date → faellig!

        Args:
            recurring: Der zu pruefende Dauerauftrag.
            reference_date: Das Datum, gegen das geprueft wird.

        Returns:
            True wenn faellig, False wenn nicht.
        """
        if reference_date < recurring.start_date:
            return False
        next_due = self._next_due_date(recurring.last_executed, recurring.interval)
        return next_due <= reference_date

    def _next_due_date(self, from_date: date, interval: str) -> date:
        """Berechnet das naechste Faelligkeitsdatum ab `from_date`.

        WARUM NICHT EINFACH +30 TAGE?
            Monate haben verschiedene Laengen. "Jeden Monat" muss bedeuten:
            gleicher Tag im naechsten Monat, geclampt auf den letzten Tag.

        BEISPIELE:
            31.01.2026 + monthly = min(31, 28) = 28.02.2026
            28.02.2026 + monthly = min(28, 31) = 28.03.2026
            31.12.2025 + monthly = 31.01.2026

        Args:
            from_date: Ausgangsdatum (normalerweise last_executed).
            interval: "monthly" oder "yearly".

        Returns:
            Naechstes faelliges Datum.
        """
        if interval == "monthly":
            # Naechsten Monat berechnen (mit Jahr-Uebertrag bei Dezember).
            year = from_date.year + (from_date.month // 12)
            month = (from_date.month % 12) + 1
            # Clampen: Falls Tag > Monatsletzter (z.B. 31. in Monat mit 30 Tagen).
            day = min(from_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
        if interval == "yearly":
            year = from_date.year + 1
            day = min(from_date.day, calendar.monthrange(year, from_date.month)[1])
            return date(year, from_date.month, day)
        # Defensiver Fallback (interval wird vorher validiert).
        return from_date

    def _previous_due_date(self, from_date: date, interval: str) -> date:
        """Berechnet das direkte Vorgaengerdatum zum Intervall.

        WOZU WIRD DAS GEBRAUCHT?
            Beim Anlegen eines Dauerauftrags wird `last_executed` auf den
            Vorgaenger des start_date gesetzt. Dadurch ergibt
            `_next_due_date(last_executed)` = start_date.
            Der Dauerauftrag ist also genau ab start_date faellig.

        BEISPIEL (monthly, start_date = 01.06.2026):
            _previous_due_date(2026-06-01) = 2026-05-01
            _next_due_date(2026-05-01) = 2026-06-01 ✓

        Args:
            from_date: Das Startdatum des Dauerauftrags.
            interval: "monthly" oder "yearly".

        Returns:
            Datum genau 1 Intervall vor from_date.
        """
        if interval == "monthly":
            year = from_date.year
            month = from_date.month - 1
            if month == 0:
                month = 12
                year -= 1
            day = min(from_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
        if interval == "yearly":
            year = from_date.year - 1
            day = min(from_date.day, calendar.monthrange(year, from_date.month)[1])
            return date(year, from_date.month, day)
        return from_date


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.recurring_service import recurring_service`
recurring_service = RecurringService()
