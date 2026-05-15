"""src.services.payment_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der PaymentService verwaltet drei verwandte Themen:

1. ZAHLUNG (Payment):
   Geld von einem eigenen Konto an eine externe IBAN ueberweisen.
   Technisch: 1 Transaction (expense) + 1 Payment-Datensatz (Ziel-IBAN, Verwendungszweck)

2. UMBUCHUNG (Transfer):
   Geld zwischen zwei eigenen Konten verschieben.
   Technisch: 2 Transactions (expense + income) + 1 Transfer-Datensatz (from/to Konto)

3. KONTOAUSZUG (Statement):
   Alle Buchungen eines Kontos in einem Zeitraum als PDF exportieren.
   Technisch: DB-Abfrage + manuell erstelltes PDF (ohne externe Library)

=== WARUM ZWEI TRANSAKTIONEN BEI UMBUCHUNG? ===
Eine Umbuchung bewegt Geld von Konto A nach Konto B.
Das braucht zwei Buchungen:
    - Konto A: CHF -500 (expense = Geld geht weg)
    - Konto B: CHF +500 (income = Geld kommt an)
Der Transfer-Datensatz verknuepft beide und merkt sich: "Das sind zusammengehoerend."
Das Dashboard filtert Umbuchungen heraus, damit sie nicht doppelt als
Einnahme UND Ausgabe gezaehlt werden.

=== WARUM DELEGIERT DIESER SERVICE AN TransactionService? ===
Die Saldologik (Konto-Balance aendern, Limit pruefen, Quelle validieren) liegt
zentral im TransactionService. Der PaymentService muss diese Logik nicht selbst
implementieren - er delegiert die eigentliche Buchung weiter.

=== ARCHITEKTUR-KETTE ===
    View (card_view.py bzw. kein direktes View) → Controller (payment_controller.py)
    → **PaymentService (du bist hier)**
    → TransactionService (eigentliche Buchung + Saldo)
    → PaymentRepository (Payment/Transfer-Datensatz speichern)
    → AccountRepository (Konto validieren)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `payment_service = PaymentService()`
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.payment_repository import PaymentRepository
from src.domain.models import Payment, Transfer
from src.services.transaction_service import transaction_service
from src.utils.formatters import format_date_dmy, format_transaction_type
from src.utils.validators import validate_date_range, validate_iban, validate_positive_amount


CURRENCY_CODE = "CHF"


class PaymentService:
    """Fachlogik fuer Zahlungen, Umbuchungen und Kontoauszuege."""

    def create_payment(self, payload: dict) -> Payment:
        """Erstellt eine Zahlung (Ausgabe) von einem eigenen Konto zu einer Ziel-IBAN.

        AUFRUF-KETTE:
            payment_controller.create_payment(payload)
            → PaymentService.create_payment(payload)
            → validate_iban(target_iban)              [IBAN-Format pruefen]
            → validate_positive_amount(amount)
            → AccountRepository.get_by_id(from_account_id)  [Konto laden und Saldo pruefen]
            → TransactionService.create_transaction(...)     [Buchung + Saldo-Update]
            → PaymentRepository.create_payment(payment)     [Payment-Zusatzdaten speichern]

        RUECKGABE-KETTE:
            DB → PaymentRepository → PaymentService → payment_controller
            → View zeigt: "Zahlung erfolgreich"

        WARUM ZWEI DB-SCHRITTE?
            1. TransactionService erstellt die eigentliche Buchung (bucht vom Konto ab).
            2. PaymentRepository speichert Zahlungsdetails (Ziel-IBAN, Verwendungszweck).
            Diese Trennung erlaubt es, dieselbe Transaction-Logik fuer alle Zahlungstypen
            zu wiederverwenden.

        DATUM-REGEL:
            Zahlungsdatum darf nicht in der Vergangenheit liegen.
            (Echte Banken erlauben keine rueckdatierten Zahlungen.)

        PAYLOAD-KEYS:
            - "target_iban" (str)       → Pflichtfeld: Ziel-IBAN
            - "amount" (float/str)      → Pflichtfeld
            - "from_account_id" (int)   → Pflichtfeld: Von welchem Konto
            - "purpose" (str)           → Pflichtfeld: Verwendungszweck
            - "category_id" (int)       → Pflichtfeld: Buchungskategorie
            - "date" (date/str, opt.)   → Default: heute

        Args:
            payload: Dictionary aus Controller/UI.

        Returns:
            Das gespeicherte Payment-Objekt (inkl. payment_id und transaction_id).

        Raises:
            KeyError: Wenn das Quellkonto nicht existiert.
            ValueError: Bei ungueltiger IBAN, ungueltigem Betrag, Datum in der
                        Vergangenheit, oder unzureichendem Kontosaldo.
        """
        target_iban = str(payload["target_iban"])
        amount = float(payload["amount"])
        from_account_id = int(payload["from_account_id"])
        purpose = str(payload["purpose"])
        category_id = int(payload["category_id"])

        # Schnelle Validierungen: pruefen bevor eine DB-Session geoeffnet wird.
        validate_iban(target_iban)
        validate_positive_amount(amount)

        payment_date = payload.get("date", date.today())
        if isinstance(payment_date, str):
            payment_date = date.fromisoformat(payment_date)
        if payment_date < date.today():
            raise ValueError("Ausfuehrungsdatum darf nicht in der Vergangenheit liegen")

        with Session(engine) as session:
            account_repository = AccountRepository(session)
            from_account = account_repository.get_by_id(from_account_id)
            if from_account is None:
                raise KeyError(f"Konto {from_account_id} nicht gefunden")
            # Vorzeitige Saldo-Pruefung (vor der Buchung).
            if from_account.balance < amount:
                raise ValueError("Unzureichender Kontosaldo")

        # Die eigentliche Buchung (inkl. Saldologik) wird zentral im TransactionService gemacht.
        # Das verhindert, dass jede Feature-Klasse eigene Saldo-Logik implementiert.
        transaction = transaction_service.create_transaction(
            {
                "amount": amount,
                "type": "expense",
                "date": payload.get("date", date.today()),
                "category_id": category_id,
                "account_id": from_account_id,
                "note": purpose,
            }
        )

        with Session(engine) as session:
            payment_repository = PaymentRepository(session)
            # Payment = Spezialisierung der Transaktion mit Zahlungs-Zusatzdaten.
            payment = Payment(
                target_iban=target_iban,
                purpose=purpose,
                status="success",
                transaction_id=transaction.transaction_id,
            )
            return payment_repository.create_payment(payment)

    def create_transfer(self, payload: dict) -> Transfer:
        """Fuehrt eine Umbuchung zwischen zwei eigenen Konten aus.

        AUFRUF-KETTE:
            payment_controller.create_transfer(payload)
            → PaymentService.create_transfer(payload)
            → validate_positive_amount(amount)
            → Pruefung: from_account_id != to_account_id
            → AccountRepository.get_by_id(from_account_id)    [Quellkonto laden]
            → AccountRepository.get_by_id(to_account_id)      [Zielkonto laden]
            → Validierungen: aktiv? gleicher User? Saldo?
            → TransactionService.create_transaction(...)       [Ausgangsbuchung: expense]
            → TransactionService.create_transaction(...)       [Eingangsbuchung: income]
            → PaymentRepository.create_transfer(transfer)      [Transfer-Verknuepfung speichern]

        RUECKGABE-KETTE:
            DB → PaymentRepository → PaymentService → payment_controller
            → View zeigt: "Umbuchung erfolgreich"

        WARUM ZWEI TRANSAKTIONEN?
            Konto A -500 (expense)  → Konto A Saldo sinkt um 500
            Konto B +500 (income)   → Konto B Saldo steigt um 500
            Transfer-Datensatz haengt an der Ausgangstransaktion (expense_tx).

        SICHERHEITSREGELN:
            - Umbuchung auf sich selbst: from_account == to_account → Fehler
            - Beide Konten muessen aktiv sein
            - Beide Konten muessen dem gleichen User gehoeren
              (verhindert Geldtransfer zu anderen Users)

        PAYLOAD-KEYS:
            - "from_account_id" (int)    → Pflichtfeld: Quellkonto
            - "to_account_id" (int)      → Pflichtfeld: Zielkonto
            - "amount" (float/str)       → Pflichtfeld
            - "date" (date/str, opt.)    → Default: heute
            - "category_id" (int, opt.)  → Default: 9 (Demo-Kategorie)

        Args:
            payload: Dictionary aus Controller/UI.

        Returns:
            Das gespeicherte Transfer-Objekt.

        Raises:
            ValueError: Bei ungueltigem Betrag, gleichen Konten, fremden Konten,
                        inaktiven Konten oder unzureichendem Saldo.
            KeyError: Wenn eines der Konten nicht existiert.
        """
        from_account_id = int(payload["from_account_id"])
        to_account_id = int(payload["to_account_id"])
        amount = float(payload["amount"])
        category_id = int(payload.get("category_id", 9))

        validate_positive_amount(amount)

        # Schutz vor Eingabefehler: Umbuchung auf sich selbst ergibt keinen Sinn.
        if from_account_id == to_account_id:
            raise ValueError("Umbuchung ungueltig: Quell- und Zielkonto duerfen nicht identisch sein")

        with Session(engine) as session:
            account_repository = AccountRepository(session)
            from_account = account_repository.get_by_id(from_account_id)
            to_account = account_repository.get_by_id(to_account_id)
            if from_account is None:
                raise KeyError(f"Konto {from_account_id} nicht gefunden")
            if to_account is None:
                raise KeyError(f"Konto {to_account_id} nicht gefunden")
            # Beide Konten muessen aktiv sein.
            if from_account.status != "aktiv":
                raise ValueError("Quellkonto ist nicht aktiv")
            if to_account.status != "aktiv":
                raise ValueError("Zielkonto ist nicht aktiv")
            # Ownership-Regel: Nur zwischen eigenen Konten.
            if from_account.user_id != to_account.user_id:
                raise ValueError("Umbuchung nur zwischen eigenen Konten erlaubt")
            # Saldo-Pruefung.
            if from_account.balance < amount:
                raise ValueError("Unzureichender Kontosaldo")

        # Ausgangsbuchung (expense): Quellkonto wird belastet.
        expense_tx = transaction_service.create_transaction(
            {
                "amount": amount,
                "type": "expense",
                "date": payload.get("date", date.today()),
                "category_id": category_id,
                "account_id": from_account_id,
                "note": "Kontoumbuchung (Ausgang)",
            }
        )

        # Eingangsbuchung (income): Zielkonto wird gutgeschrieben.
        transaction_service.create_transaction(
            {
                "amount": amount,
                "type": "income",
                "date": payload.get("date", date.today()),
                "category_id": category_id,
                "account_id": to_account_id,
                "note": "Kontoumbuchung (Eingang)",
            }
        )

        with Session(engine) as session:
            payment_repository = PaymentRepository(session)
            # Transfer-Datensatz haengt an der Ausgangstransaktion (expense).
            # Das erlaubt der UI, die Umbuchung anhand der Ausgangstransaktion zu finden.
            transfer = Transfer(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                status="success",
                transaction_id=expense_tx.transaction_id,
            )
            return payment_repository.create_transfer(transfer)

    def generate_statement(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
    ) -> str:
        """Erzeugt einen einfachen PDF-Kontoauszug fuer einen Zeitraum.

        AUFRUF-KETTE:
            payment_controller.generate_statement(account_id, start_date, end_date)
            → PaymentService.generate_statement(account_id, start_date, end_date)
            → validate_date_range(start_date, end_date)
            → AccountRepository.get_by_id(account_id)        [Konto laden]
            → session.get(User, account.user_id)              [User-Name laden]
            → PaymentRepository.list_account_transactions_in_range(...)  [Buchungen laden]
            → _write_simple_pdf(file_path, lines)             [PDF schreiben]

        RUECKGABE-KETTE:
            str (Dateipfad) → payment_controller
            → View bietet Download an

        ABLAGEORT:
            Die PDF wird in `statements/` gespeichert (automatisch erstellt).
            Dateiname: `statement_{account_id}_{start}_{end}.pdf`
            Beispiel: `statements/statement_3_20260501_20260531.pdf`

        WARUM OHNE EXTERNE PDF-LIBRARY?
            Demo-Projekt: minimale Abhaengigkeiten. Der PDF-Standard ist offen,
            einfache Texte lassen sich "von Hand" schreiben. _write_simple_pdf
            erzeugt eine gueltiges PDF-1.4-Dokument mit einer Seite.

        Args:
            account_id: Datenbank-ID des Kontos fuer den Auszug.
            start_date: Erster Tag des Zeitraums (inklusive).
            end_date: Letzter Tag des Zeitraums (inklusive).

        Returns:
            Dateipfad zur erzeugten PDF-Datei als String.

        Raises:
            ValueError: Wenn der Datumsbereich ungueltig ist.
            KeyError: Wenn das Konto nicht existiert.
        """
        validate_date_range(start_date, end_date)

        with Session(engine) as session:
            account_repository = AccountRepository(session)
            payment_repository = PaymentRepository(session)

            account = account_repository.get_by_id(account_id)
            if account is None:
                raise KeyError(f"Konto {account_id} nicht gefunden")

            # User-Name fuer den Auszugs-Kopf laden.
            from src.domain.models import User
            user = session.get(User, account.user_id)
            user_name = f"{user.first_name} {user.last_name}" if user else "Unbekannt"
            account_type_label = "Sparkonto" if account.account_type == "spar" else "Privatkonto"
            account_iban = (account.iban or "").upper()

            # Alle Buchungen des Kontos im Zeitraum laden (aufsteigend sortiert = chronologisch).
            transactions = payment_repository.list_account_transactions_in_range(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
            )

        # PDF-Inhalt als Textzeilen vorbereiten.
        lines = [
            "BetterBank",
            "",
            f"Kontoinhaber: {user_name}",
            f"IBAN: {account_iban}",
            f"Kontotyp: {account_type_label}",
            f"Zeitraum: {format_date_dmy(start_date)} bis {format_date_dmy(end_date)}",
            f"Waehrung: {CURRENCY_CODE}",
            "",
        ]
        for transaction in transactions:
            # format_date_dmy: date(2026,5,1) → "01.05.2026"
            # format_transaction_type: "expense" → "Ausgabe", "income" → "Einnahme"
            lines.append(
                f"{format_date_dmy(transaction.date)} | "
                f"{format_transaction_type(transaction.type)} | "
                f"{transaction.amount:.2f} {CURRENCY_CODE} | "
                f"{transaction.note or ''}"
            )

        # Ausgabeverzeichnis erstellen (falls nicht vorhanden) und PDF schreiben.
        output_dir = Path("statements")
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / (
            f"statement_{account_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
        )
        self._write_simple_pdf(file_path, lines)
        return str(file_path)

    def _write_simple_pdf(self, file_path: Path, lines: list[str]) -> None:
        """Schreibt ein minimales PDF mit Textzeilen (ohne externe Library).

        WIE FUNKTIONIERT EIN PDF "VON HAND"?
            Ein PDF-Dokument besteht aus Objekten (Catalog, Pages, Page, Font, Content).
            Jedes Objekt wird mit "N 0 obj ... endobj" markiert.
            Am Ende steht eine XRef-Tabelle mit den Byte-Offsets aller Objekte,
            damit PDF-Reader sie schnell finden koennen.

        OBJEKTE IN DIESEM PDF:
            1: Catalog   → Einstiegspunkt des PDFs
            2: Pages     → Liste aller Seiten (hier: 1 Seite)
            3: Page      → Die Seite (A4: 595x842 Punkte)
            4: Font      → Helvetica (eingebaut, keine externe Schrift noetig)
            5: Stream    → Der eigentliche Textinhalt

        TEXT-BEFEHLE (PDF-Syntax):
            BT               → Begin Text
            /F1 10 Tf        → Schrift Helvetica, Groesse 10
            50 780 Td        → Position: 50 von links, 780 von unten
            (text) Tj        → Text ausgeben
            0 -14 Td         → 14 Punkte nach unten (naechste Zeile)
            ET               → End Text

        ENCODING (CP1252):
            WinAnsi/CP1252 ist der Standard fuer einfache deutsche Texte in PDFs.
            Unbekannte Zeichen werden durch `errors="replace"` ersetzt.

        Args:
            file_path: Pfad zur zu erstellenden PDF-Datei.
            lines: Textzeilen, die untereinander ausgegeben werden.
        """
        # Bestimmte Zeichen muessen in PDF-Strings escaped werden.
        escaped_lines = [
            line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            for line in lines
        ]

        # PDF-Content-Stream aufbauen.
        text_commands = ["BT /F1 10 Tf 50 780 Td"]
        for line in escaped_lines:
            text_commands.append(f"({line}) Tj")
            text_commands.append("0 -14 Td")   # Naechste Zeile: 14 Punkte nach unten.
        text_commands.append("ET")

        stream_data = "\n".join(text_commands).encode("cp1252", errors="replace")

        # PDF-Objekte zusammenstellen.
        objects: list[bytes] = []
        objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        objects.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
        objects.append(
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        )
        objects.append(
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >> endobj\n"
        )
        objects.append(
            f"5 0 obj << /Length {len(stream_data)} >> stream\n".encode("ascii")
            + stream_data
            + b"\nendstream endobj\n"
        )

        # Byte-Offsets berechnen (fuer XRef-Tabelle).
        content = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(content))
            content.extend(obj)

        # XRef-Tabelle: PDF-Reader braucht sie, um Objekte schnell zu finden.
        xref_start = len(content)
        content.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        content.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

        content.extend(
            (
                "trailer << /Size "
                + str(len(offsets))
                + " /Root 1 0 R >>\nstartxref\n"
                + str(xref_start)
                + "\n%%EOF\n"
            ).encode("ascii")
        )

        file_path.write_bytes(bytes(content))


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.payment_service import payment_service`
payment_service = PaymentService()
