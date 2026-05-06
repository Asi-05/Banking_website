"""src.ui.controllers.account_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Der AccountController stellt UI-freundliche Methoden rund um Konten bereit.
Er delegiert die fachlichen Regeln an `AccountService` und wandelt Exceptions in
einfache Rueckgabewerte um (z.B. Fehlertext statt Exception).
"""

from __future__ import annotations

from src.services.account_service import account_service


# Orchestriert Konto-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class AccountController:
	"""UI-Controller fuer Konto-Use-Cases (Eroeffnen, Schliessen, Auflisten)."""

	# Fuehrt die Kontoeroeffnung aus.
	def open_account(self, payload: dict) -> str | None:
		"""Eroeffnet ein neues Konto.

		Args:
			payload: Eingabedaten aus der View (z.B. Kontotyp, User-ID, Startsaldo).

		Returns:
			`None` bei Erfolg, sonst eine Fehlermeldung als String.
		"""
		try:
			account_service.open_account(payload)
			return None
		except Exception as error:
			return str(error)

	# Fuehrt die Kontoschliessung gemaess Business-Regeln aus.
	def close_account(self, account_id: int) -> str | None:
		"""Schliesst ein Konto gemaess Business-Regeln.

		Die eigentlichen Regeln (z.B. nur schliessen wenn Saldo = 0) liegen im Service.

		Args:
			account_id: ID des zu schliessenden Kontos.

		Returns:
			`None` bei Erfolg, sonst Fehlermeldung als String.
		"""
		try:
			account_service.close_account(account_id)
			return None
		except Exception as error:
			return str(error)

	# Liefert Kontenliste oder Fehlermeldung.
	def list_accounts(self, user_id: int) -> list | str:
		"""Listet die Konten eines Users.

		Args:
			user_id: ID des eingeloggten Users.

		Returns:
			Entweder eine Liste von Konto-Objekten oder eine Fehlermeldung als String.
		"""
		try:
			return account_service.list_accounts(user_id)
		except Exception as error:
			return str(error)


account_controller = AccountController()
