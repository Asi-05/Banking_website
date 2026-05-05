"""src.services.dashboard_service

Diese Datei gehoert zur **Service-Schicht**.

Das Dashboard fasst Daten aus mehreren Quellen zusammen und liefert eine
kompakte `DashboardSummary` fuer die UI:

- **Total Balance**: Summe der aktuellen Kontostaende aller Konten eines Users.
- **Income/Expenses**: Summen im gewaehlten Zeitraum, basierend auf Transaktionen.
- **Chart Data**: Aggregation pro Monat (YYYY-MM) fuer Diagramme.

Wichtig: Interne Kontoumbuchungen werden als zwei Transaktionen gespeichert
(Ausgang = expense, Eingang = income). Fuer Auswertungen wuerde das das
Einkommen und die Ausgaben kuenstlich erhoehen, obwohl es nur eine Verschiebung
innerhalb des eigenen Vermoegens ist. Deshalb filtert dieser Service Umbuchungen
aus den Income/Expense-Auswertungen heraus.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.domain.models import ChartData, DashboardSummary
from src.utils.validators import validate_date_range


# Implementiert die Geschaeftslogik fuer Dashboard-Aggregationen.
class DashboardService:
	"""Fachlogik fuer Dashboard-Aggregationen."""

	# Berechnet Bilanz, Summen und Chartdaten fuer einen Zeitraum.
	def dashboard(self, user_id: int, start_date: date, end_date: date) -> DashboardSummary:
		"""Berechnet Dashboard-Kennzahlen fuer einen User und Zeitraum.

		Args:
			user_id: Der User, dessen Daten ausgewertet werden.
			start_date: Start des Auswertungszeitraums (inklusive).
			end_date: Ende des Auswertungszeitraums (inklusive).

		Returns:
			`DashboardSummary` mit Kontosumme, Income/Expenses und monatlichen Chartdaten.

		Raises:
			ValueError: Wenn der Datumsbereich ungueltig ist.
		"""
		# Grundvalidierung: Im UI duerfen keine "negativen" oder invertierten Zeitraeume entstehen.
		validate_date_range(start_date, end_date)

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			transaction_repository = TransactionRepository(session)

			# DB-Query: Alle Konten des Users.
			accounts = account_repository.list_by_user(user_id)
			# Der Kontostand ist der aktuelle Zustand (nicht nur im Zeitraum). Das ist
			# fuer das Dashboard ok, weil es eine "Momentaufnahme" ist.
			total_balance = sum(account.balance for account in accounts)

			# DB-Query: Transaktionen im Zeitraum, bereits auf den User eingeschraenkt.
			transactions = transaction_repository.filter_transactions(
				start_date=start_date,
				end_date=end_date,
				user_id=user_id,
			)
			
			# Umbuchungen (Kontoumbuchungen) werden technisch als zwei Transaktionen
			# umgesetzt. Fuer Income/Expense wuerden sie sonst doppelt zaehlen.
			#
			# Die Filterung erfolgt ueber das Note-Label "Kontoumbuchung ...".
			# Hinweis: Einige Tests nutzen SimpleNamespace-Fixtures ohne Attribut `note`;
			# wir sind daher defensiv mit `getattr(...)`.
			non_transfer_transactions = [
				t for t in transactions
				if not (getattr(t, "note", None) and "Kontoumbuchung" in getattr(t, "note", ""))
			]
			
			# Income: Summiere alle Einnahmen.
			total_income = sum(t.amount for t in non_transfer_transactions if t.type == "income")
			# Expenses: Wir nehmen `abs(...)`, damit die Ausgabe als positive Zahl im
			# Dashboard erscheint (egal ob sie intern positiv oder negativ gespeichert ist).
			total_expenses = sum(abs(t.amount) for t in non_transfer_transactions if t.type == "expense")

			# Gruppierung pro Monat (YYYY-MM) fuer Chart-Daten.
			grouped: dict[str, dict[str, float]] = defaultdict(
				lambda: {"income": 0.0, "expenses": 0.0}
			)
			for transaction in non_transfer_transactions:
				label = transaction.date.strftime("%Y-%m")
				if transaction.type == "income":
					grouped[label]["income"] += transaction.amount
				else:
					grouped[label]["expenses"] += abs(transaction.amount)

			# Sortierung sorgt fuer stabile Reihenfolge in Diagrammen (chronologisch).
			chart_data = [
				ChartData(
					label=label,
					income=values["income"],
					expenses=values["expenses"],
				)
				for label, values in sorted(grouped.items())
			]

			return DashboardSummary(
				total_balance=total_balance,
				total_income=total_income,
				total_expenses=total_expenses,
				chart_data=chart_data,
			)


dashboard_service = DashboardService()
