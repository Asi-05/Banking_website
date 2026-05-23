"""src.ui.controllers.transaction_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS IST EINE TRANSAKTION? ===
Eine Transaktion ist eine Geldein- oder -ausgabe auf einem Konto/einer Karte.
Beispiele: Gehalt eingegangen (+CHF 4'500), Supermarkt (-CHF 85.30).

Die `transactions`-Tabelle in der Datenbank speichert alle Geldbewegungen und ist
die zentrale Tabelle der App. Daran haengen:
    - Payments (Zahlungen an externe IBANs)
    - Transfers (Umbuchungen zwischen eigenen Konten)
    - RecurringTransactions (Dauerauftraege)

=== WAS MACHT DIESER CONTROLLER? ===
Verbindet transaction_view.py mit transaction_service.py.

BESONDERHEIT: NiceGUI gibt Datumswerte als ISO-Strings ("2026-05-01") zurueck.
Der Service erwartet Python date-Objekte. Dieser Controller wandelt deshalb
Datumsstrings um.

AUSSERDEM: Der Controller wandelt SQLModel-Objekte (aus dem Service) in einfache
Python-Dictionaries um, die leichter in NiceGUI-Tabellen angezeigt werden koennen.
Dabei werden Datum und Typ bereits in lesbare Strings formatiert.

=== AUFRUF-KETTE (Beispiel: Transaktion erstellen) ===
    [1] Nutzer klickt "Transaktion erfassen" in transaction_view.py
    [2] transaction_view.py ruft transaction_controller.create_transaction(payload) auf
    [3] Controller wandelt Datum-String in date-Objekt um
    [4] transaction_controller ruft transaction_service.create_transaction(payload) auf
    [5] Service validiert (exactly-one-Quelle, positiver Betrag) und aktualisiert Saldo
    [6] transaction_repository.create(transaction) → Datenbank
"""

from __future__ import annotations

from datetime import date

from src.services.transaction_service import transaction_service
from src.utils.formatters import format_date_dmy, format_transaction_type


def _parse_date(value: str) -> date:
    """Wandelt DD.MM.YYYY oder YYYY-MM-DD in ein date-Objekt um."""
    if "." in value:
        d, m, y = value.split(".")
        return date(int(y), int(m), int(d))
    return date.fromisoformat(value)


# Orchestriert Transaktions-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class TransactionController:
    """UI-Controller fuer Transaktionen (Erstellen, Bearbeiten, Loeschen, Filtern).

    Zusaetzlich zur Fehlerbehandlung:
    - Wandelt Datumsstrings in date-Objekte um
    - Wandelt SQLModel-Objekte in UI-geeignete Dictionaries um
    """

    def create_transaction(self, payload: dict) -> str | None:
        """Erstellt eine neue Transaktion (Einnahme oder Ausgabe).

        AUFRUF-KETTE:
            transaction_view.py (Button "Erfassen") → create_transaction(payload)
            → [Datum-Umwandlung: "2026-05-01" → date(2026, 5, 1)]
            → transaction_service.create_transaction(payload)
            → transaction_repository.create(transaction) → Datenbank
            (Konto-/Kartensaldo wird ebenfalls aktualisiert)

        EINGABE (payload-Keys):
            - "amount"        (float): Betrag in CHF (muss > 0)
            - "type"          (str): "income" oder "expense"
            - "date"          (str/date): Datum der Transaktion
            - "category_id"   (int): Kategorie
            - "note"          (str, optional): Beschreibung
            GENAU EINE der folgenden (Exactly-One-Quelle Regel!):
            - "account_id"    (int): Konto-ID  (wenn Kontozahlung)
            - "card_id"       (int): Debitkarten-ID  (wenn Debitkarte)
            - "creditcard_id" (int): Kreditkarten-ID  (wenn Kreditkarte)

        EXACTLY-ONE-REGEL:
            Jede Transaktion darf nur EINE Quelle haben (Konto ODER Karte ODER
            Kreditkarte). Mehrere oder keine Quellen sind ein Fehler (Service prueft).

        Args:
            payload: Dictionary mit Transaktionsdaten.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = _parse_date(payload["date"])
            transaction_service.create_transaction(payload)
            return None
        except Exception as error:
            return str(error)

    def edit_transaction(self, transaction_id: int, payload: dict) -> str | None:
        """Bearbeitet eine bestehende Transaktion (Betrag, Notiz, Kategorie, Datum).

        AUFRUF-KETTE:
            transaction_view.py (Edit-Dialog) → edit_transaction(id, payload)
            → [Datum-Umwandlung falls noetig]
            → transaction_service.edit_transaction(transaction_id, payload)
            → transaction_repository.save(transaction) → Datenbank

        HINWEIS:
            Nur die Keys, die im payload vorhanden sind, werden geaendert.
            Wenn der Betrag geaendert wird, passt der Service den Kontosaldo
            automatisch an (Differenz wird verrechnet).

        Args:
            transaction_id: ID der zu aendernden Transaktion.
            payload: Zu aendernde Felder (z.B. {"amount": 95.0, "note": "Neue Notiz"}).

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            if "date" in payload and isinstance(payload["date"], str):
                payload["date"] = _parse_date(payload["date"])

            transaction_service.edit_transaction(transaction_id, payload)
            return None
        except Exception as error:
            return str(error)

    def delete_transaction(self, transaction_id: int, confirm: bool) -> str | None:
        """Loescht eine Transaktion dauerhaft.

        AUFRUF-KETTE:
            transaction_view.py (Button "Loeschen" + Bestaetigung) → delete_transaction(id, True)
            → transaction_service.delete_transaction(transaction_id, confirm)
            → transaction_repository.delete(transaction) → Datenbank
            (Kontosaldo wird entsprechend zurueckgerechnet)

        WARUM DAS confirm-FLAG?
            Als Schutzmassnahme vor versehentlichem Loeschen. Die View setzt
            confirm=True nur, wenn der Nutzer explizit bestaetigt hat.
            Falls confirm=False, wirft der Service einen Fehler.

        Args:
            transaction_id: ID der zu loeschenden Transaktion.
            confirm: Muss True sein, damit geloescht wird (UI-Schutzflag).

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            transaction_service.delete_transaction(transaction_id, confirm)
            return None
        except Exception as error:
            return str(error)

    def filter_for_month(
        self,
        user_id: int,
        year: int,
        month: int,
        account_id: int | None = None,
        category_id: int | None = None,
    ) -> list | str:
        """Gibt alle gebuchten Transaktionen eines Users fuer einen Monat zurueck.

        Kapselt die Monatsberechnung (erster/letzter Tag) und den optionalen
        Konto-Filter. Die View muss keine Datumsarithmetik mehr selbst machen.

        Args:
            user_id: ID des eingeloggten Users.
            year: Jahr (z.B. 2026).
            month: Monat (1-12).
            account_id: Optional – nur Transaktionen dieses Kontos; None = alle.
            category_id: Optional – nur Transaktionen dieser Kategorie; None = alle.

        Returns:
            Liste von UI-Dictionaries oder Fehlermeldung als String.
        """
        try:
            import calendar
            _, last_day = calendar.monthrange(year, month)
            transactions = transaction_service.filter_transactions(
                start_date=date(year, month, 1),
                end_date=date(year, month, last_day),
                category_id=category_id,
                user_id=user_id,
                is_settled=True,
            )
            return [
                {
                    "transaction_id": t.transaction_id,
                    "amount": t.amount,
                    "date": format_date_dmy(t.date),
                    "type": format_transaction_type(t.type),
                    "note": t.note,
                    "category_id": t.category_id,
                    "account_id": t.account_id,
                    "card_id": t.card_id,
                    "creditcard_id": t.creditcard_id,
                }
                for t in transactions
                if account_id is None or t.account_id == account_id
            ]
        except Exception as error:
            return str(error)

    def filter_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category_id: int | None = None,
        user_id: int | None = None,
        is_settled: bool | None = None,
    ) -> list | str:
        """Filtert Transaktionen und gibt UI-geeignete Dictionaries zurueck.

        AUFRUF-KETTE:
            transaction_view.py (Filter anwenden) → filter_transactions(...)
            → transaction_service.filter_transactions(...)
            → transaction_repository.filter(...) → Datenbank

        WOZU DIE UMWANDLUNG IN DICTIONARIES?
            SQLModel-Objekte (Datenbankzeilen) haben .date als Python date-Objekt
            und .type als "income"/"expense". Die View-Tabelle braucht aber Strings.
            Deshalb wandelt dieser Controller um:
            - date → formatiertes Datum "TT.MM.JJJJ" (z.B. "01.05.2026")
            - "income" → "Einkommen", "expense" → "Ausgabe"

        FILTER-PARAMETER (alle optional - None = kein Filter):
            start_date: Nur Transaktionen ab diesem Datum
            end_date: Nur Transaktionen bis zu diesem Datum
            category_id: Nur Transaktionen dieser Kategorie
            user_id: Nur Transaktionen dieses Users (ueber Konto-Ownership)

        RUECKGABE (Liste von Dicts bei Erfolg):
            [
              {
                "transaction_id": 42,
                "amount": 85.30,
                "date": "01.05.2026",        ← bereits formatiert
                "type": "Ausgabe",            ← bereits uebersetzt
                "note": "Supermarkt Migros",
                "category_id": 1,
                "account_id": 5,
                "card_id": None,
                "creditcard_id": None,
              },
              ...
            ]

        Args:
            start_date: Startdatum fuer Filter (inkl.) oder None.
            end_date: Enddatum fuer Filter (inkl.) oder None.
            category_id: Kategorie-ID fuer Filter oder None.
            user_id: User-ID fuer Filter oder None.

        Returns:
            Liste von Dictionaries (UI-geeignet) oder Fehlermeldung als String.
        """
        try:
            # Service gibt SQLModel-Objekte zurueck
            transactions = transaction_service.filter_transactions(
                start_date=start_date,
                end_date=end_date,
                category_id=category_id,
                user_id=user_id,
                is_settled=is_settled,
            )
            # Umwandlung in UI-geeignete Dictionaries mit formatierten Strings
            return [
                {
                    "transaction_id": transaction.transaction_id,
                    "amount": transaction.amount,
                    # format_date_dmy wandelt date(2026,5,1) → "01.05.2026"
                    "date": format_date_dmy(transaction.date),
                    # format_transaction_type wandelt "income" → "Einkommen" etc.
                    "type": format_transaction_type(transaction.type),
                    "note": transaction.note,
                    "category_id": transaction.category_id,
                    "account_id": transaction.account_id,
                    "card_id": transaction.card_id,
                    "creditcard_id": transaction.creditcard_id,
                }
                for transaction in transactions
            ]
        except Exception as error:
            return str(error)


# Singleton-Instanz: wird von transaction_view.py und dashboard_controller.py importiert.
transaction_controller = TransactionController()
