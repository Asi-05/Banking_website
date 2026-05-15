"""src.ui.controllers.account_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS IST EIN CONTROLLER? ===
Ein Controller ist der "Vermittler" zwischen der View (was der Nutzer auf dem Bildschirm
sieht) und dem Service (wo die Geschaeftslogik liegt).

Wenn der Nutzer z.B. auf den Button "Konto eroeffnen" klickt, laeuft folgendes ab:

    AUFRUF-KETTE (von vorne nach hinten):
    [1] Nutzer klickt Button  →  account_view.py (show-Funktion)
    [2] View ruft auf         →  account_controller.open_account(payload)
    [3] Controller ruft auf   →  account_service.open_account(payload)
    [4] Service ruft auf      →  account_repository.create(account)
    [5] Repository schreibt   →  SQLite-Datenbank (Datei banking.db)

    RUECKGABE-KETTE (von hinten nach vorne):
    [5] Datenbank gibt zurueck  →  gespeichertes Account-Objekt
    [4] Repository gibt zurueck →  Account-Objekt mit generierter account_id
    [3] Service gibt zurueck    →  Account-Objekt (oder wirft ValueError/KeyError)
    [2] Controller gibt zurueck →  None (Erfolg) oder Fehlertext als String
    [1] View zeigt an           →  ui.notify("Fehler...") oder aktualisiert Konto-Liste

=== WARUM try/except IN JEDEM CONTROLLER? ===
Der Service wirft bei Fehlern Python-Exceptions (ValueError, KeyError). Die View
moechte aber nicht mit Exceptions umgehen muessen - sie soll einfach einen Text
anzeigen koennen. Deshalb faengt der Controller alle Exceptions ab und wandelt sie
in einen einfachen String um.

=== WAS BEDEUTEN DIE RUECKGABEWERTE? ===
    None  = Alles gut, kein Fehler aufgetreten
    str   = Ein Fehler ist aufgetreten, dieser String ist die Fehlermeldung

Die View prueft dann: `if error_text: ui.notify(error_text)` - ist es ein String,
wird er als Fehlermeldung angezeigt. Ist es None, war alles erfolgreich.
"""

from __future__ import annotations

from src.services.account_service import account_service


# Orchestriert Konto-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AccountController:
    """UI-Controller fuer Konto-Use-Cases (Eroeffnen, Schliessen, Auflisten).

    Jede Methode folgt dem gleichen Muster:
    1. Service-Methode aufrufen (enthalt die eigentliche Logik)
    2. Bei Erfolg: None zurueckgeben
    3. Bei Fehler (Exception): Fehlermeldung als String zurueckgeben

    Die Methoden aendern nie den Kontostatus direkt - das macht immer der Service.
    """

    def open_account(self, payload: dict) -> str | None:
        """Eroeffnet ein neues Konto fuer einen User.

        AUFRUF-KETTE:
            account_view.py (Button-Klick) → open_account(payload)
            → account_service.open_account(payload)
            → account_repository.create(account) → Datenbank

        EINGABE (payload-Keys):
            - "user_id"      (int): ID des eingeloggten Users
            - "account_type" (str): "privat" oder "spar"
            - "iban"         (str, optional): wird sonst automatisch generiert
            - "balance"      (float, optional): Startguthaben (Standard: 0.0)

        FEHLERQUELLEN (Service wirft, Controller faengt ab):
            - Unguentiger Kontotyp (nicht "privat" oder "spar")
            - User existiert nicht (KeyError)
            - IBAN bereits in Verwendung (ValueError)

        Args:
            payload: Dictionary mit Eingaben aus der View.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            # Service enthaelt die Geschaeftsregeln (Validierung, IBAN-Generierung, DB-Speicherung)
            account_service.open_account(payload)
            # None = alles gut, View kann Erfolgsmeldung zeigen
            return None
        except Exception as error:
            # Jede Exception (ValueError, KeyError, usw.) wird als Text an die View weitergegeben
            return str(error)

    def close_account(self, account_id: int) -> str | None:
        """Schliesst ein Konto (setzt Status auf "geschlossen").

        AUFRUF-KETTE:
            account_view.py (Button "Konto schliessen") → close_account(account_id)
            → account_service.close_account(account_id)
            → account_repository.save(account) → Datenbank

        WICHTIGE GESCHAEFTSREGEL (im Service):
            Ein Konto kann nur geschlossen werden, wenn der Saldo genau 0.0 ist.
            Wenn noch Geld auf dem Konto ist, wirft der Service einen ValueError.

        Args:
            account_id: Die ID des zu schliessenden Kontos (eine Ganzzahl).

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            account_service.close_account(account_id)
            return None
        except Exception as error:
            return str(error)

    def list_accounts(self, user_id: int) -> list | str:
        """Gibt alle Konten eines Users zurueck (fuer die Anzeige in der View).

        AUFRUF-KETTE:
            account_view.py (Seite laden) → list_accounts(user_id)
            → account_service.list_accounts(user_id)
            → account_repository.list_by_user(user_id) → Datenbank

        RÜCKGABE:
            Eine Liste von Account-Objekten (SQLModel-Instanzen). Jedes Objekt hat
            Felder wie .account_id, .iban, .balance, .status, .account_type.
            Die View zeigt diese Daten z.B. in einer Tabelle an.

        Args:
            user_id: ID des eingeloggten Users (aus app_state["user_id"]).

        Returns:
            Liste von Account-Objekten bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            return account_service.list_accounts(user_id)
        except Exception as error:
            return str(error)


# Singleton-Instanz: wird von den Views direkt importiert und genutzt.
# Statt jedes Mal AccountController() zu schreiben, importiert die View nur:
# from src.ui.controllers.account_controller import account_controller
account_controller = AccountController()
