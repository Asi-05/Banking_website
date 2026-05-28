"""src.ui.controllers.payment_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

=== WAS MACHT DIESER CONTROLLER? ===
Verbindet transaction_view.py (wo Zahlungen und Umbuchungen eingegeben werden)
mit payment_service.py (wo die Geschaeftslogik liegt).

=== DREI FUNKTIONEN ===

1. ZAHLUNG (create_payment):
   Geld wird an eine externe IBAN ueberwiesen (z.B. an einen Vermieter).
   Das Konto des Users wird belastet.

2. UMBUCHUNG (create_transfer):
   Geld wird zwischen zwei eigenen Konten verschoben (z.B. vom Privatkonto
   aufs Sparkonto). Beide Konten gehoeren dem gleichen User.

3. KONTOAUSZUG (generate_statement):
   Erstellt einen PDF-Kontoauszug fuer einen bestimmten Zeitraum.
   Gibt den Dateipfad zur PDF-Datei zurueck.

=== AUFRUF-KETTE (Beispiel: Zahlung erstellen) ===
    [1] Nutzer klickt "Zahlung ausfuehren" in transaction_view.py
    [2] transaction_view.py ruft payment_controller.create_payment(payload) auf
    [3] payment_controller ruft payment_service.create_payment(payload) auf
    [4] payment_service validiert (IBAN, Betrag, Datum), prueft Saldo, erstellt Transaktion
    [5] transaction_repository.create(transaction) + payment_repository.create(payment)
    [6] Datenbank speichert Transaktion und Payment-Eintrag

=== GESCHAEFTSREGELN (im Service) ===
    - Ziel-IBAN muss gueltig sein (Schweizer Format)
    - Betrag muss positiv sein
    - Ausfuehrungsdatum darf nicht in der Vergangenheit liegen
    - Das Konto muss genuegend Saldo haben
"""

from __future__ import annotations

from datetime import date

from src.services.payment_service import payment_service


# Orchestriert Zahlungs-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class PaymentController:
    """UI-Controller fuer Zahlungen, Umbuchungen und Kontoauszuege."""

    def create_payment(self, payload: dict) -> str | None:
        """Fuehrt eine Inlandszahlung an eine externe IBAN aus.

        AUFRUF-KETTE:
            transaction_view.py (Button "Zahlung ausfuehren") → create_payment(payload)
            → payment_service.create_payment(payload)
            → transaction_service.create_transaction(...) [bucht Ausgabe vom Konto]
            → payment_repository.create(payment) [speichert Ziel-IBAN]
            → Datenbank

        EINGABE (payload-Keys):
            - "from_account_id" (int): Konto, von dem das Geld abgebucht wird
            - "target_iban"     (str): Ziel-IBAN (muss CH-Format sein, 21 Zeichen)
            - "amount"          (float): Betrag in CHF (muss > 0 sein)
            - "date"            (date): Ausfuehrungsdatum (darf nicht in Vergangenheit)
            - "category_id"     (int): Kategorie der Ausgabe
            - "note"            (str, optional): Verwendungszweck/Notiz

        WHAT HAPPENS TO THE ACCOUNT BALANCE:
            Das Konto (from_account_id) wird um den Betrag vermindert.
            Beispiel: Saldo vorher CHF 1'500, Zahlung CHF 200 → Saldo nachher CHF 1'300

        Args:
            payload: Dictionary mit Zahlungsdaten aus transaction_view.py.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            raw_date = payload.get("date")
            if isinstance(raw_date, str) and "." in raw_date:
                day, month, year = raw_date.split(".")
                payload = {**payload, "date": date(int(year), int(month), int(day))}
            payment_service.create_payment(payload)
            return None
        except Exception as error:
            return str(error)

    def create_transfer(self, payload: dict) -> str | None:
        """Fuehrt eine Umbuchung zwischen zwei eigenen Konten aus.

        AUFRUF-KETTE:
            transaction_view.py (Tab "Umbuchung") → create_transfer(payload)
            → payment_service.create_transfer(payload)
            → transaction_service.create_transaction(...) [2x: Ausgabe + Einnahme]
            → transfer_repository.create(transfer) [verknuepft beide Transaktionen]
            → Datenbank

        EINGABE (payload-Keys):
            - "from_account_id" (int): Quellkonto (wird belastet)
            - "to_account_id"   (int): Zielkonto (wird gutgeschrieben)
            - "amount"          (float): Umzubuchender Betrag in CHF

        WAS GENAU PASSIERT:
            1. Quellkonto: Ausgabe-Transaktion (Saldo wird vermindert)
            2. Zielkonto:  Einnahme-Transaktion (Saldo wird erhoht)
            3. Transfer-Eintrag: verknuepft beide Transaktionen miteinander

        GESCHAEFTSREGEL:
            Beide Konten muessen dem gleichen User gehoeren (Service prueft das).

        Args:
            payload: Dictionary mit Umbuchungsdaten.

        Returns:
            None bei Erfolg; Fehlermeldung als String bei Fehler.
        """
        try:
            payment_service.create_transfer(payload)
            return None
        except Exception as error:
            return str(error)

    def generate_statement(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
    ) -> str:
        """Erstellt einen Kontoauszug als PDF-Datei.

        AUFRUF-KETTE:
            account_view.py (Button "Kontoauszug") → generate_statement(...)
            → payment_service.generate_statement(account_id, start_date, end_date)
            → transaction_repository.filter_by_account_and_period(...) → Datenbank
            → PDF-Erstellung (liefert Dateipfad zurueck)

        RÜCKGABE:
            Bei Erfolg: Dateipfad als String (z.B. "/tmp/statement_12345.pdf")
            Bei Fehler: Fehlermeldung als String

        WIE DIE VIEW DAMIT UMGEHT:
            Die View prueft, ob der Pfad auf ".pdf" endet oder eine Fehlermeldung ist:
            if path.endswith(".pdf"): ui.download(path)
            else: ui.notify(path, type="negative")

        Args:
            account_id: Konto, fuer das der Auszug erstellt werden soll.
            start_date: Erster Tag des gewuenschten Zeitraums (inkl.).
            end_date: Letzter Tag des gewuenschten Zeitraums (inkl.).

        Returns:
            Dateipfad zur PDF-Datei oder Fehlermeldung als String.
        """
        try:
            return payment_service.generate_statement(account_id, start_date, end_date)
        except Exception as error:
            return str(error)


# Singleton-Instanz: wird von transaction_view.py und account_view.py importiert.
payment_controller = PaymentController()
