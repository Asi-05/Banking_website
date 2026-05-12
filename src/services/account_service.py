"""src.services.account_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der AccountService verwaltet Bankkonten:
- Konto eroeffnen (mit IBAN-Generierung)
- Konto schliessen (nur moeglich wenn Saldo = 0)
- Konten auflisten

=== KONTOTYPEN ===
Es gibt genau zwei erlaubte Kontotypen:
    - "privat": Normales Girokonto, kann mit Debitkarten verknuepft werden
    - "spar":   Sparkonto, keine Debitkarten moeglich

=== IBAN-GENERIERUNG ===
Beim Eroeffnen eines neuen Kontos wird automatisch eine Schweizer Demo-IBAN
generiert (wenn keine IBAN im Payload mitgegeben wurde). Die IBAN wird mit
der Bankleitzahl "09000" (Demo-Bank) und einer zufaelligen 12-stelligen
Kontonummer aufgebaut. Falls die generierte IBAN zufaellig schon in der DB
existiert, wird bis zu 100 Mal ein neuer Versuch unternommen.

=== KONTO SCHLIESSEN - WARUM NUR BEI SALDO 0? ===
Bankkonten koennen nicht geschlossen werden, solange noch Geld darauf ist.
Das ist eine Geschaeftsregel: Der Kunde muss das Geld zuerst abheben oder
ueberweisen. Erst wenn balance == 0.0, erlaubt der Service das Schliessen.

=== ARCHITEKTUR-KETTE ===
    View (account_view.py) → Controller (account_controller.py)
    → **AccountService (du bist hier)** → AccountRepository / UserRepository → DB

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `account_service = AccountService()`
"""

from __future__ import annotations

import random

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.user_repository import UserRepository
from src.domain.models import Account
from src.utils.validators import generate_ch_iban


class AccountService:
    """Service fuer Konto-Eroeffnung, Konto-Schliessung und Konto-Listen."""

    def open_account(self, payload: dict) -> Account:
        """Eroeffnet ein neues Konto fuer einen bestehenden User.

        AUFRUF-KETTE:
            account_controller.open_account(payload)
            → AccountService.open_account(payload)
            → UserRepository.get_by_id(user_id)          [User muss existieren]
            → _generate_iban(user_id)                     [IBAN generieren wenn nicht angegeben]
            → AccountRepository.get_by_iban(iban)         [Eindeutigkeit pruefen]
            → AccountRepository.create(account)           [Konto speichern]
            → SQL: INSERT INTO accounts (...) VALUES (...)

        RUECKGABE-KETTE:
            DB → AccountRepository → AccountService → account_controller
            → View zeigt: "Konto erfolgreich eroeffnet" + neue IBAN

        PAYLOAD-KEYS (WAS WIRD ERWARTET?):
            - "user_id" (int/str)       → Pflichtfeld: fuer welchen User
            - "account_type" (str)      → Pflichtfeld: "privat" oder "spar"
            - "iban" (str, optional)    → Falls vorhanden, wird diese IBAN verwendet
            - "balance" (float, opt.)   → Startsaldo, Default = 0.0

        WAS PASSIERT MIT DEM SALDO?
            Normalerweise startet ein Konto mit balance=0.0. Falls jedoch
            Demo-Daten einen Startsaldo benoetigen, kann dieser im Payload
            mitgegeben werden (z.B. "balance": 5000.0).

        Args:
            payload: Dictionary mit Eingaben aus Controller/UI.

        Returns:
            Das neu gespeicherte Account-Objekt (mit account_id aus der DB).

        Raises:
            ValueError: Wenn account_type nicht "privat" oder "spar" ist.
            ValueError: Wenn die IBAN bereits in der DB existiert.
            KeyError: Wenn der User mit dieser user_id nicht existiert.
        """
        # Eingaben normalisieren: Strings trimmen, Zahlen casten.
        user_id = int(payload["user_id"])
        account_type = str(payload["account_type"]).strip().lower()

        # Geschaeftsregel: Nur die zwei erlaubten Kontotypen sind gueltig.
        if account_type not in {"privat", "spar"}:
            raise ValueError("Ungueltiger Kontotyp: erlaubt sind privat und spar")

        with Session(engine) as session:
            user_repository = UserRepository(session)
            account_repository = AccountRepository(session)

            # Pruefe: Existiert der User ueberhaupt?
            user = user_repository.get_by_id(user_id)
            if user is None:
                raise KeyError(f"User {user_id} nicht gefunden")

            # IBAN aus Payload übernehmen ODER automatisch generieren.
            # Der `or`-Operator: "payload.get('iban')" gibt None zurueck wenn kein Key.
            # None ist "falsy" in Python, also wird dann _generate_iban() aufgerufen.
            iban = str(payload.get("iban") or self._generate_iban(user_id))

            # Eindeutigkeitspruefung: IBAN muss in der ganzen Datenbank einmalig sein.
            existing = account_repository.get_by_iban(iban)
            if existing is not None:
                raise ValueError("IBAN ist bereits vergeben")

            # Account-Objekt erstellen (noch nicht in DB) und dann speichern.
            account = Account(
                account_type=account_type,
                balance=float(payload.get("balance", 0.0)),
                status="aktiv",
                iban=iban,
                user_id=user_id,
            )
            return account_repository.create(account)

    def close_account(self, account_id: int) -> Account:
        """Schliesst ein Konto, aber nur wenn der Saldo exakt 0.0 ist.

        AUFRUF-KETTE:
            account_controller.close_account(account_id)
            → AccountService.close_account(account_id)
            → AccountRepository.get_by_id(account_id)    [Konto laden]
            → account.close()                             [Status auf "geschlossen" setzen]
            → AccountRepository.save(account)             [Speichern]
            → SQL: UPDATE accounts SET status='geschlossen' WHERE account_id=:id

        RUECKGABE-KETTE:
            DB → AccountRepository → AccountService → account_controller
            → View zeigt: "Konto erfolgreich geschlossen"

        WAS MACHT account.close()?
            Das ist eine Methode auf dem Account-Modell (domain/models.py).
            Sie setzt `account.status = "geschlossen"`.
            Danach kann das Konto nicht mehr fuer Transaktionen verwendet werden.

        WARUM NUR BEI SALDO 0?
            Wenn noch Geld auf dem Konto ist, wuerde das Schliessen bedeuten,
            dass das Geld "verschwindet". Das ist eine Bankregel: Vor der
            Kontoaufloesung muss das Geld abgehoben werden.

        Args:
            account_id: Datenbank-ID des zu schliessenden Kontos.

        Returns:
            Das aktualisierte Account-Objekt mit status="geschlossen".

        Raises:
            KeyError: Wenn kein Konto mit dieser ID existiert.
            ValueError: Wenn der Saldo nicht genau 0.0 ist.
        """
        with Session(engine) as session:
            account_repository = AccountRepository(session)
            account = account_repository.get_by_id(account_id)
            if account is None:
                raise KeyError(f"Konto {account_id} nicht gefunden")

            # Geschaeftsregel: Saldo muss genau 0.0 sein.
            # Strenger Vergleich mit !=, nicht < oder > (auch negative Salden blockieren).
            if account.balance != 0.0:
                raise ValueError("Konto kann nicht geschlossen werden: Balance ist nicht 0")

            account.close()
            return account_repository.save(account)

    def list_accounts(self, user_id: int) -> list[Account]:
        """Listet alle Konten eines Users (inkl. geschlossener).

        AUFRUF-KETTE:
            account_controller.list_accounts(user_id)
            → AccountService.list_accounts(user_id)
            → AccountRepository.list_by_user(user_id)
            → SQL: SELECT * FROM accounts WHERE user_id = :user_id

        RUECKGABE-KETTE:
            DB → AccountRepository → AccountService → account_controller
            → View zeigt Konten-Tabelle (IBAN, Typ, Saldo, Status)

        WARUM AUCH GESCHLOSSENE KONTEN?
            Die View kann dann selbst entscheiden, ob sie geschlossene Konten
            anzeigen will. Der Service filtert nicht vor - das ist Aufgabe der View.

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            Liste aller Account-Objekte des Users (kann leer sein).
        """
        with Session(engine) as session:
            account_repository = AccountRepository(session)
            return account_repository.list_by_user(user_id)

    def _generate_iban(self, user_id: int) -> str:
        """Generiert eine eindeutige Schweizer Demo-IBAN.

        WIE FUNKTIONIERT IBAN-GENERIERUNG?
            1. Eine 12-stellige Kontonummer wird zufaellig generiert.
            2. Mit der Demo-Bankleitzahl "09000" wird eine CH-IBAN berechnet.
               Format: CH + 2-Pruefziffern + 09000 + 12-stellige Kontonummer
            3. In der Datenbank pruefen, ob diese IBAN schon existiert.
            4. Falls ja → neuer Versuch (bis zu 100 Mal).
            5. Falls nein → IBAN zurueckgeben.

        WARUM BIS ZU 100 VERSUCHE?
            Sicherheitsnetz gegen Endlosschleife. Bei einer Demo-App mit wenigen
            Konten wird die IBAN fast immer beim ersten Versuch eindeutig sein.
            In der Realitaet haetten Banken viel laengere Kontonummern.

        Args:
            user_id: Wird aktuell nicht direkt verwendet, aber fuer spaetere
                Erweiterungen oder Logs weitergegeben.

        Returns:
            Eine IBAN (String), die aktuell nicht in der Datenbank existiert.
            Beispiel: "CH9309000123456789012"

        Raises:
            ValueError: Wenn nach 100 Versuchen keine freie IBAN gefunden wurde
                (sollte in der Praxis nie passieren).
        """
        for _ in range(100):
            # Zufaellige 12-stellige Kontonummer (mit fuehrenden Nullen aufgefuellt).
            # Beispiel: random.randint(0, 999999999999) = 42 → "000000000042"
            account_number = f"{random.randint(0, 999_999_999_999):012d}"
            iban = generate_ch_iban("09000", account_number)

            # Pro Versuch eine eigene Session oeffnen, um Konflikte zu vermeiden.
            with Session(engine) as session:
                account_repository = AccountRepository(session)
                existing = account_repository.get_by_iban(iban)
                if existing is None:
                    return iban  # Diese IBAN ist noch frei!

        raise ValueError("Konnte keine eindeutige IBAN generieren")


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.account_service import account_service`
account_service = AccountService()
