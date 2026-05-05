"""src.ui.controllers.payment_controller

Diese Datei gehoert zur **UI-Controller-Schicht**.

Zahlungen/Umbuchungen erzeugen Buchungen (Transaktionen) und ggf. Zusatzdaten
(`Payment`, `Transfer`). Der Controller ruft die entsprechenden Service-Methoden
auf und gibt fuer die UI ein simples Erfolg/Fehler-Ergebnis zurueck.
"""

from __future__ import annotations

from datetime import date

from src.services.payment_service import payment_service


# Orchestriert Zahlungs-Use-Cases und kapselt Fehlerbehandlung fuer die UI.
class PaymentController:
	"""UI-Controller fuer Zahlungen, Umbuchungen und Kontoauszuege."""

	# Fuehrt eine Inlandszahlung aus.
	def create_payment(self, payload: dict) -> str | None:
		"""Fuehrt eine Zahlung aus.

		Args:
			payload: Eingabedaten aus der UI (z.B. target_iban, amount, from_account_id, date, ...).

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			payment_service.create_payment(payload)
			return None
		except Exception as error:
			return str(error)

	# Fuehrt eine Kontoumbuchung aus.
	def create_transfer(self, payload: dict) -> str | None:
		"""Fuehrt eine Umbuchung zwischen zwei eigenen Konten aus.

		Args:
			payload: Eingabedaten aus der UI (from_account_id, to_account_id, amount).

		Returns:
			`None` bei Erfolg, sonst Fehlertext.
		"""
		try:
			payment_service.create_transfer(payload)
			return None
		except Exception as error:
			return str(error)

	# Erzeugt einen Kontoauszug oder liefert Fehlermeldung.
	def generate_statement(
		self,
		account_id: int,
		start_date: date,
		end_date: date,
	) -> str:
		"""Erzeugt einen Kontoauszug als PDF und gibt den Dateipfad zurueck.

		Args:
			account_id: Konto, fuer das der Auszug erzeugt werden soll.
			start_date: Start des Zeitraums (inkl.).
			end_date: Ende des Zeitraums (inkl.).

		Returns:
			Pfad zur erzeugten PDF-Datei oder Fehlertext als String.
		"""
		try:
			return payment_service.generate_statement(account_id, start_date, end_date)
		except Exception as error:
			return str(error)


payment_controller = PaymentController()
