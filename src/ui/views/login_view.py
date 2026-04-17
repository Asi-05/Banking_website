"""
Login View - Betterbank Banking App
Implementiert US13: Benutzer-Anmeldung mit Vertragsnummer und Passwort
Route: /
"""

from src.ui.controllers.auth_controller import auth_controller
from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt das Login-Formular an.
	Enthält Eingabefelder für Vertragsnummer und Passwort sowie einen Anmelde-Button.
	"""
	from nicegui import ui

	# Container: Zentriertes Card-Layout
	with ui.card().classes("self-center m-auto"):
		# Titel
		ui.label("💰 Betterbank").classes("text-h4 text-center font-bold")
		ui.label("E-Banking für persönliche Finanzplanung").classes("text-center text-gray-600 mb-8")

		ui.separator()

		# Eingabefelder
		contract_number_input = ui.input(label="Vertragsnummer").props("outlined")
		contract_number_input.classes("w-full mb-4")

		password_input = ui.input(label="Passwort", password=True).props("outlined")
		password_input.classes("w-full mb-6")

		# Fehlermeldungs-Label (wird bei Fehlern gefüllt)
		error_label = ui.label("").classes("text-red-600 mb-4")

		# Login-Button
		async def handle_login() -> None:
			"""
			Verarbeitet den Login-Vorgang.
			1. controller.login() aufrufen → gibt dict (success) oder str (error) zurück
			2. Bei Erfolg: app_state setzen und zu /dashboard navigieren
			3. Bei Fehler: Fehlermeldung anzeigen
			"""
			contract_number = contract_number_input.value.strip()
			password = password_input.value

			# Validierung: Beide Felder müssen gefüllt sein
			if not contract_number or not password:
				error_label.set_text("Bitte Vertragsnummer und Passwort eingeben.")
				return

			# Controller aufrufen
			result = auth_controller.login(contract_number, password)

			# Fehlerbehandlung
			if isinstance(result, str):
				# Fehler: result ist ein String
				error_label.set_text(result)
				return

			# Erfolg: result ist ein dict mit success=True, user_id, auth_token, etc.
			if result.get("success"):
				# App-State setzen (wird in anderen Views überprüft)
				app_state["user_id"] = result.get("user_id")
				# current_user wird später ggf. gefüllt, für jetzt reicht user_id
				app_state["current_user"] = result

				# Erfolgs-Meldung anzeigen
				ui.notify("Erfolgreich angemeldet!", type="positive")

				# Zu Dashboard navigieren
				ui.navigate.to("/dashboard")
			else:
				error_label.set_text(result.get("message", "Anmeldung fehlgeschlagen"))

		login_button = ui.button("Anmelden", on_click=handle_login).classes("w-full")
		login_button.props("unelevated color=primary")
