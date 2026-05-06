"""src.data_access.repositories.payment_repository

Repository fuer Zahlungs-Zusatzdaten (Payment/Transfer).

Dieses Repository kapselt DB-Zugriffe fuer Zahlungsarten, die zusaetzliche
Felder zur Basis-Transaktion haben:

- `Payment`: Inlandszahlung mit Ziel-IBAN und Verwendungszweck
- `Transfer`: Umbuchung zwischen eigenen Konten

Die Basisdaten (Betrag, Datum, Typ, Kategorie, Quelle) liegen in `Transaction`.
Services erstellen zuerst eine `Transaction` und speichern danach das passende
Zusatzobjekt ueber dieses Repository.
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Payment, Transaction, Transfer


# Kapselt reine Datenbankzugriffe fuer Zahlungsobjekte.
class PaymentRepository:
	"""Datenbankzugriffe fuer `Payment`, `Transfer` und Konto-Transaktionslisten.

	Hinweis:
		`create_payment()` und `create_transfer()` committen die Session selbst.
	"""
	def __init__(self, session: Session):
		"""Initialisiert das Repository mit einer DB-Session.

		Args:
			session: Offene SQLModel-Session.
		"""
		self.session = session

	# Legt ein Payment-Objekt an und persistiert es.
	def create_payment(self, payment: Payment) -> Payment:
		"""Speichert ein `Payment`-Objekt (Zahlungs-Zusatzdaten).

		Args:
			payment: Das Payment-Objekt.

		Returns:
			Gespeichertes Payment (inkl. DB-generierter `payment_id`).
		"""
		self.session.add(payment)
		self.session.commit()
		self.session.refresh(payment)
		return payment

	# Legt ein Transfer-Objekt an und persistiert es.
	def create_transfer(self, transfer: Transfer) -> Transfer:
		"""Speichert ein `Transfer`-Objekt (Umbuchungs-Zusatzdaten).

		Args:
			transfer: Das Transfer-Objekt.

		Returns:
			Gespeicherter Transfer (inkl. DB-generierter `transfer_id`).
		"""
		self.session.add(transfer)
		self.session.commit()
		self.session.refresh(transfer)
		return transfer

	# Gibt alle kontobezogenen Transaktionen in einem Datumsbereich zurueck.
	def list_account_transactions_in_range(
		self,
		account_id: int,
		start_date: date,
		end_date: date,
	) -> list[Transaction]:
		"""Listet Transaktionen eines Kontos für einen Kontoauszug.

		Args:
			account_id: Das Konto, dessen Transaktionen geladen werden.
			start_date: Anfang des Zeitraums (inkl.).
			end_date: Ende des Zeitraums (inkl.).

		Returns:
			Liste der Transaktionen, sortiert von alt nach neu.
		"""
		# Query: Transaktionen dieses Kontos im Zeitraum. Aufsteigend sortieren,
		# damit ein PDF-Kontoauszug chronologisch lesbar ist.
		statement = (
			select(Transaction)
			.where(Transaction.account_id == account_id)
			.where(Transaction.date >= start_date)
			.where(Transaction.date <= end_date)
			.order_by(Transaction.date.asc(), Transaction.transaction_id.asc())
		)
		return list(self.session.exec(statement).all())
