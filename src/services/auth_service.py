"""src.services.auth_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der AuthService ist zustaendig fuer den Login-Vorgang. Er ist der "Torwächter"
der App: Nur wer sich erfolgreich anmeldet, darf die App nutzen.

=== LOGIN-ABLAUF (SCHRITT FUER SCHRITT) ===
    1. User anhand der Vertragsnummer in der Datenbank suchen.
    2. Passwort ueberpruefen:
       - Neues Format: "salt$hash" → sicherer PBKDF2-Hash (via verify_password)
       - Altes Format: kein "$" → Demo-Klartext (wird direkt verglichen)
    3. Bei altem Format: Passwort automatisch auf sicheres Hash-Format upgraden
       (das nennt man "Migration on login").
    4. Nach erfolgreichem Login: Dauerauftraege ausfuehren (recurring_service).
    5. Nach erfolgreichem Login: Kreditkarten-Monatsabrechnung pruefen (billing_service).
    6. Zurueckgeben: auth_token, user_id, Infos zu ausgefuehrten Automationen.

=== WARUM PASSIEREN SCHRITTE 4 & 5 AUSSERHALB DER SESSION? ===
    Die `UserRepository`-Session wird mit `with Session(engine) as session:` geöffnet
    und nach dem Passwort-Check automatisch geschlossen (am Ende des with-Blocks).
    Dauerauftraege und Abrechnung oeffnen EIGENE Sessions.
    Das ist Absicht: Jeder Service verwaltet seine eigene DB-Verbindung.
    Es wuerde auch funktionieren, alles in einer Session zu machen, aber
    die Trennung macht den Code modularer und robuster.

=== ARCHITEKTUR-KETTE ===
    View (login_view.py) → Controller (auth_controller.py) → **AuthService (du bist hier)**
    → UserRepository → Datenbank

    Nach Login: **AuthService** → recurring_service.process_due_recurring_on_login
                **AuthService** → creditcard_billing_service.process_monthly_billing

=== RUECKGABE-KETTE ===
    DB → UserRepository → **AuthService** → Controller → View (login_view zeigt Fehler/navigiert)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `auth_service = AuthService()`
    Diese eine Instanz wird ueberall im Projekt importiert.
"""

from __future__ import annotations

import secrets
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from src.services.recurring_service import recurring_service
from src.services.transaction_service import transaction_service
from src.services.creditcard_billing_service import creditcard_billing_service
from src.utils.validators import verify_password, hash_password


class AuthService:
    """Service fuer Login und userbezogene Helper.

    Warum ein Service?
    - Repositories sollen nur "Daten holen/speichern" (Datenbankzugriff).
    - Die Login-Regeln (Passwort pruefen, Session-Token erzeugen, Folgelogik starten)
      sind Geschaeftslogik und gehoeren deshalb in den Service.
    - Controller rufen den Service auf, nicht das Repository direkt.
    """

    def login(self, contract_number: str, password: str) -> dict:
        """Meldet einen User an und verarbeitet Login-Automationen.

        AUFRUF-KETTE:
            auth_controller.login(contract_number, password)
            → AuthService.login(contract_number, password)
            → UserRepository.get_by_contract_number(contract_number)   [DB-Read]
            → verify_password(password, stored_hash)                    [Sicherheitspruefung]
            → (ggf.) session.add(user), session.commit()                [Migration: Passwort-Upgrade]
            → recurring_service.process_due_recurring_on_login(...)    [Login-Automation 1]
            → creditcard_billing_service.process_monthly_billing(...)  [Login-Automation 2]
            → dict zurueckgeben                                          [Rueckgabe]

        RUECKGABE-KETTE:
            dict mit success/token/user_id → auth_controller
            → app_state wird befuellt (user_id, auth_token)
            → login_view navigiert zum Dashboard

        WARUM "AUTH_TOKEN"?
            In echten Systemen wuerde man JWT (JSON Web Token) oder serverseitige Sessions
            verwenden. Hier verwenden wir `secrets.token_urlsafe(24)` - das erzeugt einen
            zufaelligen 32-Zeichen-String. Er wird in `app_state` gespeichert und pro
            Anfrage verglichen (vereinfachtes Session-Management fuer Demo-Zwecke).

        PASSWORT-MIGRATION (WAS IST DAS?):
            Fruehe Demo-Daten hatten Klartextpasswoerter ("password123").
            Beim ersten erfolgreichen Login wird das Passwort automatisch durch einen
            sicheren PBKDF2-Hash ersetzt. So wird die Datenbank Schritt fuer Schritt
            sicherer, ohne alle Benutzer gleichzeitig zum Passwort-Reset zu zwingen.

        Args:
            contract_number: Vertragsnummer des Users (z.B. "1001234").
            password: Passwort-Eingabe des Users (Klartext, wird NICHT gespeichert).

        Returns:
            Dictionary mit:
            - "success": True (immer True, da sonst ValueError geworfen wird)
            - "auth_token": Zufaelliger Session-Token (String)
            - "user_id": Datenbank-ID des eingeloggten Users (int)
            - "executed_recurring": Anzahl ausgefuehrter Dauerauftraege (int)
            - "billed_cards": Anzahl abgerechneter Kreditkarten (int)

        Raises:
            ValueError: Bei ungueltigem Vertragsnummer ODER falschem Passwort.
                WICHTIG: Beide Faelle geben die GLEICHE Fehlermeldung ("Ungueltige Anmeldedaten").
                Das ist Absicht: Man soll nicht erkennen koennen, ob die Vertragsnummer
                oder das Passwort falsch war (Security Best Practice).
        """
        with Session(engine) as session:
            user_repository = UserRepository(session)

            # Schritt 1: User anhand der Vertragsnummer laden.
            # Wenn kein User gefunden → ValueError (gleiche Meldung wie falsches PW).
            user = user_repository.get_by_contract_number(contract_number)
            if user is None:
                raise ValueError("Ungueltige Anmeldedaten")

            stored_hash = user.password_hash

            # Schritt 2: Passwort-Pruefung.
            # "$" im Hash = neues PBKDF2-Format ("salt$hash").
            # Kein "$" = altes Demo-Klartext-Format.
            password_ok = (
                verify_password(password, stored_hash)   # PBKDF2-Pruefung
                if "$" in stored_hash
                else stored_hash == password             # Demo-Direktvergleich
            )
            if not password_ok:
                raise ValueError("Ungueltige Anmeldedaten")

            user_id = user.user_id

            # Schritt 3: Passwort-Migration (nur wenn altes Format vorliegt).
            # Das neue Hash-Format ist viel sicherer: Es braucht 310.000 Iterationen,
            # um ein einziges Passwort zu pruefen (Brute-Force wird extrem langsam).
            if "$" not in stored_hash:
                user.password_hash = hash_password(password)
                session.add(user)
                session.commit()
        # Die Session ist jetzt geschlossen. Ab hier kein DB-Zugriff mehr ueber `session`.

        # Schritt 4 & 5: Login-Automationen.
        # Diese Services oeffnen EIGENE Sessions (deshalb koennen sie nach dem with-Block stehen).
        # `process_due_recurring_on_login`: Fuehrt faellige Dauerauftraege aus.
        # `process_monthly_billing`: Prueft, ob Kreditkarten-Abrechnung faellig ist.
        executed_recurring = recurring_service.process_due_recurring_on_login(
            user_id,
            date.today(),
        )
        transaction_service.settle_pending_transactions(user_id, date.today())
        billed_cards = creditcard_billing_service.process_monthly_billing(
            user_id,
            date.today(),
        )

        # Schritt 6: Ergebnis-Dictionary zusammenstellen.
        return {
            "success": True,
            "auth_token": secrets.token_urlsafe(24),
            "user_id": user_id,
            "executed_recurring": executed_recurring,
            "billed_cards": billed_cards,
        }

    def get_full_name(self, user_id: int) -> str:
        """Laedt den vollstaendigen Namen eines Users.

        AUFRUF-KETTE:
            (wird z.B. von dashboard_controller oder direkt von Views aufgerufen)
            → AuthService.get_full_name(user_id)
            → UserRepository.get_by_id(user_id)  [DB-Read]
            → f"{first_name} {last_name}"         [Formatierung]

        WARUM HIER UND NICHT IM CONTROLLER?
            Diese Hilfsmethode ist kurz und haengt direkt am Login-Konzept ("wer bin ich?").
            Sie koennte alternativ im UserService liegen, aber hier passt sie als
            "Login-bezogener Helper" gut.

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            "Vorname Nachname" als String.
            Leerer String "" wenn der User nicht in der DB gefunden wird.
        """
        with Session(engine) as session:
            user = UserRepository(session).get_by_id(user_id)
            return f"{user.first_name} {user.last_name}" if user else ""


# Singleton-Instanz: Diese eine Instanz wird im gesamten Projekt verwendet.
# Import-Muster: `from src.services.auth_service import auth_service`
auth_service = AuthService()
