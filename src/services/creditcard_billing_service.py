from __future__ import annotations

import calendar
from datetime import date

from sqlmodel import Session, select

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import Category, CreditCard
from src.services.transaction_service import transaction_service


# Implementiert die Geschaeftslogik fuer Kreditkarten-Monatsabschluss.
class CreditCardBillingService:
	# Erzeugt fiktive historische Kreditkartenumsatze und stellt sie monatlich in Rechnung.
	def seed_historical_billing_demo(
		self,
		user_id: int,
		months_back: int = 3,
		transactions_per_month: int = 3,
		reference_date: date | None = None,
	) -> dict:
		"""
		Erzeugt Demo-Daten fuer vergangene Monate, damit die Abrechnungslogik sichtbar ist:
		1. Aktive Kreditkarten des Users laden
		2. Falls noetig, ein aktives Privatkonto als billing_account setzen
		3. Pro historischem Monat fiktive Kreditkarten-Transaktionen erstellen
		4. Zum Monatsende process_monthly_billing() ausfuehren

		Gibt eine Zusammenfassung mit Anzahl erzeugter Buchungen und Rechnungen zurueck.
		"""
		if months_back < 1:
			raise ValueError("months_back muss mindestens 1 sein")
		if transactions_per_month < 1:
			raise ValueError("transactions_per_month muss mindestens 1 sein")

		reference_date = reference_date or date.today()

		with Session(engine) as session:
			card_repository = CardRepository(session)
			account_repository = AccountRepository(session)
			category_repository = CategoryRepository(session)

			credit_cards = [
				card
				for card in card_repository.list_credit_by_user(user_id)
				if card.status == "aktiv"
			]
			if not credit_cards:
				raise ValueError("Keine aktive Kreditkarte fuer Demo-Abrechnung gefunden")

			# Fuer Demo-Umsaetze bevorzugen wir Freizeit, fallback auf erste verfuegbare Kategorie.
			category_id = self._resolve_demo_category_id(category_repository)

			# Ohne billing_account ist keine Monatsabrechnung moeglich.
			user_accounts = account_repository.list_by_user(user_id)
			active_private_account = next(
				(
					account
					for account in user_accounts
					if account.account_type == "privat" and account.status == "aktiv"
				),
				None,
			)
			if active_private_account is None:
				raise ValueError("Kein aktives Privatkonto fuer Kreditkarten-Abrechnung gefunden")

			updated_cards = 0
			for card in credit_cards:
				if card.billing_account_id is None:
					card.billing_account_id = active_private_account.account_id
					card_repository.save_credit(card)
					updated_cards += 1

		created_transactions = 0
		processed_billings = 0

		# Monatlich von alt -> neu erzeugen, damit Saldoaufbau und Abrechnung chronologisch sind.
		for offset in range(months_back, 0, -1):
			month_start = self._first_day_of_shifted_month(reference_date, -offset)
			month_end = self._last_day_of_month(month_start.year, month_start.month)

			with Session(engine) as session:
				card_repository = CardRepository(session)
				monthly_cards = [
					card
					for card in card_repository.list_credit_by_user(user_id)
					if card.status == "aktiv" and card.billing_account_id is not None
				]

			for card in monthly_cards:
				for tx_index in range(transactions_per_month):
					day = min(3 + (tx_index * 7), month_end.day - 1)
					tx_date = date(month_start.year, month_start.month, max(1, day))
					amount = 25.0 + float((offset * 10) + (tx_index * 5))
					transaction_service.create_transaction(
						{
							"amount": amount,
							"type": "expense",
							"date": tx_date,
							"category_id": category_id,
							"creditcard_id": card.creditcard_id,
							"note": (
								f"DEMO Kreditkartenumsatz {month_start.year}-{month_start.month:02d}"
							),
						}
					)
					created_transactions += 1

			processed_billings += self.process_monthly_billing(user_id, month_end)

		return {
			"user_id": user_id,
			"months_back": months_back,
			"transactions_per_month": transactions_per_month,
			"created_transactions": created_transactions,
			"processed_billings": processed_billings,
			"updated_cards_with_billing_account": updated_cards,
		}

	# Verarbeitet alle faelligen Kreditkarten-Monatsabrechnungen eines Users.
	def process_monthly_billing(self, user_id: int, reference_date: date) -> int:
		"""
		Prueft alle aktiven Kreditkarten des Users.
		Fuer jede faellige Karte mit balance > 0 und gesetztem billing_account_id:
		  1. Erstelle expense-Transaktion auf dem billing_account
		  2. Setze credit_card.balance = 0.0
		  3. Setze credit_card.last_billed = reference_date
		
		Gibt die Anzahl der verarbeiteten Kreditkarten zurueck.
		"""
		processed = 0
		
		with Session(engine) as session:
			card_repository = CardRepository(session)
			credit_cards = card_repository.list_credit_by_user(user_id)
		
		for credit_card in credit_cards:
			# Pruefe ob Abrechnung noetig ist
			if not self._is_billing_due(credit_card, reference_date):
				continue
			
			# Pruefe ob Karte aktiv ist
			if credit_card.status != "aktiv":
				continue
			
			# Pruefe ob balance > 0
			if credit_card.balance <= 0.0:
				continue
			
			# Pruefe ob billing_account_id gesetzt ist
			if credit_card.billing_account_id is None:
				continue
			
			try:
				# Finde die Kategorie "Sonstiges"
				with Session(engine) as session:
					category_repository = CategoryRepository(session)
					categories = category_repository.list_all()
					miscellaneous_category = categories[-1] if categories else None
					
					if miscellaneous_category is None:
						continue
					
					# Erstelle Transaktion
					transaction_service.create_transaction({
						"amount": credit_card.balance,
						"type": "expense",
						"date": reference_date,
						"category_id": miscellaneous_category.category_id,
						"account_id": credit_card.billing_account_id,
						"note": "Zahlung Kreditkarte",
					})
			except (ValueError, KeyError):
				# Fehlerbehandlung: bei Fehler (z.B. unzureichender Saldo) weitermachen
				continue
			
			# Aktualisiere Kreditkarte
			with Session(engine) as session:
				card_repository = CardRepository(session)
				reloaded = card_repository.get_credit_by_id(credit_card.creditcard_id)
				if reloaded is not None:
					reloaded.balance = 0.0
					reloaded.last_billed = reference_date
					card_repository.save_credit(reloaded)
			
			processed += 1
		
		return processed

	# Ermittelt eine Kategorie-ID fuer Demo-Buchungen (bevorzugt Freizeit).
	def _resolve_demo_category_id(self, category_repository: CategoryRepository) -> int:
		categories = category_repository.list_all()
		if not categories:
			raise ValueError("Keine Kategorien vorhanden")

		preferred = next((c for c in categories if c.name.lower() == "freizeit"), None)
		selected = preferred or categories[0]
		if selected.category_id is None:
			raise ValueError("Kategorie-ID nicht verfuegbar")
		return selected.category_id

	# Gibt den ersten Tag eines relativ verschobenen Monats zurueck.
	def _first_day_of_shifted_month(self, base_date: date, month_shift: int) -> date:
		total_month = (base_date.year * 12) + (base_date.month - 1) + month_shift
		year = total_month // 12
		month = (total_month % 12) + 1
		return date(year, month, 1)

	# Gibt den letzten Tag eines Monats zurueck.
	def _last_day_of_month(self, year: int, month: int) -> date:
		last_day = calendar.monthrange(year, month)[1]
		return date(year, month, last_day)
	
	# Prueft, ob ein einzelne Kreditkarte zum Referenzdatum faellig ist.
	def _is_billing_due(self, credit_card: CreditCard, reference_date: date) -> bool:
		"""
		Gibt True zurueck wenn noch keine Abrechnung fuer diesen Monat/Jahr erfolgte.
		Abrechnung ist faellig, wenn:
		  - last_billed is None ODER
		  - last_billed.month != reference_date.month ODER
		  - last_billed.year != reference_date.year
		"""
		if credit_card.last_billed is None:
			return True
		
		if credit_card.last_billed.month != reference_date.month:
			return True
		
		if credit_card.last_billed.year != reference_date.year:
			return True
		
		return False


creditcard_billing_service = CreditCardBillingService()
