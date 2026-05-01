from __future__ import annotations

from datetime import date
from pathlib import Path
from textwrap import TextWrapper

from fpdf import FPDF
from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.payment_repository import PaymentRepository
from src.domain.models import Payment, Transfer
from src.services.transaction_service import transaction_service
from src.utils.formatters import format_date_dmy, format_transaction_type
from src.utils.validators import validate_date_range, validate_iban, validate_positive_amount


CURRENCY_CODE = "CHF"


# Implementiert die Geschaeftslogik fuer Zahlungen, Umbuchungen und Auszuege.
class PaymentService:
	# Erstellt eine Inlandszahlung als Transaction plus Payment-Spezialisierung.
	def create_payment(self, payload: dict) -> Payment:
		target_iban = str(payload["target_iban"])
		amount = float(payload["amount"])
		from_account_id = int(payload["from_account_id"])
		purpose = str(payload["purpose"])
		category_id = int(payload["category_id"])

		validate_iban(target_iban)
		validate_positive_amount(amount)

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			from_account = account_repository.get_by_id(from_account_id)
			if from_account is None:
				raise KeyError(f"Konto {from_account_id} nicht gefunden")
			if from_account.balance < amount:
				raise ValueError("Unzureichender Kontosaldo")

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
			payment = Payment(
				target_iban=target_iban,
				purpose=purpose,
				status="success",
				transaction_id=transaction.transaction_id,
			)
			return payment_repository.create_payment(payment)

	# Fuehrt eine Umbuchung zwischen zwei eigenen Konten aus.
	def create_transfer(self, payload: dict) -> Transfer:
		from_account_id = int(payload["from_account_id"])
		to_account_id = int(payload["to_account_id"])
		amount = float(payload["amount"])
		category_id = int(payload.get("category_id", 9))

		validate_positive_amount(amount)
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
			if from_account.status != "aktiv":
				raise ValueError("Quellkonto ist nicht aktiv")
			if to_account.status != "aktiv":
				raise ValueError("Zielkonto ist nicht aktiv")
			if from_account.user_id != to_account.user_id:
				raise ValueError("Umbuchung nur zwischen eigenen Konten erlaubt")
			if from_account.balance < amount:
				raise ValueError("Unzureichender Kontosaldo")

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
			transfer = Transfer(
				from_account_id=from_account_id,
				to_account_id=to_account_id,
				status="success",
				transaction_id=expense_tx.transaction_id,
			)
			return payment_repository.create_transfer(transfer)

	# Generiert einen einfachen PDF-Kontoauszug fuer einen Zeitraum.
	def generate_statement(
		self,
		account_id: int,
		start_date: date,
		end_date: date,
	) -> str:
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
			account_type_label = "Sparkonto" if account.account_type == "spar" else "Privatkonto"
			account_iban = (account.iban or "").upper()
			transactions = payment_repository.list_account_transactions_in_range(
				account_id=account_id,
				start_date=start_date,
				end_date=end_date,
			)

		output_dir = Path("statements")
		output_dir.mkdir(parents=True, exist_ok=True)
		file_path = output_dir / (
			f"statement_{account_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
		)
		self._write_statement_pdf(file_path, user_name, account_iban, account_type_label, start_date, end_date, transactions)
		return str(file_path)

	# Schreibt einen strukturierten PDF-Kontoauszug mit FPDF2.
	def _write_statement_pdf(
		self,
		file_path: Path,
		user_name: str,
		account_iban: str,
		account_type_label: str,
		start_date: date,
		end_date: date,
		transactions: list,
	) -> None:
		pdf = FPDF(format="A4")
		pdf.set_auto_page_break(auto=True, margin=16)
		pdf.set_margins(15, 15, 15)
		pdf.add_page()

		pdf.set_font("Helvetica", "B", 16)
		pdf.cell(0, 10, "BetterBank Kontoauszug", ln=True)

		pdf.set_font("Helvetica", "", 11)
		pdf.cell(0, 8, f"Kontoinhaber: {user_name}", ln=True)
		pdf.cell(0, 8, f"IBAN: {account_iban}", ln=True)
		pdf.cell(0, 8, f"Kontotyp: {account_type_label}", ln=True)
		pdf.cell(0, 8, f"Zeitraum: {format_date_dmy(start_date)} bis {format_date_dmy(end_date)}", ln=True)
		pdf.cell(0, 8, f"Waehrung: {CURRENCY_CODE}", ln=True)

		pdf.ln(4)
		pdf.set_font("Helvetica", "B", 10)
		pdf.set_fill_color(235, 235, 235)
		pdf.cell(28, 8, "Datum", border=1, fill=True)
		pdf.cell(26, 8, "Typ", border=1, fill=True)
		pdf.cell(30, 8, "Betrag", border=1, fill=True, align="R")
		pdf.cell(0, 8, "Beschreibung", border=1, fill=True, ln=True)

		pdf.set_font("Helvetica", "", 10)
		if not transactions:
			pdf.cell(0, 8, "Keine Transaktionen im gewaehlteten Zeitraum.", border=1, ln=True)
		else:
			max_text_width = pdf.w - pdf.l_margin - pdf.r_margin
			for transaction in transactions:
				description = transaction.note or ""
				header_line = (
					f"Datum: {format_date_dmy(transaction.date)} | "
					f"Typ: {format_transaction_type(transaction.type)} | "
					f"Betrag: {transaction.amount:.2f} {CURRENCY_CODE}"
				)
				pdf.cell(0, 8, header_line, border=1, ln=True)
				for index, line in enumerate(self._split_statement_text(description, pdf, max_text_width)):
					prefix = "Beschreibung: " if index == 0 else ""
					pdf.cell(0, 8, f"{prefix}{line}", border=1, ln=True)
				pdf.ln(1)

		pdf.output(str(file_path))

	# Teilt Text in Zeilen auf, die sicher in die aktuelle PDF-Breite passen.
	def _split_statement_text(self, text: str, pdf: FPDF, max_width: float) -> list[str]:
		if not text:
			return [""]

		wrapped_lines = TextWrapper(
			width=200,
			break_long_words=True,
			break_on_hyphens=True,
		).wrap(text)
		result: list[str] = []
		for wrapped_line in wrapped_lines or [text]:
			result.extend(self._fit_text_to_width(wrapped_line, pdf, max_width))
		return result

	# Schneidet einen Text so auf, dass jede Teilzeile innerhalb der verfügbaren Breite liegt.
	def _fit_text_to_width(self, text: str, pdf: FPDF, max_width: float) -> list[str]:
		if not text:
			return [""]

		lines: list[str] = []
		remaining = text
		while remaining:
			cut = len(remaining)
			while cut > 0 and pdf.get_string_width(remaining[:cut]) > max_width:
				cut -= 1
			if cut == 0:
				cut = 1
			lines.append(remaining[:cut])
			remaining = remaining[cut:]
		return lines


payment_service = PaymentService()
