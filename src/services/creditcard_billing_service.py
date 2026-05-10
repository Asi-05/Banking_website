"""src.services.creditcard_billing_service

Diese Datei gehoert zur **Service-Schicht**.

Sie implementiert die Monatsabrechnung fuer Kreditkarten.

Wichtige Begriffe in diesem Projekt:

- `CreditCard.balance` ist **nicht** ein Kontostand, sondern der aktuell
	**genutzte Kredit** (also der offene Betrag, der der Bank noch geschuldet ist).
- Eine Monatsabrechnung bedeutet: Offener Kredit wird vom *Abrechnungskonto*
	(`billing_account_id`) abgebucht und die Kreditkarten-`balance` wird wieder 0.

Warum ist das als eigener Service ausgelagert?

- Die Logik wird (aehnlich wie Dauerauftraege) beim Login oder zu einem
	Referenzdatum getriggert.
- Die Buchung selbst erfolgt ueber `TransactionService`, damit Validierungen
	und Saldoaenderungen konsistent sind.

Zusatz: `seed_historical_billing_demo()` erzeugt Demo-Umsaetze fuer vergangene
Monate. Das ist rein fuer Vorfuehrung/Tests gedacht und keine produktive Funktion.
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.card_repository import CardRepository
from src.data_access.repositories.category_repository import CategoryRepository
from src.domain.models import CreditCard
from src.services.transaction_service import transaction_service


# Implementiert die Geschaeftslogik fuer Kreditkarten-Monatsabschluss.
class CreditCardBillingService:
	"""Fachlogik fuer Kreditkarten-Abrechnungen (monatlich).

	Die Kernregel:
	- Pro Monat (Monat+Jahr) darf maximal *eine* Abrechnung pro Kreditkarte stattfinden.
	- Abgerechnet wird nur, wenn die Karte aktiv ist, ein Abrechnungskonto gesetzt ist
	  und ein offener Betrag (`balance`) existiert.
	"""

	# Erzeugt fiktive historische Kreditkartenumsatze und stellt sie monatlich in Rechnung.
	def seed_historical_billing_demo(
		self,
		user_id: int,
		months_back: int = 3,
		transactions_per_month: int = 3,
		reference_date: date | None = None,
	) -> dict:
		"""Erzeugt Demo-Umsaetze fuer vergangene Monate und rechnet sie ab.

		Diese Methode macht die Abrechnungslogik "sichtbar", auch wenn ein User
		gerade erst angelegt wurde und noch keine echten Kreditkartenumsatze hat.

		Ablauf:
		1) Aktive Kreditkarten des Users laden
		2) Falls noetig: ein aktives Privatkonto als `billing_account_id` setzen
		3) Pro Monat fiktive Kreditkarten-Transaktionen erzeugen (bauen `balance` auf)
		4) Am Monatsende `process_monthly_billing()` ausfuehren (baut `balance` wieder ab)

		Args:
			user_id: Besitzer der Kreditkarten.
			months_back: Anzahl Monate in der Vergangenheit (>= 1).
			transactions_per_month: Anzahl Demo-Umsaetze pro Monat (>= 1).
			reference_date: Basisdatum (Default: heute). Von dort aus werden Monate zurueck gerechnet.

		Returns:
			Zusammenfassung mit Anzahl erzeugter Umsaetze, verarbeiteter Abrechnungen
			und ggf. Karten, bei denen ein Billing-Account gesetzt wurde.
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

			# DB-Read: Nur aktive Kreditkarten sind fuer die Demo sinnvoll.
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
					# Wir setzen fuer die Demo ein Abrechnungskonto, damit `process_monthly_billing`
					# spaeter nicht an fehlender Konfiguration scheitert.
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
				# Wir laden die Karten je Monat frisch, damit wir immer aktuelle
				# Konfiguration (Status, billing_account_id) verwenden.
				monthly_cards = [
					card
					for card in card_repository.list_credit_by_user(user_id)
					if card.status == "aktiv" and card.billing_account_id is not None
				]

			for card in monthly_cards:
				for tx_index in range(transactions_per_month):
					# Wir verteilen Umsaetze im Monat, aber vermeiden den letzten Tag,
					# damit es nicht mit dem Abrechnungsdatum kollidiert.
					day = min(3 + (tx_index * 7), month_end.day - 1)
					tx_date = date(month_start.year, month_start.month, max(1, day))
					amount = 25.0 + float((offset * 10) + (tx_index * 5))
					# Kreditkarten-Umsatz: wird als Transaction auf der Kreditkarte gebucht.
					# `TransactionService` erhoeht dabei typischerweise `CreditCard.balance`.
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

			# Am Monatsende wird der offene Betrag abgerechnet.
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
		"""Fuehrt Monatsabrechnungen fuer alle Kreditkarten eines Users aus.

		Fuer jede Kreditkarte gilt:
		- Abrechnung ist nur faellig, wenn in diesem Monat/Jahr noch nicht abgerechnet wurde.
		- Die Karte muss aktiv sein.
		- `balance` muss > 0 sein (sonst gibt es nichts zu bezahlen).
		- `billing_account_id` muss gesetzt sein (von welchem Konto soll abgebucht werden?).

		Wenn alles passt:
		1) Erzeuge eine `expense`-Transaktion auf dem Abrechnungskonto in Hoehe der Balance.
		2) Setze `balance` auf 0.0 und `last_billed` auf das Referenzdatum.

		Args:
			user_id: Besitzer der Kreditkarten.
			reference_date: Stichtag der Abrechnung (z.B. letzter Tag des Monats oder Login-Datum).

		Returns:
			Anzahl der erfolgreich abgerechneten Kreditkarten.

		Raises:
			Keine. Fehler bei einzelnen Karten werden abgefangen, damit die
			Verarbeitung fuer andere Karten weiterlaufen kann.
		"""
		processed = 0

		with Session(engine) as session:
			card_repository = CardRepository(session)
			# DB-Read: Alle Kreditkarten des Users (Status/Balances werden spaeter geprueft).
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
				# Wir brauchen eine Kategorie fuer die Abbuchung vom Abrechnungskonto.
				# In diesem Projekt wird dafuer eine "Sonstiges"/Fallback-Kategorie verwendet.
				with Session(engine) as session:
					category_repository = CategoryRepository(session)
					categories = category_repository.list_all()
					# Aktueller Ansatz: letzte Kategorie als Fallback.
					miscellaneous_category = categories[-1] if categories else None
					
					if miscellaneous_category is None:
						continue
					
					# Erstelle Abbuchung: Das ist die "Rechnungszahlung".
					# `TransactionService` prueft dabei u.a. den Kontosaldo.
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
				# Reload in frischer Session: so arbeiten wir mit einem gemanagten ORM-Objekt.
				reloaded = card_repository.get_credit_by_id(credit_card.creditcard_id)
				if reloaded is not None:
					# Nach erfolgreicher Zahlung ist der offene Kredit ausgeglichen.
					reloaded.balance = 0.0
					# Monat/Jahr in `last_billed` dient als "Schon abgerechnet"-Marker.
					reloaded.last_billed = reference_date
					card_repository.save_credit(reloaded)
			
			processed += 1
		
		return processed

	# Ermittelt eine Kategorie-ID fuer Demo-Buchungen (bevorzugt Freizeit).
	def _resolve_demo_category_id(self, category_repository: CategoryRepository) -> int:
		"""Waehlt eine Kategorie fuer Demo-Umsaetze aus.

		Strategie: "Freizeit" ist gut sichtbar in der UI. Falls nicht vorhanden,
		nehmen wir einfach die erste Kategorie.

		Args:
			category_repository: Repository fuer Kategorien.

		Returns:
			Die ausgewaehlte `category_id`.

		Raises:
			ValueError: Wenn keine Kategorien existieren oder keine ID verfuegbar ist.
		"""
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
		"""Gibt den 1. Tag des um `month_shift` verschobenen Monats zurueck.

		Args:
			base_date: Ausgangsdatum.
			month_shift: Monatsverschiebung (z.B. -1 fuer den Vormonat).

		Returns:
			Datum des 1. Tages im Zielmonat.
		"""
		total_month = (base_date.year * 12) + (base_date.month - 1) + month_shift
		year = total_month // 12
		month = (total_month % 12) + 1
		return date(year, month, 1)

	# Gibt den letzten Tag eines Monats zurueck.
	def _last_day_of_month(self, year: int, month: int) -> date:
		"""Gibt den letzten Tag eines Monats zurueck (z.B. 28/29/30/31).

		Args:
			year: Jahr.
			month: Monat (1-12).

		Returns:
			Letzter Tag des Monats als `date`.
		"""
		last_day = calendar.monthrange(year, month)[1]
		return date(year, month, last_day)
	
	# Prueft, ob ein einzelne Kreditkarte zum Referenzdatum faellig ist.
	def _is_billing_due(self, credit_card: CreditCard, reference_date: date) -> bool:
		"""Prueft, ob fuer diese Karte im aktuellen Monat noch nicht abgerechnet wurde.

		Die Abrechnungsregel ist absichtlich einfach: Es wird pro Monat/Jahr nur eine
		Abrechnung zugelassen. Das Datum `last_billed` wird daher nur als Marker fuer
		"in diesem Monat schon erledigt" genutzt.

		Args:
			credit_card: Kreditkarte, die geprueft wird.
			reference_date: Stichtag (Monat/Jahr), fuer den geprueft wird.

		Returns:
			`True`, wenn eine Abrechnung in diesem Monat/Jahr noch offen ist.
		"""
		if credit_card.last_billed is None:
			return True
		
		if credit_card.last_billed.month != reference_date.month:
			return True
		
		if credit_card.last_billed.year != reference_date.year:
			return True
		
		return False


creditcard_billing_service = CreditCardBillingService()
