"""src.services.payment_service

Diese Datei gehoert zur **Service-Schicht**.

Die Service-Schicht enthaelt fachliche Regeln (Validierungen, erlaubte Zustaende,
Orchestrierung mehrerer Schritte) und nutzt Repositories fuer Datenbankzugriffe.

In diesem Modul geht es um drei zusammenhaengende Themen:

- **Zahlungen**: Eine externe Zahlung wird als normale Transaktion ("expense")
	verbucht und zusaetzlich als `Payment`-Datensatz gespeichert.
- **Umbuchungen**: Eine interne Umbuchung zwischen zwei eigenen Konten wird als
	*zwei* Transaktionen umgesetzt (Ausgang = expense, Eingang = income) und als
	`Transfer` referenziert. (Wichtig: Reporting/Dashboard muss Transfers passend
	behandeln, damit sie nicht aus Versehen doppelt als "Einnahme" und "Ausgabe"
	interpretiert werden.)
- **Kontoauszug**: Es wird ein sehr einfacher PDF-Auszug erzeugt, bewusst ohne
	externe PDF-Bibliothek. Das ist didaktisch nuetzlich, aber kein vollwertiger
	PDF-Renderer.

Das Modul arbeitet eng mit folgenden Komponenten zusammen:

- `TransactionService`: erzeugt die eigentlichen Buchungen und passt Salden an.
- `PaymentRepository`: speichert/liest `Payment` und `Transfer` sowie die
	Transaktionsliste fuer den Auszug.
- `AccountRepository`: stellt sicher, dass das betroffene Konto existiert und
	zulaessig ist.
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
	"""Fachlogik fuer Zahlungen, Umbuchungen und Kontoauszuege.

	Die Methoden in dieser Klasse sind bewusst "duenn" in der Datenbank-Logik:
	- Validierungen und fachliche Regeln passieren hier.
	- Persistenz-Details liegen in den Repositories.
	- Die eigentliche Buchung (Saldoaenderung) wird ueber `TransactionService`
	  zentralisiert, damit es eine *einheitliche* Quelle fuer die Kontostands-Logik gibt.
	"""

	# Erstellt eine Inlandszahlung als Transaction plus Payment-Spezialisierung.
	def create_payment(self, payload: dict) -> Payment:
		"""Erstellt eine Zahlung (Ausgabe) von einem eigenen Konto zu einer Ziel-IBAN.

		Ablauf (vereinfacht):
		1) Payload lesen und Grundvalidierungen ausfuehren (IBAN, Betrag).
		2) Quellkonto pruefen (existiert, ausreichender Saldo).
		3) Eine Transaktion ("expense") ueber `TransactionService` erzeugen.
		4) Den zusaetzlichen `Payment`-Datensatz speichern, der die "Zahlungsdetails"
		   (Ziel-IBAN, Verwendungszweck, Status) enthaelt.

		Args:
			payload: Eingabedaten aus UI/Controller. Erwartete Keys:
				- `target_iban` (str)
				- `amount` (float/str)
				- `from_account_id` (int/str)
				- `purpose` (str)
				- `category_id` (int/str)
				Optional: `date` (date oder ISO-String; wird im TransactionService normalisiert)

		Returns:
			Das gespeicherte `Payment`-Objekt (inkl. gesetzter IDs).

		Raises:
			KeyError: Wenn das Quellkonto nicht existiert.
			ValueError: Bei ungueltiger IBAN, ungueltigem Betrag oder zu wenig Saldo.
		"""
		target_iban = str(payload["target_iban"])
		amount = float(payload["amount"])
		from_account_id = int(payload["from_account_id"])
		purpose = str(payload["purpose"])
		category_id = int(payload["category_id"])

		# Validierungen passieren moeglichst frueh, damit wir keine DB-Session fuer
		# offensichtlich falsche Eingaben oeffnen.
		validate_iban(target_iban)
		validate_positive_amount(amount)

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			from_account = account_repository.get_by_id(from_account_id)
			if from_account is None:
				raise KeyError(f"Konto {from_account_id} nicht gefunden")
			# Fachregel: Eine Zahlung darf das Konto nicht ueberziehen.
			if from_account.balance < amount:
				raise ValueError("Unzureichender Kontosaldo")

		# Die eigentliche Buchung (inkl. Saldologik) passiert zentral im
		# TransactionService. Das verhindert, dass jede Feature-Klasse "ihre eigene"
		# Saldo-Implementierung erfindet.
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
			# `Payment` ist eine Spezialisierung zur Transaktion: Details, die nur fuer
			# Zahlungen relevant sind, liegen hier und nicht in der Basistabelle.
			payment = Payment(
				target_iban=target_iban,
				purpose=purpose,
				status="success",
				transaction_id=transaction.transaction_id,
			)
			return payment_repository.create_payment(payment)

	# Fuehrt eine Umbuchung zwischen zwei eigenen Konten aus.
	def create_transfer(self, payload: dict) -> Transfer:
		"""Fuehrt eine Umbuchung zwischen zwei eigenen Konten aus.

		Wichtiges Konzept: Eine Umbuchung ist fachlich *ein* Vorgang, technisch aber
		werden zwei Buchungen benoetigt:
		- Ausgang: `expense` auf dem Quellkonto
		- Eingang: `income` auf dem Zielkonto

		Der `Transfer`-Datensatz referenziert dabei die Ausgangstransaktion
		(`transaction_id`), damit man den Vorgang in der UI wiederfinden kann.

		Args:
			payload: Eingabedaten aus UI/Controller. Erwartete Keys:
				- `from_account_id` (int/str)
				- `to_account_id` (int/str)
				- `amount` (float/str)
				Optional: `date` (date oder ISO-String)
				Optional: `category_id` (int/str) – Default wird verwendet, falls nichts kommt.

		Returns:
			Das gespeicherte `Transfer`-Objekt.

		Raises:
			ValueError: Bei ungueltigem Betrag, gleichen Konten, fremden Konten,
				inaktiven Konten oder zu wenig Saldo.
			KeyError: Wenn eines der Konten nicht existiert.
		"""
		from_account_id = int(payload["from_account_id"])
		to_account_id = int(payload["to_account_id"])
		amount = float(payload["amount"])
		category_id = int(payload.get("category_id", 9))

		validate_positive_amount(amount)
		# Schutz vor Eingabefehler: Umbuchung "auf sich selbst" ergibt fachlich keinen Sinn.
		if from_account_id == to_account_id:
			raise ValueError("Umbuchung ungueltig: Quell- und Zielkonto duerfen nicht identisch sein")

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			# DB-Reads: beide Konten muessen existieren und zueinander passen.
			from_account = account_repository.get_by_id(from_account_id)
			to_account = account_repository.get_by_id(to_account_id)
			if from_account is None:
				raise KeyError(f"Konto {from_account_id} nicht gefunden")
			if to_account is None:
				raise KeyError(f"Konto {to_account_id} nicht gefunden")
			# Fachregel: Umbuchungen nur zwischen aktiven Konten.
			if from_account.status != "aktiv":
				raise ValueError("Quellkonto ist nicht aktiv")
			if to_account.status != "aktiv":
				raise ValueError("Zielkonto ist nicht aktiv")
			# Sicherheits-/Ownership-Regel: Man darf nur zwischen eigenen Konten umbuchen.
			if from_account.user_id != to_account.user_id:
				raise ValueError("Umbuchung nur zwischen eigenen Konten erlaubt")
			# Kein Ueberziehen.
			if from_account.balance < amount:
				raise ValueError("Unzureichender Kontosaldo")

		# Ausgangsbuchung (expense): reduziert den Saldo.
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
		# Eingangsbuchung (income): erhoeht den Saldo.
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
			# `Transfer` haengt als "Zusatzinformation" an der Ausgangstransaktion.
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
		"""Erzeugt einen sehr einfachen PDF-Kontoauszug fuer einen Zeitraum.

		Die Transaktionen werden aus der Datenbank gelesen und anschliessend als
		Textzeilen in eine minimale PDF-Struktur geschrieben.

		Hinweis: Das ist bewusst "low level" (ohne externe PDF-Library). Es reicht
		fuer einen einfachen Auszug, deckt aber nicht alle Sonderfaelle (Layout,
		mehrseitige Dokumente, Schriften, etc.) ab.

		Args:
			account_id: Das Konto, fuer das der Auszug erstellt wird.
			start_date: Startdatum (inklusive).
			end_date: Enddatum (inklusive).

		Returns:
			Den Dateipfad zur erzeugten PDF-Datei als String.

		Raises:
			ValueError: Wenn der Datumsbereich ungueltig ist.
			KeyError: Wenn das Konto nicht existiert.
		"""
		validate_date_range(start_date, end_date)

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			payment_repository = PaymentRepository(session)

			# DB-Read: Konto muss existieren.
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")

			# DB-Read: Besitzer-Name fuer den Kopf des Kontoauszugs.
			# (Der Import liegt hier, weil `User` nicht auf Modulebene benoetigt wird.)
			from src.domain.models import User
			user = session.get(User, account.user_id)
			user_name = f"{user.first_name} {user.last_name}" if user else "Unbekannt"
			account_type_label = "Sparkonto" if account.account_type == "spar" else "Privatkonto"
			account_iban = (account.iban or "").upper()

			# DB-Query: Alle Buchungen fuer den Zeitraum (inkl. Kategorien/Notizen je nach Repository).
			transactions = payment_repository.list_account_transactions_in_range(
				account_id=account_id,
				start_date=start_date,
				end_date=end_date,
			)

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
			# UI-/Report-Formatierung (DD.MM.YYYY und lesbarer Typ).
			lines.append(
				f"{format_date_dmy(transaction.date)} | {format_transaction_type(transaction.type)} | {transaction.amount:.2f} {CURRENCY_CODE} | {transaction.note or ''}"
			)

		# Ablageort: Im Projektordner gibt es ein `statements/`-Verzeichnis fuer Auszuege.
		output_dir = Path("statements")
		output_dir.mkdir(parents=True, exist_ok=True)
		file_path = output_dir / (
			f"statement_{account_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
		)
		# PDF wird bewusst "von Hand" geschrieben, um keine externe Abhaengigkeit zu brauchen.
		self._write_simple_pdf(file_path, lines)
		return str(file_path)

	# Schreibt ein minimales, gueltiges PDF mit Textinhalt.
	def _write_simple_pdf(self, file_path: Path, lines: list[str]) -> None:
		"""Schreibt ein minimales PDF mit Textzeilen.

		Technische Idee:
		- Wir erstellen eine PDF-Datei mit genau *einer* Seite.
		- Der Seiteninhalt ist ein Text-Stream mit einfachen PDF-Textbefehlen.
		- Danach schreiben wir eine XRef-Tabelle (Byte-Offets), damit PDF-Reader die
		  Objekte schnell finden koennen.

		Das ist absichtlich minimal und eignet sich gut zum Verstehen von
		Dateiformaten, ersetzt aber keine professionelle PDF-Erzeugung.

		Args:
			file_path: Zielpfad fuer die PDF-Datei.
			lines: Textzeilen, die untereinander in die PDF geschrieben werden.
		"""
		# PDF-Strings muessen bestimmte Zeichen escapen. Ohne Escape koennen
		# Backslashes oder Klammern die PDF-Syntax kaputt machen.
		escaped_lines = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
		# Start einer Textsektion (BT...ET) in der PDF-Content-Stream-Syntax.
		text_commands = ["BT /F1 10 Tf 50 780 Td"]
		for line in escaped_lines:
			text_commands.append(f"({line}) Tj")
			# Naechste Zeile: wir gehen 14 Punkte nach unten.
			text_commands.append("0 -14 Td")
		text_commands.append("ET")

		# Encoding: WinAnsi/CP1252 passt zu `/Encoding /WinAnsiEncoding` und ist fuer
		# einfache deutsche Texte oft ausreichend. Unbekannte Zeichen werden ersetzt.
		stream_data = "\n".join(text_commands).encode("cp1252", errors="replace")

		objects: list[bytes] = []
		objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
		objects.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
		# Page-Objekt: verweist auf Ressourcen (Font) und auf den Content-Stream.
		objects.append(
			b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
		)
		# Font-Objekt: Wir nutzen die eingebaute Schrift Helvetica.
		objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> endobj\n")
		# Content-Stream: laenge + Streamdaten.
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
		# Jede Zeile in der XRef-Tabelle enthaelt den Byte-Offset eines Objekts.
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
