"""src.ui.controllers.auth_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS MACHT DIESER CONTROLLER? ===
Dieser Controller ist zustaendig fuer die Authentifizierung - also den Login-Vorgang.
Er ist der erste Kontaktpunkt nach dem View, wenn ein Nutzer seine Vertragsnummer
und sein Passwort eingibt und auf "Anmelden" klickt.

    AUFRUF-KETTE beim Login:
    [1] Nutzer klickt "Anmelden" in login_view.py
    [2] login_view.py ruft auth_controller.login(contract_number, password) auf
    [3] auth_controller ruft auth_service.login(contract_number, password) auf
    [4] auth_service laedt User aus der Datenbank und prueft Passwort-Hash
    [5] auth_service gibt ein Ergebnis-Dict oder eine Exception zurueck
    [6] auth_controller gibt dict (Erfolg) oder String (Fehler) an login_view.py zurueck
    [7] login_view.py setzt app_state und navigiert zum Dashboard (Erfolg)
        oder zeigt Fehlermeldung an (Fehler)

=== WAS IST app_state? ===
Nach erfolgreichem Login speichert die View das Ergebnis-Dict in app_state["current_user"].
Das ist ein globales Dictionary (definiert in src/ui/app_state.py), das alle anderen
Views nutzen, um zu wissen, wer gerade eingeloggt ist.
Jede View prueft am Anfang: `if app_state["current_user"] is None: navigate.to("/")`
Das schuetzt alle Seiten davor, ohne Login aufgerufen zu werden.

=== ALLGEMEINES CONTROLLER-MUSTER ===
Alle Controller in dieser App folgen demselben Prinzip:
    - Service aufrufen (Service hat die echte Logik)
    - Bei Erfolg: Ergebnis zurueckgeben
    - Bei Fehler (Exception): Fehlertext als String zurueckgeben (nie die Exception selbst)
Die View prueft dann: `if isinstance(result, str): zeige Fehler an`
"""

from __future__ import annotations

from src.services.auth_service import auth_service


# Orchestriert Login-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AuthController:
    """UI-Controller fuer Authentifizierung (Login-Use-Case).

    Dieser Controller hat nur zwei Aufgaben:
    1. Den Login an den AuthService delegieren
    2. Exceptions in Strings umwandeln, damit die View sie anzeigen kann

    Keine Datenbanklogik, keine Passwort-Pruefung - das alles liegt im AuthService.
    """

    def login(self, contract_number: str, password: str) -> dict | str:
        """Fuehrt den Login-Vorgang durch.

        AUFRUF-KETTE:
            login_view.py (Button-Klick) → login(contract_number, password)
            → auth_service.login(contract_number, password)
            → user_repository.get_by_contract_number(contract_number) → Datenbank
            → verify_password(password, user.password_hash)  [in validators.py]

        EINGABE:
            contract_number: Die Vertragsnummer des Users (z.B. "V-10001").
                             Eingabe aus dem Formularfeld in login_view.py.
            password: Das eingegebene Passwort im Klartext.
                      WICHTIG: Wird NICHT gespeichert, nur fuer die Verifikation genutzt.

        RUECKGABE (zwei Moeglichkeiten):
            dict: Login war erfolgreich. Enthaelt Keys wie:
                  - "success": True
                  - "user_id": int (ID des eingeloggten Users)
                  - Weitere User-Daten fuer app_state
            str:  Login hat nicht geklappt. Dieser String ist die Fehlermeldung
                  (z.B. "Falsche Vertragsnummer oder Passwort").

        WAS DIE VIEW DAMIT MACHT:
            result = auth_controller.login(nr, pw)
            if isinstance(result, str):   →  error_label.set_text(result)
            elif result.get("success"):   →  app_state["current_user"] = result
                                          →  ui.navigate.to("/dashboard")

        Args:
            contract_number: Vertragsnummer als Login-Identifikator.
            password: Passwort im Klartext (wird im Service geprueft und nie gespeichert).

        Returns:
            Dict mit Login-Ergebnis (inkl. user_id) oder Fehlermeldung als String.
        """
        try:
            # Der AuthService prueft: existiert der User? Stimmt das Passwort? (PBKDF2-Hash)
            return auth_service.login(contract_number, password)
        except Exception as error:
            # Bei jedem Fehler (User nicht gefunden, falsches Passwort, DB-Fehler)
            # wird die Exception als lesbarer Text zurueckgegeben.
            return str(error)

    def get_username(self, user_id: int) -> str:
        """Liefert den vollstaendigen Namen eines Users fuer die Anzeige in der UI.

        AUFRUF-KETTE:
            Irgendeine View (z.B. Header-Begruessung) → get_username(user_id)
            → auth_service.get_full_name(user_id)
            → user_repository.get_by_id(user_id) → Datenbank

        VERWENDUNG:
            Wird z.B. verwendet, um "Hallo, Max Muster" im Header anzuzeigen.
            user_id kommt dabei aus app_state["user_id"].

        FEHLERBEHANDLUNG:
            Falls der User nicht gefunden wird oder die DB nicht erreichbar ist,
            wird kein Fehler angezeigt - stattdessen wird "" (leerer String) zurueckgegeben.
            Die View zeigt dann einfach keinen Namen an.

        Args:
            user_id: ID des eingeloggten Users (aus app_state["user_id"]).

        Returns:
            Vollstaendiger Name (Vorname + Nachname) oder leerer String bei Fehlern.
        """
        try:
            return auth_service.get_full_name(user_id)
        except Exception:
            # Fehler werden hier stillschweigend ignoriert (leerer Name ist kein kritischer Fehler)
            return ""


# Singleton-Instanz: einmal erstellt, von allen Views importiert.
auth_controller = AuthController()
