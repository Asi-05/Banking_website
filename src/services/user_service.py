"""src.services.user_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der UserService verwaltet Benutzerprofile. Er kann:
- Profildaten laden (Vorname, Nachname, Telefon, Adresse)
- Telefonnummer und Adresse aktualisieren

=== WAS KANN DIESER SERVICE NICHT? ===
- Passwort aendern: Das ist Aufgabe des AuthService (Login-Logik)
- Vertragsnummer aendern: Ist unveraenderlicher Identifikator
- Vorname/Nachname aendern: Nicht vorgesehen (wuerde rechtliche Dokumente erfordern)
- Neuen User anlegen: Das passiert in `seed.py` (Demo-Daten) oder waere Aufgabe
  eines separaten Registrierungs-Services

=== ARCHITEKTUR-KETTE ===
    View (Profilseite) → Controller (user_controller.py)
    → **UserService (du bist hier)** → UserRepository → Datenbank

=== RUECKGABE-KETTE ===
    DB → UserRepository → UserService → user_controller
    → View zeigt Profildaten an ODER zeigt Erfolgsmeldung

=== PARTIAL UPDATE - WAS IST DAS? ===
    `update_profile(user_id, phone=None, address=None)` erlaubt es, nur
    einen Teil der Felder zu aendern. Wenn phone=None uebergeben wird,
    bleibt das alte Telefon unveraendert. Das ist nuetzlich, wenn das
    Formular nur ein Feld enthaelt.

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `user_service = UserService()`
    Diese eine Instanz wird ueberall im Projekt importiert.
"""

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from sqlmodel import Session


class UserService:
    """Service fuer Benutzerverwaltung und Profilbearbeitung.

    Delegiert alle Datenbankoperationen an das UserRepository.
    Enthaelt keine komplexe Geschaeftslogik (ausser Delegation und Session-Verwaltung).
    """

    def get_profile(self, user_id: int):
        """Laedt die Profildaten eines Users.

        AUFRUF-KETTE:
            user_controller.get_profile(user_id)
            → UserService.get_profile(user_id)
            → UserRepository.get_by_id(user_id)
            → SQL: SELECT * FROM users WHERE user_id = :user_id

        RUECKGABE-KETTE:
            DB → UserRepository → UserService → user_controller
            → View zeigt: Vorname, Nachname, Vertragsnummer, Telefon, Adresse

        WAS GIBT DAS ZURUECK?
            Ein User-Objekt (SQLModel ORM-Objekt) mit allen Feldern:
            user_id, first_name, last_name, contract_number, phone, address, password_hash
            ACHTUNG: password_hash ist ebenfalls im Objekt. Die View darf dieses Feld
            niemals anzeigen!

        Args:
            user_id: Datenbank-ID des Users.

        Returns:
            User-Objekt (ORM-Model) mit Profildaten.
            None, wenn kein User mit dieser ID existiert.
        """
        # Service-Schicht: Session oeffnen, DB-Details ans Repository delegieren.
        with Session(engine) as session:
            return UserRepository(session).get_by_id(user_id)

    def update_profile(self, user_id: int, phone: str | None, address: str | None):
        """Aktualisiert Profildaten eines Users (Telefon und/oder Adresse).

        AUFRUF-KETTE:
            user_controller.update_profile(user_id, phone, address)
            → UserService.update_profile(user_id, phone, address)
            → UserRepository.update_profile(user_id, phone, address)
            → SQL: UPDATE users SET phone=..., address=... WHERE user_id=:user_id

        RUECKGABE-KETTE:
            DB → UserRepository → UserService → user_controller
            → View zeigt Erfolgsmeldung ("Profil aktualisiert")

        PARTIAL UPDATE - WIE FUNKTIONIERT DAS?
            Das Repository prueft pro Feld: "Ist der Wert None?"
            Falls ja → Feld unveraendert lassen.
            Falls nein → Feld aktualisieren.

            Beispiele:
            - update_profile(5, phone="079 123 45 67", address=None)
              → Nur Telefon wird aktualisiert, Adresse bleibt unveraendert
            - update_profile(5, phone=None, address="Musterstrasse 1, 5000 Aarau")
              → Nur Adresse wird aktualisiert, Telefon bleibt unveraendert
            - update_profile(5, phone="...", address="...")
              → Beide Felder werden aktualisiert

        Args:
            user_id: Datenbank-ID des Users.
            phone: Neue Telefonnummer oder None (dann nicht aendern).
            address: Neue Adresse oder None (dann nicht aendern).

        Returns:
            Das aktualisierte User-Objekt (mit neuen Werten).

        Raises:
            KeyError: Wenn kein User mit dieser ID existiert.
        """
        # Repository kuemmert sich um "User laden → Felder setzen → speichern".
        with Session(engine) as session:
            return UserRepository(session).update_profile(user_id, phone, address)


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.user_service import user_service`
user_service = UserService()
