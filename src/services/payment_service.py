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

from datetime import date, timedelta
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

        PDF-GENERIERUNG MIT fpdf2:
            _write_statement_pdf() verwendet die fpdf2-Library fuer ein
            formatiertes A4-PDF mit Header-Balken, Transaktions-Tabelle,
            Eroeffnungs-/Schlusssaldo und Fusstext.

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

            from src.domain.models import User
            user = session.get(User, account.user_id)
            user_name = f"{user.first_name} {user.last_name}" if user else "Unbekannt"
            user_address = (getattr(user, "address", None) or "") if user else ""
            account_type_label = "Sparkonto" if account.account_type == "spar" else "Privatkonto"
            account_iban = (account.iban or "").upper()

            transactions = payment_repository.list_account_transactions_in_range(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
            )

            # Eroeffnungssaldo: alle Buchungen vor dem Startdatum aufsummieren.
            pre_transactions = payment_repository.list_account_transactions_in_range(
                account_id=account_id,
                start_date=date(2000, 1, 1),
                end_date=start_date - timedelta(days=1),
            )
            opening_balance = sum(
                t.amount if t.type == "income" else -t.amount
                for t in pre_transactions
            )

            # Fallback-Texte fuer leere Notizen innerhalb der Session bestimmen,
            # da nach Schliessen der Session keine Beziehungen mehr nachgeladen werden.
            tx_ids = [t.transaction_id for t in transactions]
            from sqlmodel import select as _select, col
            if tx_ids:
                payment_tx_ids = set(session.exec(
                    _select(Payment.transaction_id).where(col(Payment.transaction_id).in_(tx_ids))
                ).all())
                transfer_tx_ids = set(session.exec(
                    _select(Transfer.transaction_id).where(col(Transfer.transaction_id).in_(tx_ids))
                ).all())
            else:
                payment_tx_ids = set()
                transfer_tx_ids = set()

            note_display: dict[int, str] = {}
            for t in transactions:
                if t.note:
                    note_display[t.transaction_id] = t.note
                elif t.transaction_id in payment_tx_ids:
                    note_display[t.transaction_id] = "Inlandszahlung"
                elif t.transaction_id in transfer_tx_ids:
                    note_display[t.transaction_id] = "Umbuchung"
                else:
                    note_display[t.transaction_id] = "Gutschrift" if t.type == "income" else "Lastschrift"

        output_dir = Path("statements")
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / (
            f"statement_{account_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
        )
        self._write_statement_pdf(
            file_path=file_path,
            user_name=user_name,
            user_address=user_address,
            account_iban=account_iban,
            account_type_label=account_type_label,
            start_date=start_date,
            end_date=end_date,
            opening_balance=opening_balance,
            transactions=transactions,
            note_display=note_display,
        )
        return str(file_path)

    def _write_statement_pdf(
        self,
        file_path: Path,
        user_name: str,
        user_address: str,
        account_iban: str,
        account_type_label: str,
        start_date: date,
        end_date: date,
        opening_balance: float,
        transactions: list,
        note_display: dict | None = None,
    ) -> None:
        """Erstellt einen formatierten PDF-Kontoauszug mit fpdf2."""
        from fpdf import FPDF

        NAVY = (26, 35, 126)
        NAVY_LIGHT = (232, 234, 246)
        GRAY = (110, 110, 110)
        DARK = (30, 30, 30)
        COL_W = [22, 73, 25, 25, 25]
        ROW_H = 6

        def fmt(amount: float) -> str:
            return f"{amount:,.2f}".replace(",", " ")

        def safe(text: str) -> str:
            return (text
                    .replace("–", "-").replace("—", "-")
                    .replace("’", "'").replace("“", '"').replace("”", '"'))

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(20, 15, 20)
        pdf.set_auto_page_break(auto=True, margin=25)
        pdf.add_page()

        # ── HEADER-BALKEN ────────────────────────────────────────────
        pdf.set_fill_color(*NAVY)
        pdf.rect(0, 0, 210, 24, "F")
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 7)
        pdf.cell(190, 10, "BetterBank", align="R")

        # ── BANK-INFO (links) ────────────────────────────────────────
        pdf.set_text_color(*GRAY)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(20, 30)
        pdf.multi_cell(70, 4.5, "BetterBank AG\nKundenservice\nInland: 0844 840 140\nAusland: +41 44 293 95 95\nwww.betterbank.ch")

        # ── KONTOBEZEICHNUNG ─────────────────────────────────────────
        pdf.set_xy(20, 60)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*DARK)
        pdf.cell(170, 9, safe(account_type_label))
        pdf.ln(9)

        pdf.set_x(20)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*NAVY)
        pdf.cell(170, 6, f"Kontoauszug {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
        pdf.ln(10)

        # ── KONTODETAILS (inkl. Kontoinhaber) ────────────────────────
        details = [
            ("Kontoinhaber", safe(user_name)),
            ("IBAN", account_iban),
            ("Datum", date.today().strftime("%d.%m.%Y")),
        ]
        for label, value in details:
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*GRAY)
            pdf.cell(28, 5, label)
            pdf.set_text_color(*DARK)
            pdf.cell(142, 5, safe(value))
            pdf.ln(5)

        pdf.ln(6)

        # ── TABELLEN-HEADER ──────────────────────────────────────────
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_x(20)
        for i, (header, w) in enumerate(zip(["Datum", "Text", "Gutschrift", "Lastschrift", "Saldo"], COL_W)):
            pdf.cell(w, ROW_H, header, fill=True, align="L" if i <= 1 else "R")
        pdf.ln()

        # ── EROEFFNUNGSSALDO ─────────────────────────────────────────
        opening_date = (start_date - timedelta(days=1)).strftime("%d.%m.%Y")
        pdf.set_fill_color(*NAVY_LIGHT)
        pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_x(20)
        pdf.cell(COL_W[0], ROW_H, opening_date, fill=True)
        pdf.cell(COL_W[1], ROW_H, "Kontostand", fill=True)
        pdf.cell(COL_W[2], ROW_H, "", fill=True)
        pdf.cell(COL_W[3], ROW_H, "", fill=True)
        pdf.cell(COL_W[4], ROW_H, fmt(opening_balance), fill=True, align="R")
        pdf.ln()

        # ── TRANSAKTIONSZEILEN ───────────────────────────────────────
        saldo = opening_balance
        for i, txn in enumerate(transactions):
            fill = i % 2 == 0
            pdf.set_fill_color(*(NAVY_LIGHT if fill else (255, 255, 255)))
            if txn.type == "income":
                gutschrift, lastschrift = fmt(txn.amount), ""
                saldo += txn.amount
            else:
                gutschrift, lastschrift = "", fmt(txn.amount)
                saldo -= txn.amount
            pdf.set_text_color(*DARK)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_x(20)
            pdf.cell(COL_W[0], ROW_H, txn.date.strftime("%d.%m.%Y"), fill=fill)
            tx_text = (note_display or {}).get(txn.transaction_id) or txn.note or ""
            pdf.cell(COL_W[1], ROW_H, safe(tx_text[:38]), fill=fill)
            pdf.cell(COL_W[2], ROW_H, gutschrift, fill=fill, align="R")
            pdf.cell(COL_W[3], ROW_H, lastschrift, fill=fill, align="R")
            pdf.cell(COL_W[4], ROW_H, fmt(saldo), fill=fill, align="R")
            pdf.ln()

        if not transactions:
            pdf.set_x(20)
            pdf.set_text_color(*GRAY)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(170, ROW_H, "Keine Transaktionen in diesem Zeitraum.")
            pdf.ln()

        # ── TRENNLINIE ───────────────────────────────────────────────
        pdf.set_draw_color(*NAVY)
        pdf.set_line_width(0.4)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(2)

        # ── TOTAL-ZEILE ──────────────────────────────────────────────
        total_g = sum(t.amount for t in transactions if t.type == "income")
        total_l = sum(t.amount for t in transactions if t.type != "income")
        pdf.set_text_color(*GRAY)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_x(20)
        pdf.cell(COL_W[0], 5, "")
        pdf.cell(COL_W[1], 5, "Total")
        pdf.cell(COL_W[2], 5, fmt(total_g), align="R")
        pdf.cell(COL_W[3], 5, fmt(total_l), align="R")
        pdf.cell(COL_W[4], 5, "")
        pdf.ln(2)

        # ── SCHLUSSSALDO (fett) ──────────────────────────────────────
        pdf.set_x(20)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*DARK)
        pdf.cell(COL_W[0], 7, end_date.strftime("%d.%m.%Y"))
        pdf.cell(COL_W[1], 7, "Kontostand")
        pdf.cell(COL_W[2], 7, "")
        pdf.cell(COL_W[3], 7, "")
        pdf.cell(COL_W[4], 7, fmt(saldo), align="R")
        pdf.ln(12)

        # ── FUSSTEXT & SEITENZAHL ─────────────────────────────────────
        # auto_page_break deaktivieren, damit Fussbereich keine neue Seite erzeugt.
        pdf.set_auto_page_break(auto=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(20, pdf.h - 38)
        pdf.multi_cell(
            170, 5,
            "Bitte ueberprufen Sie den Kontoauszug. Ohne Ihren Gegenbericht "
            "innert 30 Tagen gilt er als genehmigt.\n\nFreundliche Gruesse\nBetterBank AG",
        )
        pdf.set_xy(20, pdf.h - 12)
        pdf.cell(170, 5, f"Seite {pdf.page_no()}", align="R")

        pdf.output(str(file_path))


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.payment_service import payment_service`
payment_service = PaymentService()
