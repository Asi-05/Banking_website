"""Authentifizierung und Login-Nebenwirkungen (Service-Schicht).

Dieses Modul enthält die Login-Logik der BetterBank. Es gehört zur Service-
Schicht, weil hier Regeln und Abläufe ("Was passiert beim Login?") umgesetzt
werden. Der Service nutzt `UserRepository` für DB-Zugriffe und ruft beim Login
zusätzlich Services für Daueraufträge und Kreditkarten-Abrechnung auf.
"""

from __future__ import annotations

import secrets
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from src.services.recurring_service import recurring_service
from src.services.creditcard_billing_service import creditcard_billing_service
from src.utils.validators import verify_password, hash_password


class AuthService:
    """Service für Login und userbezogene Helper.

    Warum ein Service?
    - Repositories sollen nur "Daten holen/speichern".
    - Die Login-Regeln (Passwort prüfen, Session-Token erzeugen, Folgelogik starten)
      sind Geschäftslogik und gehören deshalb hierher.
    """
    def login(self, contract_number: str, password: str) -> dict:
        """Meldet einen User an und verarbeitet Login-Automationen.

        Ablauf (vereinfacht):
        1) User über Vertragsnummer laden
        2) Passwort prüfen (bevorzugt über PBKDF2-Hash)
        3) Falls alte Dummy-Passwörter in der DB liegen: auf echten Hash migrieren
        4) Nach erfolgreichem Login: fällige Daueraufträge ausführen und ggf.
           Kreditkarten-Monatsabrechnung starten

        Args:
            contract_number: Vertragsnummer des Users.
            password: Passwort-Eingabe (Klartext).

        Returns:
            Ein Dictionary mit Login-Ergebnis, Token und Zusatzinfos.

        Raises:
            ValueError: Bei ungültigen Anmeldedaten.
        """
        with Session(engine) as session:
            user_repository = UserRepository(session)
            # User anhand der Vertragsnummer suchen.
            user = user_repository.get_by_contract_number(contract_number)
            if user is None:
                raise ValueError("Ungueltige Anmeldedaten")

            stored_hash = user.password_hash
            # Passwort-Prüfung:
            # - Wenn `stored_hash` das Format "salt$hash" hat, ist es ein PBKDF2-Hash.
            # - Sonst ist es vermutlich ein altes Demo-/Legacy-Format.
            password_ok = (
                verify_password(password, stored_hash)
                if "$" in stored_hash
                else stored_hash == password
            )
            if not password_ok:
                raise ValueError("Ungueltige Anmeldedaten")

            user_id = user.user_id
            # Migration: Falls noch ein altes Klartext-/Dummy-Passwort gespeichert ist,
            # ersetzen wir es beim erfolgreichen Login durch einen echten Hash.
            # Vorteil: ab dem nächsten Login ist die Speicherung deutlich sicherer.
            if "$" not in stored_hash:
                user.password_hash = hash_password(password)
                session.add(user)
                session.commit()

        # Nach dem Login werden Automationen ausgelöst.
        # Diese Services verwalten ihre eigenen DB-Sessions, daher passiert das
        # bewusst außerhalb des `with Session(...)` Blocks oben.
        executed_recurring = recurring_service.process_due_recurring_on_login(
            user_id,
            date.today(),
        )
        billed_cards = creditcard_billing_service.process_monthly_billing(
            user_id,
            date.today(),
        )
        return {
            "success": True,
            # Token ist hier ein einfacher, zufälliger String für die UI-Session.
            # (In echten Systemen wäre das oft ein JWT oder ein serverseitiges Session-Objekt.)
            "auth_token": secrets.token_urlsafe(24),
            "user_id": user_id,
            "executed_recurring": executed_recurring,
            "billed_cards": billed_cards,
        }

    def get_full_name(self, user_id: int) -> str:
        """Lädt den vollständigen Namen eines Users.

        Args:
            user_id: User-ID.

        Returns:
            Vorname + Nachname oder leerer String, falls nicht gefunden.
        """
        with Session(engine) as session:
            user = UserRepository(session).get_by_id(user_id)
            return f"{user.first_name} {user.last_name}" if user else ""


auth_service = AuthService()