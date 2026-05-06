"""src.ui.controllers.recurring_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Die UI liefert Datumswerte haeufig als ISO-String (z.B. "2026-05-05").
Die Service-Schicht arbeitet dagegen mit echten `datetime.date`-Objekten.

Dieser Controller uebernimmt daher (wo noetig) die Umwandlung von Strings in
`date`, bevor er den `RecurringService` aufruft.
"""

from __future__ import annotations

from datetime import date

from src.services.recurring_service import recurring_service


# Orchestriert Dauerauftrag-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class RecurringController:
    """UI-Controller fuer Dauerauftraege (Recurring Transactions)."""

    # Legt einen Dauerauftrag an.
    def create_recurring(self, payload: dict) -> str | None:
        """Legt einen neuen Dauerauftrag an.

        Die wichtigste Zusatzaufgabe des Controllers ist hier die Normalisierung
        von Datumsfeldern (ISO-String -> `date`), weil NiceGUI/Browser haeufig Strings
        liefert.

        Args:
            payload: Eingabedaten aus der UI (z.B. amount, interval, start_date, optional end_date).

        Returns:
            `None` bei Erfolg.
            Bei Fehlern: ein Fehlertext als `str`.

        Raises:
            Keine. Fehler werden als String zur UI zurueckgegeben.
        """
        try:
            # NiceGUI/Browser liefern Datumswerte haeufig als Text (ISO-String).
            # Die Service-Schicht arbeitet dagegen mit echten `datetime.date`-Objekten.
            # Darum wandeln wir hier Datumsstrings in `date` um, bevor wir den Service aufrufen.
            # 1. Startdatum des Dauerauftrags
            if "start_date" in payload and isinstance(payload["start_date"], str):
                payload["start_date"] = date.fromisoformat(payload["start_date"])
                
            # 2. Enddatum des Dauerauftrags (falls vorhanden)
            if "end_date" in payload and isinstance(payload["end_date"], str):
                payload["end_date"] = date.fromisoformat(payload["end_date"])
                
            # 3. Datum für die zugrundeliegende Basis-Transaktion
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = date.fromisoformat(payload["date"])

            recurring_service.create_recurring(payload)
            return None
        except Exception as error:
            return str(error)

    # Verarbeitet faellige Dauerauftraege beim Login.
    def process_due_on_login(self, user_id: int, login_date: date) -> int | str:
        """Fuehrt beim Login alle Dauerauftraege aus, die faellig geworden sind.

        Die Service-Schicht prueft dabei, welche Dauerauftraege seit dem letzten
        Login ausgefuehrt werden muessen.

        Args:
            user_id: ID des eingeloggten Users.
            login_date: Heutiges Datum (typischerweise `date.today()`).

        Returns:
            Anzahl der ausgefuehrten Dauerauftraege als `int`.
            Bei Fehlern: ein Fehlertext als `str` (statt einer Exception).

        Raises:
            Keine. Fehler werden als String zur UI zurueckgegeben.
        """
        try:
            return recurring_service.process_due_recurring_on_login(user_id, login_date)
        except Exception as error:
            return str(error)

    # Aktualisiert einen bestehenden Dauerauftrag.
    def update_recurring(self, recurring_id: int, payload: dict) -> str | None:
        """Aktualisiert einen Dauerauftrag.

        Auch hier wird (falls noetig) `end_date` normalisiert.

        Args:
            recurring_id: ID des zu aktualisierenden Dauerauftrags.
            payload: Zu aendernde Felder aus der UI.

        Returns:
            `None` bei Erfolg.
            Bei Fehlern: ein Fehlertext als `str`.

        Raises:
            Keine. Fehler werden als String zur UI zurueckgegeben.
        """
        try:
            # Umwandlung von Datumsstrings (z.B. "2026-05-01") in Python date-Objekte
            if "end_date" in payload and isinstance(payload["end_date"], str):
                payload["end_date"] = date.fromisoformat(payload["end_date"]) if payload["end_date"] else None

            recurring_service.update_recurring(recurring_id, payload)
            return None
        except Exception as error:
            return str(error)

    # Loescht einen Dauerauftrag.
    def delete_recurring(self, recurring_id: int) -> str | None:
        """Loescht einen Dauerauftrag dauerhaft.

        Args:
            recurring_id: ID des zu loeschenden Dauerauftrags.

        Returns:
            `None` bei Erfolg.
            Bei Fehlern: ein Fehlertext als `str`.

        Raises:
            Keine. Fehler werden als String zur UI zurueckgegeben.
        """
        try:
            recurring_service.delete_recurring(recurring_id)
            return None
        except Exception as error:
            return str(error)

    # Listet alle Dauerauftraege eines Users.
    def list_recurring(self, user_id: int) -> list | str:
        """Gibt alle Dauerauftraege eines Users zurueck.

        Args:
            user_id: ID des eingeloggten Users.

        Returns:
            Liste von `RecurringTransaction`-Objekten.
            Bei Fehlern: ein Fehlertext als `str`.

        Raises:
            Keine. Fehler werden als String zur UI zurueckgegeben.
        """
        try:
            return recurring_service.list_recurring(user_id)
        except Exception as error:
            return str(error)

    # Berechnet das naechste Ausfuehrungsdatum.
    def get_next_execution_date(self, last_executed: date, interval: str) -> date:
        """Berechnet das naechste Ausfuehrungsdatum.

        Die View nutzt dieses Datum z.B. fuer die Tabellenspalte "Naechste Ausfuehrung".

        Args:
            last_executed: Datum der letzten Ausfuehrung.
            interval: Intervall als String, typischerweise "monthly" oder "yearly".

        Returns:
            Das naechste Ausfuehrungsdatum als `date`.
        """
        return recurring_service.next_execution_date(last_executed, interval)

    # Liefert einen einzelnen Dauerauftrag per ID.
    def get_by_id(self, recurring_id: int):
        """Laedt einen einzelnen Dauerauftrag.

        Args:
            recurring_id: ID des Dauerauftrags.

        Returns:
            Ein `RecurringTransaction`-Objekt, oder `None`, wenn der Datensatz
            nicht gefunden wird oder ein Fehler auftritt.

        Raises:
            Keine. Fehler werden abgefangen und als `None` abgebildet.
        """
        try:
            return recurring_service.get_by_id(recurring_id)
        except Exception:
            return None


recurring_controller = RecurringController()