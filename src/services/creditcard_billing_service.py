from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.data_access.db import engine
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import Category, CreditCard
from src.services.transaction_service import transaction_service


# Implementiert die Geschaeftslogik fuer Kreditkarten-Monatsabschluss.
class CreditCardBillingService:
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
