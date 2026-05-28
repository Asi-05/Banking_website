"""src.data_access.repositories.user_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS MACHT DIESES REPOSITORY? ===
Laedt und speichert User-Daten in der SQLite-Datenbank.
Ein "User" ist ein registrierter Bankkunde mit Vertragsnummer und Passwort-Hash.

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank

    Dieses Repository wird hauptsaechlich von zwei Services genutzt:
    - auth_service.py:  Login-Pruefung (User per Vertragsnummer laden)
    - user_service.py:  Profil-Verwaltung (Telefon/Adresse aktualisieren)

=== WAS IST EINE SESSION? ===
Eine Session ist die "Verbindung" zur Datenbank. Alle Datenbankoperationen laufen
ueber die Session:
    - session.get(User, user_id)      → Suche nach Primaerschluessel (sehr schnell)
    - session.exec(statement).first() → Suche nach anderen Kriterien (per SQL-Query)
    - session.add(user)               → Objekt zur Session hinzufuegen (noch nicht in DB)
    - session.commit()                → Aenderungen wirklich in die Datei schreiben
    - session.refresh(user)           → Aktuelle Werte aus DB ins Objekt laden

=== WICHTIG: PASSWORT-SICHERHEIT ===
Dieses Repository speichert NIEMALS das Klartextpasswort. In der Datenbank steht
nur der `password_hash` (ein berechneter Wert, aus dem man das Passwort nicht
zurueckrechnen kann). Die Hash-Berechnung passiert in `auth_service.py`.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import User


# Kapselt reine Datenbankzugriffe fuer Benutzer.
class UserRepository:
    """Datenbankzugriffe fuer `User`-Objekte.

    Wird vom AuthService (Login) und UserService (Profil-Verwaltung) genutzt.
    Enthaelt keine Passwort-Logik oder Geschaeftsregeln - nur reiner DB-Zugriff.
    """

    def __init__(self, session: Session):
        """Erstellt das Repository mit einer offenen Datenbank-Session.

        WOHER KOMMT DIE SESSION?
            Der aufgerufene Service erstellt sie mit:
            `with Session(engine) as session: user_repo = UserRepository(session)`

        Args:
            session: Eine bereits geoeffnete SQLModel/SQLAlchemy-Session.
        """
        self.session = session

    def get_by_contract_number(self, contract_number: str) -> User | None:
        """Laedt einen User anhand seiner Vertragsnummer.

        AUFRUF-KETTE:
            auth_service.login(contract_number, password)
            → UserRepository.get_by_contract_number(contract_number)
            → SQL: SELECT * FROM users WHERE contract_number = :contract_number

        WOZU?
            Beim Login gibt der Nutzer seine Vertragsnummer ein. Damit finden wir
            den zugehoerigen User-Datensatz in der Datenbank.

        Args:
            contract_number: Die Vertragsnummer des Users (z.B. "BB-100001").
                             Jede Vertragsnummer ist eindeutig (unique in der DB).

        Returns:
            User-Objekt wenn gefunden, None wenn keine Vertragsnummer passt.
        """
        # select(User) = "Suche in der users-Tabelle"
        # .where(...) = "Filtere: nur wo contract_number = gesuchter Wert"
        statement = select(User).where(User.contract_number == contract_number)
        # .first() = erstes (und einziges) Ergebnis, oder None wenn nicht gefunden
        return self.session.exec(statement).first()

    def get_by_id(self, user_id: int) -> User | None:
        """Laedt einen User anhand seiner Datenbank-ID.

        AUFRUF-KETTE:
            Verschiedene Services (auth, user, account, ...)
            → UserRepository.get_by_id(user_id)
            → SQL: SELECT * FROM users WHERE user_id = :user_id

        WARUM GIBT ES ZWEI LADE-METHODEN (get_by_id + get_by_contract_number)?
            - Beim Login kennt man nur die Vertragsnummer → get_by_contract_number
            - Danach wird die user_id in app_state gespeichert → get_by_id

        Args:
            user_id: Die eindeutige Datenbank-ID des Users (Ganzzahl).

        Returns:
            User-Objekt wenn gefunden, None wenn User nicht existiert.
        """
        # session.get() ist schneller als eine Query, weil SQLAlchemy intern cachen kann
        return self.session.get(User, user_id)

    def save(self, user: User) -> User:
        """Speichert einen User (neu oder geaendert) in der Datenbank.

        AUFRUF-KETTE:
            user_service.update_profile(...)
            → UserRepository.save(user)
            → SQL: UPDATE users SET phone=..., address=... WHERE user_id=...

        WAS PASSIERT SCHRITT FUER SCHRITT:
            1. session.add(user):    Hat der User eine user_id? Ja → UPDATE, Nein → INSERT
            2. session.commit():     Wirklich in die SQLite-Datei schreiben
            3. session.refresh(user): DB-Werte ins Python-Objekt zurueckladen

        Args:
            user: Das User-Objekt mit eventuell geaenderten Feldern (phone, address).

        Returns:
            Das gespeicherte User-Objekt nach dem Update (aktueller Stand aus DB).
        """
        self.session.add(user)      # Objekt fuer Speicherung markieren
        self.session.commit()       # In Datenbank schreiben
        self.session.refresh(user)  # Aktuelle Werte aus DB laden
        return user

    def update_profile(self, user_id: int, phone: str | None, address: str | None) -> User:
        """Aktualisiert Telefonnummer und/oder Adresse eines Users.

        AUFRUF-KETTE:
            user_service.update_profile(user_id, phone, address)
            → UserRepository.update_profile(user_id, phone, address)
            → get_by_id(user_id) [laden] → save(user) [speichern]

        WIE FUNKTIONIERT DAS PARTIELLE UPDATE?
            Wenn phone=None uebergeben wird → Telefonnummer wird NICHT geaendert
            Wenn phone="0441234567" uebergeben wird → Telefonnummer wird gesetzt

            So kann man Telefon oder Adresse einzeln aktualisieren, ohne beide angeben zu muessen.

        Args:
            user_id: ID des zu aktualisierenden Users.
            phone: Neue Telefonnummer oder None (dann unveraendert lassen).
            address: Neue Adresse oder None (dann unveraendert lassen).

        Returns:
            Den gespeicherten User nach der Aktualisierung.

        Raises:
            KeyError: Wenn kein User mit dieser user_id existiert.
        """
        # Zuerst den User laden (brauchen das Objekt, um Felder zu aendern)
        user = self.get_by_id(user_id)
        if user is None:
            raise KeyError(f"User {user_id} nicht gefunden")

        # Nur Felder ueberschreiben, die auch einen neuen Wert haben (nicht None)
        if phone is not None:
            user.phone = phone       # Telefonnummer aktualisieren
        if address is not None:
            user.address = address   # Adresse aktualisieren

        # Geaenderten User speichern
        return self.save(user)
