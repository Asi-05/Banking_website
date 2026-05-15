"""src.ui.controllers.recurring_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS IST EIN DAUERAUFTRAG? ===
Ein Dauerauftrag (auch: "Recurring Transaction") ist eine Ausgabe, die sich
automatisch wiederholt - z.B. monatliche Miete oder jaehrliche Versicherung.
Der Nutzer legt den Dauerauftrag einmal an, und beim naechsten Login wird geprueft,
ob er seit dem letzten Login faellig geworden ist. Falls ja, wird er automatisch
als Transaktion ausgefuehrt.

=== WAS MACHT DIESER CONTROLLER? ===
Verbindet transaction_view.py mit recurring_service.py.

BESONDERHEIT: NiceGUI gibt Datumswerte als Text (ISO-String, z.B. "2026-05-01")
zurueck. Der Service erwartet aber Python `date`-Objekte. Dieser Controller wandelt
deshalb Datumsstrings in `date`-Objekte um, bevor er den Service aufruft.

=== AUFRUF-KETTE (Beispiel: Dauerauftrag anlegen) ===
    [1] Nutzer faellt Dauerauftrag-Formular aus und klickt "Erstellen"
    [2] transaction_view.py ruft recurring_controller.create_recurring(payload) auf
    [3] Controller wandelt start_date-String in date-Objekt um
    [4] recurring_controller ruft recurring_service.create_recurring(payload) auf
    [5] recurring_service validiert (Betrag, IBAN, Startdatum) und speichert
    [6] recurring_repository.create(recurring) → Datenbank

=== AUTOMATISCHE AUSFUEHRUNG BEIM LOGIN ===
    Beim Login wird process_due_on_login() aufgerufen (durch login_view.py via
    auth_controller). Der Service prueft dann, ob seit dem letzten Login
    Dauerauftraege faellig waren, und fuehrt sie automatisch aus.
"""

from __future__ import annotations

from datetime import date

from src.services.recurring_service import recurring_service


# Orchestriert Dauerauftrag-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class RecurringController:
    """UI-Controller fuer Dauerauftraege (Recurring Transactions).

    Zusaetzlich zur ueblichen Fehlerbehandlung wandelt dieser Controller
    Datumsstrings aus NiceGUI in Python `date`-Objekte um.
    """

    def create_recurring(self, payload: dict) -> str | None:
        """Legt einen neuen Dauerauftrag an.

        AUFRUF-KETTE:
            transaction_view.py (Button "Dauerauftrag erstellen") → create_recurring(payload)
            → [Datum-Umwandlung: ISO-String → date]
            → recurring_service.create_recurring(payload)
            → recurring_repository.create(recurring) → Datenbank

        DATUM-UMWANDLUNG (warum notwendig?):
            NiceGUI-Datepicker gibt Daten als String zurueck (z.B. "2026-06-01").
            Der Service erwartet aber ein Python date-Objekt (date(2026, 6, 1)).
            date.fromisoformat("2026-06-01") macht diese Umwandlung.

        EINGABE (payload-Keys):
            - "account_id"  (int): Konto, von dem abgebucht wird
            - "category_id" (int): Kategorie der Ausgabe
            - "amount"      (float): Betrag in CHF
            - "target_iban" (str): Ziel-IBAN (wohin das Geld geht)
            - "interval"    (str): "monthly" oder "yearly"
            - "start_date"  (str/date): Ab wann der Dauerauftrag aktiv ist
            - "end_date"    (str/date, optional): Bis wann der Dauerauftrag aktiv ist

        GESCHAEFTSREGELN (im Service):
            - Startdatum darf nicht in der Vergangenheit liegen
            - Betrag muss > 0 sein
            - IBAN muss gueltiges CH-Format haben
            - Intervall muss "monthly" oder "yearly" sein

        Args:
            payload: Dictionary mit Dauerauftragsdaten aus der View.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            # NiceGUI/Browser liefern Datumswerte als ISO-Strings ("2026-05-01")
            # Der Service braucht Python date-Objekte → hier umwandeln

            # 1. Startdatum: wann beginnt der Dauerauftrag?
            if "start_date" in payload and isinstance(payload["start_date"], str):
                payload["start_date"] = date.fromisoformat(payload["start_date"])

            # 2. Enddatum: wann endet der Dauerauftrag? (optional)
            if "end_date" in payload and isinstance(payload["end_date"], str):
                payload["end_date"] = date.fromisoformat(payload["end_date"])

            # 3. Datum der Template-Transaktion (falls mitgegeben)
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = date.fromisoformat(payload["date"])

            # Jetzt den Service aufrufen (Validierung und Datenbank-Speicherung)
            recurring_service.create_recurring(payload)
            return None
        except Exception as error:
            return str(error)

    def process_due_on_login(self, user_id: int, login_date: date) -> int | str:
        """Fuehrt beim Login alle faelligen Dauerauftraege automatisch aus.

        WANN WIRD DIESE METHODE AUFGERUFEN?
            Direkt nach dem erfolgreichen Login in login_view.py:
            recurring_controller.process_due_on_login(user_id, date.today())

        WAS PASSIERT:
            Der Service prueft, welche Dauerauftraege seit dem letzten Login
            faellig geworden sind. Fuer jeden faelligen Auftrag:
            1. Wird eine neue Transaktion erstellt (Saldo des Kontos wird vermindert)
            2. Wird "last_executed" auf heute gesetzt

        BEISPIEL:
            Letzter Login: 01.04.2026
            Heutiger Login: 03.05.2026
            Monatlicher Dauerauftrag "Miete": faellig am 01. jeden Monats
            → Miete wird automatisch fuer Mai ausgefuehrt

        RÜCKGABE:
            int: Anzahl der ausgefuehrten Dauerauftraege (z.B. 2)
            str: Fehlermeldung, wenn etwas schiefgelaufen ist

        Args:
            user_id: ID des gerade eingeloggten Users.
            login_date: Heutiges Datum (typischerweise date.today()).

        Returns:
            Anzahl der ausgefuehrten Dauerauftraege (int) oder Fehlertext (str).
        """
        try:
            return recurring_service.process_due_recurring_on_login(user_id, login_date)
        except Exception as error:
            return str(error)

    def update_recurring(self, recurring_id: int, payload: dict) -> str | None:
        """Aktualisiert einen bestehenden Dauerauftrag.

        AUFRUF-KETTE:
            transaction_view.py (Button "Speichern") → update_recurring(id, payload)
            → [Datum-Umwandlung falls noetig]
            → recurring_service.update_recurring(recurring_id, payload)
            → recurring_repository.save(recurring) → Datenbank

        HINWEIS:
            Nur die Keys, die im payload vorhanden sind, werden geaendert.
            Fehlende Keys bleiben unveraendert (partielles Update).

        Args:
            recurring_id: ID des zu aendernden Dauerauftrags.
            payload: Keys, die geaendert werden sollen (z.B. {"amount": 1500.0}).

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            # end_date aus String in date umwandeln (falls mitgegeben)
            if "end_date" in payload and isinstance(payload["end_date"], str):
                payload["end_date"] = date.fromisoformat(payload["end_date"]) if payload["end_date"] else None

            recurring_service.update_recurring(recurring_id, payload)
            return None
        except Exception as error:
            return str(error)

    def delete_recurring(self, recurring_id: int) -> str | None:
        """Loescht einen Dauerauftrag dauerhaft.

        AUFRUF-KETTE:
            transaction_view.py (Button "Loeschen") → delete_recurring(recurring_id)
            → recurring_service.delete_recurring(recurring_id)
            → recurring_repository.delete(recurring) → Datenbank
            + template_transaction wird ebenfalls geloescht

        HINWEIS:
            Beim Loeschen wird auch die Template-Transaktion (die beim Anlegen
            des Dauerauftrags erstellt wurde) aus der Datenbank entfernt.

        Args:
            recurring_id: ID des zu loeschenden Dauerauftrags.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            recurring_service.delete_recurring(recurring_id)
            return None
        except Exception as error:
            return str(error)

    def list_recurring(self, user_id: int) -> list | str:
        """Gibt alle Dauerauftraege eines Users als Liste zurueck.

        AUFRUF-KETTE:
            transaction_view.py (Tab "Dauerauftraege") → list_recurring(user_id)
            → recurring_service.list_recurring(user_id)
            → recurring_repository.list_by_user(user_id) → Datenbank

        RUECKGABE:
            Liste von RecurringTransaction-Objekten. Jedes Objekt hat Felder wie:
            .recurring_id, .amount, .interval, .start_date, .end_date, .last_executed

        Args:
            user_id: ID des eingeloggten Users.

        Returns:
            Liste von RecurringTransaction-Objekten oder Fehlermeldung als String.
        """
        try:
            return recurring_service.list_recurring(user_id)
        except Exception as error:
            return str(error)

    def get_next_execution_date(self, last_executed: date, interval: str) -> date:
        """Berechnet das naechste Ausfuehrungsdatum eines Dauerauftrags.

        VERWENDUNG:
            Wird in der View genutzt, um die Spalte "Naechste Ausfuehrung" in der
            Dauerauftrags-Tabelle zu berechnen und anzuzeigen.

        BEISPIELE:
            last_executed=date(2026, 4, 1), interval="monthly"
            → gibt date(2026, 5, 1) zurueck

            last_executed=date(2026, 5, 31), interval="monthly"
            → gibt date(2026, 6, 30) zurueck (Juni hat nur 30 Tage)

        Args:
            last_executed: Datum der letzten Ausfuehrung.
            interval: "monthly" oder "yearly".

        Returns:
            Das naechste Ausfuehrungsdatum als Python date-Objekt.
        """
        return recurring_service.next_execution_date(last_executed, interval)

    def get_by_id(self, recurring_id: int):
        """Laedt einen einzelnen Dauerauftrag anhand seiner ID.

        VERWENDUNG:
            Wird z.B. genutzt, wenn ein Bearbeitungs-Dialog geoeffnet wird und
            die aktuellen Werte des Dauerauftrags vorausgefllt werden sollen.

        FEHLERBEHANDLUNG:
            Gibt None zurueck (statt einen Fehlertext), wenn der Dauerauftrag
            nicht existiert. Die View prueft dann: `if recurring is None: zeige Meldung`

        Args:
            recurring_id: ID des gewuenschten Dauerauftrags.

        Returns:
            RecurringTransaction-Objekt oder None bei Fehler/nicht gefunden.
        """
        try:
            return recurring_service.get_by_id(recurring_id)
        except Exception:
            return None


# Singleton-Instanz: wird von transaction_view.py importiert.
recurring_controller = RecurringController()
