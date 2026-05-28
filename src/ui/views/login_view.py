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

=== SEITEN-AUFBAU ===
    1. Header-Balken  – weiss, Logo links
    2. Blauer Banner  – "Login eBanking"
    3. Zwei Spalten   – links: Formular | rechts: Hilfe-Box

Route: `/`
"""

from src.ui.controllers.auth_controller import auth_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Login-Seite im Banking-Stil.

	LOGOUT-BESTAETIGUNG:
	    Wenn der User sich gerade abgemeldet hat, setzt auth_controller.logout()
	    das Flag app_state["show_logout_message"] = True.
	    Diese Funktion prueft das Flag beim Laden und zeigt einmalig eine
	    Bestaetigung an (dann wird das Flag sofort wieder auf False gesetzt).

	    Warum hier und nicht direkt in _logout()?
	        ui.notify() nach ui.navigate.to("/") wird nicht angezeigt –
	        die Seite wechselt, bevor die Meldung sichtbar wird.
	        Das Flag-Muster loest das: Meldung erscheint auf der Ziel-Seite.
	"""
	from nicegui import ui

	# Logout-Bestaetigung anzeigen, falls gerade abgemeldet wurde.
	if app_state.get("show_logout_message"):
		ui.notify("Sie wurden erfolgreich abgemeldet.", type="positive")
		# Sofort zuruecksetzen: Meldung soll nur einmal erscheinen.
		app_state["show_logout_message"] = False

	# =====================================================================
	# SEITEN-RAHMEN
	# Weisser Hintergrund, volle Bildschirmhoehe, kein Gap zwischen den
	# Sektionen (Header / Banner / Inhalt liegen direkt aneinander).
	# =====================================================================
	with ui.column().classes("w-full min-h-screen bg-white").style("gap: 0"):

		# =================================================================
		# 1. HEADER-BALKEN
		# Weisser Balken mit Logo links – wie bei echten Banken (ZKB, UBS).
		# border-bottom = dezente Trennlinie zum blauen Banner darunter.
		# =================================================================
		with ui.row().classes("w-full items-center px-10 py-4").style(
			"background: white; border-bottom: 1px solid #e5e7eb"
		):
			# Logo links: Emoji + App-Name + Trennstrich + "eBanking".
			ui.label("💰 BetterBank").classes("font-bold").style(
				"color: #1e3a8a; font-size: 1.2rem"
			)
			ui.label("|").classes("mx-3").style("color: #9ca3af")
			ui.label("eBanking").style("color: #1e3a8a; font-size: 1.1rem")

			# Platzhalter: schiebt das Fragezeichen-Icon an den rechten Rand.
			# q-space ist ein Quasar-Element das den verbleibenden Platz fuellt.
			ui.space()

			# Fragezeichen-Icon rechts oben – gleiche Hoehe wie das Logo.
			# Bei Klick: Benachrichtigung mit Supportnummer anzeigen.
			ui.button(
				icon="help_outline",
				on_click=lambda: ui.notify(
					"Bei Fragen bitte unter 0844 840 140 anrufen.",
					type="info",
					position="top",
				),
			).props("flat round").style("color: #1e3a8a")

		# =================================================================
		# 2. BLAUER BANNER
		# Dunkles Bankblau – signalisiert dem User klar die Login-Seite.
		# Gleiche Farbe wie typische Schweizer E-Banking-Portale.
		# =================================================================
		with ui.row().classes("w-full px-10 py-3").style("background: #1a3a8f"):
			ui.label("Login eBanking").classes("text-white font-semibold")

		# =================================================================
		# 3. HAUPT-INHALT (zwei Spalten)
		# justify-center = der ganze Block wird horizontal in der Seite
		# zentriert, damit er auf grossen Monitoren nicht zu weit links klebt.
		# =================================================================
		# Äussere Row: zentriert den ganzen Inhalt horizontal auf der Seite.
		with ui.row().classes("w-full justify-center py-14"):
			# Innere Row: feste Maximalbreite 900px – nicht zu breit, nicht zu eng.
			# Beide Spalten sind so gleichmässig ausgerichtet und gut lesbar.
			with ui.row().classes("items-start").style("width: 900px; gap: 60px"):

				# =============================================================
				# LINKE SPALTE – Login-Formular
				# Feste Breite 520px: ausreichend für die Felder, aber nicht
				# so breit, dass das Formular verloren wirkt.
				# =============================================================
				with ui.column().classes("gap-5").style("width: 520px; flex-shrink: 0"):

					# Grosser Titel – klare Handlungsaufforderung, wie bei ZKB.
					# Zwei separate Labels statt \n, damit der Zeilenabstand
					# sauber kontrolliert werden kann.
					with ui.column().style("gap: 2px"):
						ui.label("Geben Sie Ihre Vertragsnummer").classes("font-bold").style(
							"color: #1e3a8a; font-size: 1.55rem; line-height: 1.3"
						)
						ui.label("und Ihr Passwort ein").classes("font-bold").style(
							"color: #1e3a8a; font-size: 1.55rem; line-height: 1.3"
						)

					# Vertragsnummer-Feld.
					# outlined = Rahmen rundum (kein bloss Unterstrich).
					contract_number_input = ui.input(
						label="Vertragsnummer",
					).props("outlined").classes("w-full")

					# Passwort-Feld mit Auge-Symbol zum Ein-/Ausblenden.
					# password_toggle_button=True → kleines Auge-Icon erscheint im Feld.
					password_input = ui.input(
						label="Passwort",
						password=True,
						password_toggle_button=True,
					).props("outlined").classes("w-full")

					# Fehlermeldungs-Label: beim Seitenaufruf unsichtbar (kein Leerraum).
					# set_visibility(True) wird in handle_login() aufgerufen, wenn ein
					# Fehler auftritt.
					error_label = ui.label("").classes("text-red-600 text-sm")
					error_label.set_visibility(False)

					# ----------------------------------------------------------
					# LOGIN-HANDLER
					# Wird aufgerufen beim Button-Klick ODER Enter-Taste im Feld.
					# Logik identisch zum Original: nur UI-Darstellung wurde ergaenzt.
					# ----------------------------------------------------------
					async def handle_login() -> None:
						"""Verarbeitet den Login-Button-Klick.

						Warum async?
						    NiceGUI-Event-Handler koennen sync oder async sein.
						    async haelt die UI reaktionsfaehig bei IO-Operationen.

						Ablauf:
						    1. Eingaben lesen + validieren (beide Felder befuellt?)
						    2. auth_controller.login() aufrufen
						    3. Fehler → Fehlermeldung anzeigen
						       Erfolg → app_state setzen, zum Dashboard navigieren
						"""
						contract_number = contract_number_input.value.strip()
						password = password_input.value

						# Passwort wird NICHT gespeichert – nur fuer diesen Aufruf genutzt.

						# Validierung: beide Felder muessen ausgefuellt sein.
						if not contract_number or not password:
							error_label.set_text("Bitte Vertragsnummer und Passwort eingeben.")
							error_label.set_visibility(True)
							return

						# Fehlermeldung vom letzten Versuch ausblenden.
						error_label.set_visibility(False)

						# Controller aufrufen → gibt dict (Erfolg) oder String (Fehler) zurueck.
						result = auth_controller.login(contract_number, password)

						# Fehlerfall: Controller gibt einen lesbaren Fehlertext zurueck.
						if isinstance(result, str):
							error_label.set_text(result)
							error_label.set_visibility(True)
							return

						# Erfolgsfall: result ist ein dict mit success=True und user_id.
						if result.get("success"):
							# Eingeloggten User im globalen app_state speichern.
							# Alle anderen Views lesen daraus, wer gerade eingeloggt ist.
							app_state["user_id"] = result.get("user_id")
							app_state["current_user"] = result

							# Achtung: In einer echten Multi-User-App wuerde man ein
							# Session-Token pro Browser-Client verwenden (nicht global).

							# Kurze Erfolgsmeldung, dann zum Dashboard navigieren.
							ui.notify("Erfolgreich angemeldet!", type="positive")
							ui.navigate.to("/dashboard")
						else:
							error_label.set_text(result.get("message", "Anmeldung fehlgeschlagen"))
							error_label.set_visibility(True)

					# Enter-Taste in beiden Feldern loest den Login aus (bessere UX).
					contract_number_input.on("keydown.enter", handle_login)
					password_input.on("keydown.enter", handle_login)

					# Anmelden-Button: nicht volle Breite (wie bei echten Banken).
					ui.button("Anmelden", on_click=handle_login).props(
						"unelevated color=primary"
					).style("min-width: 150px")

				# =============================================================
				# RECHTE SPALTE – Hilfe-Box
				# flex: 1 = nimmt den gesamten restlichen Platz ein, den die
				# linke Spalte nicht belegt. So wächst die Box mit dem Fenster.
				# =============================================================
				# Rechte Spalte: nimmt den restlichen Platz (900 - 520 - 60 = 320px).
				with ui.column().style("flex: 1; min-width: 0"):
					with ui.card().style(
						"background: #eff6ff; border: none; width: 100%; border-radius: 8px; box-shadow: none"
					):
						# Titel der Hilfe-Box.
						ui.label("Benötigen Sie Unterstützung?").classes("font-bold").style(
							"color: #1e3a8a; font-size: 1rem; margin-bottom: 12px"
						)

						# Telefonnummern und Oeffnungszeiten als 2-spaltiges Grid.
						# Linke Spalte: Bezeichnung (fett), rechte Spalte: Wert.
						# gap-y-2 = vertikaler Abstand zwischen den Zeilen.
						with ui.grid(columns=2).style("gap: 6px 16px; font-size: 0.875rem"):
							ui.label("Inland").classes("font-semibold").style("color: #1e3a8a")
							ui.label("0844 840 140").style("color: #1e3a8a")

							ui.label("Ausland").classes("font-semibold").style("color: #1e3a8a")
							ui.label("+41 44 293 95 95").style("color: #1e3a8a")

						# Visueller Trenner zwischen Nummern und Oeffnungszeiten.
						ui.separator().classes("my-3")

						with ui.grid(columns=2).style("gap: 6px 16px; font-size: 0.875rem"):
							ui.label("Mo - Fr").classes("font-semibold").style("color: #1e3a8a")
							ui.label("08:00 - 20:00").style("color: #1e3a8a")

							ui.label("Sa").classes("font-semibold").style("color: #1e3a8a")
							ui.label("08:00 - 17:00").style("color: #1e3a8a")

							ui.label("So").classes("font-semibold").style("color: #1e3a8a")
							# "Geschlossen" in Rot – fällt auf und ist sofort klar.
							ui.label("Geschlossen").style("color: #dc2626")
