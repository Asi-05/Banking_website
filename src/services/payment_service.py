from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.payment_repository import PaymentRepository
from src.domain.models import Payment, Transfer
from src.services.transaction_service import transaction_service
from src.utils.validators import validate_date_range, validate_iban, validate_positive_amount


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
			from_account = AccountRepository.get_by_id(session, from_account_id)
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
			payment = Payment(
				target_iban=target_iban,
				purpose=purpose,
				status="success",
				transaction_id=transaction.transaction_id,
			)
			return PaymentRepository.create_payment(session, payment)

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
			from_account = AccountRepository.get_by_id(session, from_account_id)
			to_account = AccountRepository.get_by_id(session, to_account_id)
			if from_account is None:
				raise KeyError(f"Konto {from_account_id} nicht gefunden")
			if to_account is None:
				raise KeyError(f"Konto {to_account_id} nicht gefunden")
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
			transfer = Transfer(
				from_account_id=from_account_id,
				to_account_id=to_account_id,
				status="success",
				transaction_id=expense_tx.transaction_id,
			)
			return PaymentRepository.create_transfer(session, transfer)

	# Generiert einen einfachen PDF-Kontoauszug fuer einen Zeitraum.
	def generate_statement(
		self,
		account_id: int,
		start_date: date,
		end_date: date,
	) -> str:
		validate_date_range(start_date, end_date)

		with Session(engine) as session:
			account = AccountRepository.get_by_id(session, account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			transactions = PaymentRepository.list_account_transactions_in_range(
				session,
				account_id=account_id,
				start_date=start_date,
				end_date=end_date,
			)

		lines = [
			f"Kontoauszug Konto {account_id}",
			f"Zeitraum: {start_date.isoformat()} bis {end_date.isoformat()}",
			"",
		]
		for transaction in transactions:
			lines.append(
				f"{transaction.date.isoformat()} | {transaction.type} | {transaction.amount:.2f} | {transaction.note or ''}"
			)

		output_dir = Path("statements")
		output_dir.mkdir(parents=True, exist_ok=True)
		file_path = output_dir / (
			f"statement_{account_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
		)
		self._write_simple_pdf(file_path, lines)
		return str(file_path)

	# Schreibt ein minimales, gueltiges PDF mit Textinhalt.
	def _write_simple_pdf(self, file_path: Path, lines: list[str]) -> None:
		escaped_lines = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
		text_commands = ["BT /F1 10 Tf 50 780 Td"]
		for line in escaped_lines:
			text_commands.append(f"({line}) Tj")
			text_commands.append("0 -14 Td")
		text_commands.append("ET")
		stream_data = "\n".join(text_commands).encode("latin-1", errors="replace")

		objects: list[bytes] = []
		objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
		objects.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
		objects.append(
			b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
		)
		objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
		objects.append(
			f"5 0 obj << /Length {len(stream_data)} >> stream\n".encode("ascii")
			+ stream_data
			+ b"\nendstream endobj\n"
		)

		content = bytearray(b"%PDF-1.4\n")
		offsets = [0]
		for obj in objects:
			offsets.append(len(content))
			content.extend(obj)

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


payment_service = PaymentService()
