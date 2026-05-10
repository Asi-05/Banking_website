"""src.ui.views.login_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

Die View ist zustaendig fuer:

- Aufbau des Login-Formulars (Eingabefelder, Button, Fehlerlabel)
- Interaktion (Button-Click) und Anzeige von Rueckmeldungen

Wichtiges Zusammenspiel:

- Der eigentliche Login-Use-Case liegt im `AuthService`.
- Diese View ruft den `AuthController` auf, der Exceptions abfaengt und entweder
	ein Ergebnis-Dict oder einen Fehlertext zurueckgibt.
- Nach erfolgreichem Login wird `app_state` gesetzt, damit andere Views wissen,
	welcher User aktiv ist.

Route: `/`
"""

from src.ui.controllers.auth_controller import auth_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert das Login-Formular.

	Die UI besteht aus einer zentrierten Card mit Vertragsnummer/Passwort und einem
	Button. Bei Fehlern wird eine Meldung unterhalb der Eingabefelder angezeigt.
	"""
	from nicegui import ui

	# Container: Zentriertes Card-Layout (volle Bildschirmhöhe mit Zentrierung)
	with ui.column().classes("w-full h-screen items-center justify-center"):
		with ui.card().classes("w-96"):
			# Titel
			ui.label("💰 BetterBank").classes("text-h4 text-center font-bold")
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
				"""Verarbeitet den Login-Button-Klick.

				Die View ruft den `AuthController` auf und verarbeitet das Ergebnis so,
				dass die UI einfach reagieren kann:
				- Bei Fehlern wird ein Text angezeigt.
				- Bei Erfolg wird der globale `app_state` gesetzt und zur Dashboard-Route
				  navigiert.

				Warum ist die Funktion `async`?
				NiceGUI erlaubt sowohl synchrone als auch asynchrone Event-Handler.
				Mit `async` bleibt die UI reaktionsfaehig, falls ein Handler spaeter
				z. B. laengere IO-Operationen machen wuerde.

				Returns:
					None
				"""
				contract_number = contract_number_input.value.strip()
				password = password_input.value

				# Hinweis: Das Passwort wird nur fuer den Login-Aufruf verwendet und
				# nicht im `app_state` gespeichert.

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

					# Achtung: In einer echten Anwendung wuerde man hier keine kompletten
					# Auth-Daten global speichern, sondern ein Session-Token pro Client.

					# Erfolgs-Meldung anzeigen
					ui.notify("Erfolgreich angemeldet!", type="positive")

					# Zu Dashboard navigieren
					ui.navigate.to("/dashboard")
				else:
					error_label.set_text(result.get("message", "Anmeldung fehlgeschlagen"))

			contract_number_input.on('keydown.enter', handle_login)
			password_input.on('keydown.enter', handle_login)

			login_button = ui.button("Anmelden", on_click=handle_login).classes("w-full")
			login_button.props("unelevated color=primary")
