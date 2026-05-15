"""src.ui.controllers.card_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS MACHT DIESER CONTROLLER? ===
Verbindet card_view.py (Karten-Seite im Browser) mit card_service.py (Geschaeftslogik
fuer Debit- und Kreditkarten).

=== ZWEI KARTENTYPEN IN DIESER APP ===

DEBITKARTE:
    - Gehoert zu genau einem Konto (account_id)
    - Zahlungen werden sofort vom Konto abgebucht (via Transaktion)
    - Max. 1 aktive Debitkarte pro Konto (Geschaeftsregel im Service)
    - Aktionen: Bestellen, Sperren, Ersetzen

KREDITKARTE:
    - Gehoert zu einem User (nicht direkt zu einem Konto)
    - Hat ein Kreditlimit (z.B. CHF 2'000)
    - Zahlungen erhoehen den Kreditkartenstand (balance), werden aber erst
      beim Monatsabschluss vom Abrechnungskonto (billing_account) abgebucht
    - Max. 1 aktive Kreditkarte pro User (Geschaeftsregel im Service)
    - Aktionen: Erstellen, Sperren, Ersetzen, Abrechnungskonto setzen

=== AUFRUF-KETTE (Beispiel: Debitkarte bestellen) ===
    [1] Nutzer klickt "Debitkarte bestellen" in card_view.py
    [2] card_view.py ruft card_controller.order_debit_card(account_id) auf
    [3] card_controller ruft card_service.order_debit_card(account_id) auf
    [4] card_service prueft Regeln (max. 1 aktive Karte?) und erstellt Karte
    [5] card_repository.create(debit_card) → Datenbank

=== RUECKGABEWERTE ===
    None  = Erfolg
    str   = Fehlermeldung (z.B. "Dieses Konto hat bereits eine aktive Debitkarte")
    list  = Liste von Karten-Objekten (bei list_*-Methoden)
"""

from __future__ import annotations

from src.services.card_service import card_service


# Orchestriert Karten-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class CardController:
    """UI-Controller fuer Karten-Use-Cases (Debit und Kredit).

    Delegiert alle Geschaeftslogik an den CardService.
    Gibt nur None (Erfolg) oder String (Fehlermeldung) zurueck.
    """

    # ===== DEBITKARTEN =====

    def order_debit_card(self, account_id: int) -> str | None:
        """Bestellt eine neue Debitkarte fuer ein Konto.

        AUFRUF-KETTE:
            card_view.py (Button "Debitkarte bestellen") → order_debit_card(account_id)
            → card_service.order_debit_card(account_id)
            → card_repository.create(debit_card) → Datenbank

        GESCHAEFTSREGELN (im Service geprueft):
            - Das Konto muss existieren und aktiv sein
            - Es darf noch keine aktive Debitkarte fuer dieses Konto geben
            - Kartennummer und Ablaufdatum werden automatisch generiert

        Args:
            account_id: ID des Kontos, fuer das eine Debitkarte erstellt werden soll.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.order_debit_card(account_id)
            return None
        except Exception as error:
            return str(error)

    def block_debit_card(self, card_id: int) -> str | None:
        """Sperrt eine Debitkarte (z.B. bei Verlust oder Diebstahl).

        AUFRUF-KETTE:
            card_view.py (Button "Karte sperren") → block_debit_card(card_id)
            → card_service.block_debit_card(card_id)
            → card_repository.save(debit_card) → Datenbank (Status auf "gesperrt")

        HINWEIS:
            Eine gesperrte Karte kann nicht mehr fuer Transaktionen verwendet werden.
            Die Karte wird nicht geloescht, sondern nur als "gesperrt" markiert.

        Args:
            card_id: ID der zu sperrenden Debitkarte.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.block_debit_card(card_id)
            return None
        except Exception as error:
            return str(error)

    def replace_debit_card(self, card_id: int) -> str | None:
        """Ersetzt eine Debitkarte durch eine neue (alte Karte wird deaktiviert).

        AUFRUF-KETTE:
            card_view.py (Button "Karte ersetzen") → replace_debit_card(card_id)
            → card_service.replace_debit_card(card_id)
            → alte Karte: status="ersetzt", neue Karte: create → Datenbank

        WAS PASSIERT GENAU:
            1. Alte Karte wird als "ersetzt" markiert (nicht geloescht, fuer Protokoll)
            2. Neue Karte mit neuer Nummer und neuem Ablaufdatum wird erstellt
            3. Beide Aktionen werden in der gleichen Datenbank-Transaktion durchgefuehrt

        Args:
            card_id: ID der zu ersetzenden Debitkarte.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.replace_debit_card(card_id)
            return None
        except Exception as error:
            return str(error)

    # ===== KREDITKARTEN =====

    def create_credit_card(self, payload: dict) -> str | None:
        """Beantragt eine neue Kreditkarte fuer einen User.

        AUFRUF-KETTE:
            card_view.py (Button "Kreditkarte beantragen") → create_credit_card(payload)
            → card_service.create_credit_card(payload)
            → card_repository.create(credit_card) → Datenbank

        EINGABE (payload-Keys):
            - "user_id"       (int): ID des eingeloggten Users
            - "desired_limit" (float): Gewuenschtes Kreditlimit in CHF
                              (Service prueft: max. CHF 10'000)

        GESCHAEFTSREGELN (im Service):
            - Max. 1 aktive Kreditkarte pro User
            - Limit darf CHF 10'000 nicht ueberschreiten

        Args:
            payload: Dictionary mit user_id und desired_limit.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.create_credit_card(payload)
            return None
        except Exception as error:
            return str(error)

    def block_credit_card(self, creditcard_id: int) -> str | None:
        """Sperrt eine Kreditkarte.

        AUFRUF-KETTE:
            card_view.py (Button "Karte sperren") → block_credit_card(creditcard_id)
            → card_service.block_credit_card(creditcard_id)
            → card_repository.save(credit_card) → Datenbank (Status auf "gesperrt")

        Args:
            creditcard_id: ID der Kreditkarte.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.block_credit_card(creditcard_id)
            return None
        except Exception as error:
            return str(error)

    def replace_credit_card(self, creditcard_id: int) -> str | None:
        """Ersetzt eine Kreditkarte (alte deaktiviert, neue erstellt, Saldo uebertragen).

        AUFRUF-KETTE:
            card_view.py (Button "Karte ersetzen") → replace_credit_card(creditcard_id)
            → card_service.replace_credit_card(creditcard_id)
            → Datenbank (alte Karte "ersetzt", neue Karte wird angelegt)

        HINWEIS:
            Der bestehende Saldo (bereits ausgegebener Kredit) wird auf die neue
            Karte uebertragen, damit beim Monatsabschluss korrekt abgerechnet wird.

        Args:
            creditcard_id: ID der zu ersetzenden Kreditkarte.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.replace_credit_card(creditcard_id)
            return None
        except Exception as error:
            return str(error)

    def handle_set_billing_account(self, creditcard_id: int, account_id: int) -> str | None:
        """Setzt das Abrechnungskonto fuer eine Kreditkarte.

        WAS IST DAS ABRECHNUNGSKONTO?
            Am Ende jeden Monats wird der aufgelaufene Kreditkartensaldo (alle
            Kreditkartenausgaben des Monats) automatisch von diesem Konto abgebucht.
            Beispiel: Kreditkarte hat CHF 342.50 Saldo → am Monatsende werden
            CHF 342.50 vom Abrechnungskonto (z.B. Privatkonto) abgezogen.

        AUFRUF-KETTE:
            card_view.py (Dropdown-Auswahl) → handle_set_billing_account(cc_id, acc_id)
            → card_service.set_billing_account(creditcard_id, account_id)
            → card_repository.save(credit_card) → Datenbank

        Args:
            creditcard_id: ID der Kreditkarte.
            account_id: ID des Kontos, das als Abrechnungskonto genutzt werden soll.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            card_service.set_billing_account(creditcard_id, account_id)
            return None
        except Exception as error:
            return str(error)

    # ===== LISTEN =====

    def list_debit_cards(self, user_id: int) -> list | str:
        """Gibt alle Debitkarten eines Users zurueck.

        AUFRUF-KETTE:
            card_view.py (Seite laden) → list_debit_cards(user_id)
            → card_service.list_debit_cards(user_id)
            → card_repository.list_debit_by_user(user_id) → Datenbank

        HINWEIS:
            Gibt ALLE Karten zurueck (aktiv, gesperrt, ersetzt), damit die View
            auch historische Karten anzeigen kann. Die View filtert selbst nach Status.

        Args:
            user_id: ID des eingeloggten Users.

        Returns:
            Liste von DebitCard-Objekten oder Fehlermeldung als String.
        """
        try:
            return card_service.list_debit_cards(user_id)
        except Exception as error:
            return str(error)

    def list_credit_cards(self, user_id: int) -> list | str:
        """Gibt alle Kreditkarten eines Users zurueck.

        AUFRUF-KETTE:
            card_view.py (Seite laden) → list_credit_cards(user_id)
            → card_service.list_credit_cards(user_id)
            → card_repository.list_credit_by_user(user_id) → Datenbank

        HINWEIS:
            Gibt ALLE Kreditkarten zurueck (inkl. gesperrter/ersetzter).
            Jedes CreditCard-Objekt hat Felder wie .limit, .balance, .status, .last_billed.

        Args:
            user_id: ID des eingeloggten Users.

        Returns:
            Liste von CreditCard-Objekten oder Fehlermeldung als String.
        """
        try:
            return card_service.list_credit_cards(user_id)
        except Exception as error:
            return str(error)


# Singleton-Instanz: wird von card_view.py importiert.
card_controller = CardController()
