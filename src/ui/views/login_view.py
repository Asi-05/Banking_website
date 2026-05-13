"""src.ui.views.login_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

=== WAS MACHT DIESE VIEW? ===
Sie zeigt das Login-Formular (Vertragsnummer + Passwort) und verarbeitet
den Login-Button-Click. Nach erfolgreichem Login wird der globale `app_state`
gesetzt und zur Dashboard-Route navigiert.

=== WAS DIESE VIEW NICHT TUT ===
Sie enthaelt KEINE Fachlogik. Sie ruft nur den `AuthController` auf und
zeigt dessen Ergebnis in der UI an (Fehlermeldung oder Navigation).

=== AUFRUF-KETTE BEI BUTTON-CLICK ===
    User klickt "Anmelden"
    → handle_login()                          [diese View]
    → auth_controller.login(nr, pw)           [AuthController]
    → AuthService.login(nr, pw)               [AuthService]
    → UserRepository.get_by_contract_number() [DB-Abfrage]
    → verify_password(pw, stored_hash)        [validators.py]
    → [bei altem Dummy-Hash: Migration zu PBKDF2]
    → recurring_service.process_due_on_login() [Dauerauftraege pruefen]
    → creditcard_billing_service.bill_if_needed() [Monatliche Abrechnung]
    → Rueckgabe: dict{success, user_id, ...}

=== RUECKGABE-KETTE ===
    AuthService → dict oder Exception
    AuthController → dict (Erfolg) oder String (Fehler)
    handle_login → app_state setzen + ui.navigate.to("/dashboard")
                   ODER error_label.set_text(fehlertext)

=== LOGIN-GUARD (auf DIESER Seite) ===
Diese Seite hat KEINEN Login-Guard. Sie muss ohne Login erreichbar sein,
da sie die Login-Seite selbst ist!
Alle anderen Views (dashboard, transactions, ...) pruefen am Anfang ihrer
`show()`-Funktion ob ein User eingeloggt ist:
    if app_state.get("current_user") is None:
        ui.navigate.to("/")
        return

=== ARCHITEKTUR-KETTE ===
    Route "/" (in __main__.py) → login_view.show()
    → ui.card mit Eingabefeldern
    → handle_login() → auth_controller → app_state → /dashboard

Route: `/`
"""

from src.ui.controllers.auth_controller import auth_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert das Login-Formular.

	Die UI besteht aus einer zentrierten Card mit Vertragsnummer/Passwort und einem
	Button. Bei Fehlern wird eine Meldung unterhalb der Eingabefelder angezeigt.

	LOGOUT-BESTAETIGUNG:
	    Wenn der User sich gerade abgemeldet hat, wurde in auth_controller.logout()
	    das Flag app_state["show_logout_message"] = True gesetzt.
	    Diese Funktion prueft das Flag BEIM LADEN der Login-Seite und zeigt
	    einmalig eine Bestaetigung an.

	    Warum hier und nicht in _logout()?
	        ui.notify() direkt vor ui.navigate.to() funktioniert nicht:
	        die Seite wechselt, bevor die Meldung sichtbar ist.
	        Das Flag-Muster loest das: Meldung wird auf der ZIEL-Seite angezeigt.
	"""
	from nicegui import ui

	# Logout-Bestaetigung anzeigen, falls gerade abgemeldet wurde.
	# Das Flag wurde von auth_controller.logout() auf True gesetzt.
	if app_state.get("show_logout_message"):
		# Gruene Benachrichtigung oben rechts fuer 3 Sekunden.
		ui.notify("Sie wurden erfolgreich abgemeldet.", type="positive")
		# Flag sofort zuruecksetzen: die Meldung soll nur einmal erscheinen,
		# nicht bei jedem weiteren Besuch der Login-Seite.
		app_state["show_logout_message"] = False

	# Container: Zentriertes Card-Layout (volle Bildschirmhöhe mit Zentrierung)
	with ui.column().classes("w-full h-screen items-center justify-center"):
		with ui.card().classes("w-96"):
			# Titel
			with ui.column().classes("w-full items-center mb-2"):
				ui.label("💰 BetterBank").classes("text-h4 font-bold")
				ui.label("E-Banking für persönliche Finanzplanung").classes("text-primary mb-6")

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
