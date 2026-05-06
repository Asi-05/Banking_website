"""src.ui.controllers.budget_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Budgets sind Limits, die pro Monat (und optional pro Kategorie) gesetzt werden.
Die fachlichen Regeln (Unique-Constraint-Logik, Verbrauchsberechnung) liegen im
`BudgetService`. Dieser Controller liefert nur UI-freundliche Rueckgabewerte
(None bei Erfolg oder Fehlertext bei Problemen).
"""

from __future__ import annotations

from src.services.budget_service import budget_service


# Orchestriert Budget-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class BudgetController:
	"""UI-Controller fuer Budget-Use-Cases."""

	# Legt ein Budget an oder aktualisiert es.
	def set_budget(self, payload: dict) -> str | None:
		"""Legt ein Budget an oder aktualisiert ein bestehendes (Upsert).

		Args:
			payload: Eingabedaten aus der UI (user_id, month, year, limit_amount, category_id).

		Returns:
			`None` bei Erfolg, sonst eine Fehlermeldung als String.
		"""
		try:
			budget_service.set_budget(payload)
			return None
		except Exception as error:
			return str(error)

	# Liefert den Budgetstatus oder eine Fehlermeldung.
	def check_budget_status(
		self,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None = None,
	) -> dict | str:
		"""Prueft den Budgetstatus (Limit vs. Verbrauch) fuer einen Monat.

		Args:
			user_id: ID des eingeloggten Users.
			month: Monat (1-12).
			year: Jahr.
			category_id: Optionaler Kategorien-Filter; `None` bedeutet globales Budget.

		Returns:
			Ein Dict mit Status-Informationen oder eine Fehlermeldung als String.
		"""
		try:
			return budget_service.check_budget_status(
				user_id=user_id,
				month=month,
				year=year,
				category_id=category_id,
			)
		except Exception as error:
			return str(error)

	# Aktualisiert ein bestehendes Budget.
	def update_budget(self, budget_id: int, limit_amount: float) -> str | None:
		"""Aendert das Limit eines bestehenden Budgets.

		Args:
			budget_id: ID des Budgets.
			limit_amount: Neues Budget-Limit.

		Returns:
			`None` bei Erfolg, sonst Fehlermeldung als String.
		"""
		try:
			budget_service.update_budget(budget_id, limit_amount)
			return None
		except Exception as error:
			return str(error)

	# Loescht ein bestehendes Budget.
	def delete_budget(self, budget_id: int) -> str | None:
		"""Loescht ein Budget.

		Args:
			budget_id: ID des Budgets.

		Returns:
			`None` bei Erfolg, sonst Fehlermeldung als String.
		"""
		try:
			budget_service.delete_budget(budget_id)
			return None
		except Exception as error:
			return str(error)

	# Listet alle Budgets eines Users.
	def list_budgets(self, user_id: int) -> list | str:
		"""Listet alle Budgets eines Users.

		Args:
			user_id: ID des eingeloggten Users.

		Returns:
			Liste von Budget-Objekten oder Fehlermeldung als String.
		"""
		try:
			return budget_service.list_budgets(user_id)
		except Exception as error:
			return str(error)


budget_controller = BudgetController()
