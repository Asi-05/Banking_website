"""src.ui.views.transaction_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

=== WAS KANN DER USER AUF DIESER SEITE TUN? ===
    Tab 1 – Neue Inlandszahlung (US10):
        Externe Zahlung ausfuehren:
        Ziel-IBAN + Betrag + Von-Konto + Kategorie + Zweck + Datum.
        → Erstellt EINE Ausgabe-Transaktion + EINEN Payment-Datensatz in der DB.

    Tab 2 – Daueraufträge (US6):
        - Bestehende Dauerauftraege anzeigen (inkl. naechste Ausfuehrung)
        - Bearbeiten (Betrag, Kategorie, Konto, Intervall, Ziel-IBAN)
        - Loeschen (mit Bestaetigung)
        - Neuen Dauerauftrag erstellen (Betrag, IBAN, Intervall, Startdatum)

    Tab 3 – Übertrag (Kontoumbuchung):
        Geld zwischen eigenen Konten umbuchen.
        → Erstellt ZWEI Transaktionen: eine Ausgabe (Von-Konto) + eine
          Einnahme (Zu-Konto). Beide werden als "Kontoumbuchung" markiert und
          im Dashboard NICHT gezaehlt.

=== WAS DIESE VIEW NICHT TUT ===
Sie enthaelt KEINE fachlichen Regeln. Alle Regeln liegen in den Services:
    - "Betrag darf Kontostand nicht uebersteigen" → TransactionService
    - "Genau eine Belastungsquelle" → validate_exactly_one_source()
    - "Naechste Ausfuehrungs-Datum berechnen" → RecurringService._next_due_date()

=== AUFRUF-KETTE: INLANDSZAHLUNG ===
    User klickt "Zahlung ausführen"
    → handle_create_payment()                    [diese View]
    → payment_controller.create_payment(payload) [PaymentController]
    → PaymentService.create_payment(payload)     [Validierung + Transaktion anlegen]
    → TransactionService.create_transaction(...)  [Saldo aendern]
    → TransactionRepository.create()             [DB INSERT]
    → None bei Erfolg, String bei Fehler

=== AUFRUF-KETTE: DAUERAUFTRAG ERSTELLEN ===
    User klickt "Dauerauftrag erstellen"
    → handle_create_recurring()                        [diese View]
    → recurring_controller.create_recurring(payload)   [RecurringController]
    → RecurringService.create_recurring(payload)       [_previous_due_date berechnen]
    → RecurringRepository.create()                     [DB INSERT]
    → None bei Erfolg, String bei Fehler

=== AUFRUF-KETTE: KONTOUMBUCHUNG ===
    User klickt "Umbuchen"
    → handle_transfer()                              [diese View]
    → payment_controller.create_transfer(payload)    [PaymentController]
    → PaymentService.create_transfer(payload)        [2 Transaktionen anlegen]
    → TransactionService.create_transaction(...)     [je einmal fuer Von/Zu-Konto]
    → TransactionRepository.create() x2             [2x DB INSERT]
    → None bei Erfolg, String bei Fehler

=== NAECHSTE AUSFUEHRUNG FUER DAUERAUFTRAEGE ===
    In der Tabelle wird die naechste Ausfuehrung angezeigt:
    → recurring_controller.get_next_execution_date(last_executed, interval)
    → RecurringService._next_due_date(last_executed, interval)
    Falls die naechste Ausfuehrung bereits "heute oder frueher" ist (z.B. weil
    der Auftrag heute beim Login schon ausgefuehrt wurde), wird die uebernachste
    berechnet, damit die Anzeige nicht wie "ueberfaellig" wirkt.

=== LOGIN-GUARD ===
    if app_state.get("current_user") is None:
        ui.navigate.to("/")    # kein User eingeloggt → zurueck zum Login
        return

=== ARCHITEKTUR-KETTE ===
    Route "/transactions" → show()
    → Tab 1: _build_domestic_payment_form() → payment_controller
    → Tab 2: _build_recurring_payments_section() → recurring_controller
    → Tab 3: _build_transfer_form() → payment_controller

Route: `/transactions`
"""

from datetime import date, timedelta

from src.ui.controllers.auth_controller import auth_controller
from src.ui.controllers.transaction_controller import transaction_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Transaktions-Seite (Tabs fuer Zahlungen, Bewegungen, ...).

	Die Seite ist geschuetzt: Ohne Login wird zur Startseite umgeleitet.

	Hinweis:
		Die View baut ein Tab-Layout auf. Die eigentlichen Inhalte pro Tab werden
		in Hilfsfunktionen erzeugt (z.B. `_build_domestic_payment_form`).
	"""
	from nicegui import ui

	# Sicherheitspruefung: ohne Login zur Startseite.
	if app_state.get("current_user") is None:
		ui.navigate.to("/")
		return

	user_id = app_state.get("user_id")

	# ===== SIDEBAR =====
	with ui.left_drawer():
		_build_sidebar()

	# ===== HEADER: BRAND LINKS + USER ACTIONS =====
	with ui.header():
		with ui.row().classes("w-full items-center justify-end"):
			ui.label("BetterBank").classes("text-h5 font-bold text-white pl-4")
			with ui.row().classes("items-center gap-2"):
				with ui.button(icon="settings").props("flat round color=primary"):
					with ui.menu():
						ui.menu_item("Kontoeinstellungen", on_click=lambda: _open_settings_dialog(user_id))
				ui.button("Abmelden", icon="logout", on_click=lambda: _logout()) \
					.props("flat no-caps color=primary") \
					.classes("font-semibold")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		ui.label("Transaktionen").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_domestic = ui.tab("Neue Inlandszahlung")
			tab_recurring = ui.tab("Daueraufträge")
			tab_transfer = ui.tab("Übertrag")

		with ui.tab_panels(tabs, value=tab_domestic).classes("w-full"):

			# ===== TAB 1: NEUE INLANDSZAHLUNG =====
			with ui.tab_panel(tab_domestic):
				_build_domestic_payment_form(user_id)

			# ===== TAB 2: DAUERAUFTRÄGE =====
			with ui.tab_panel(tab_recurring):
				_build_recurring_payments_section(user_id)

			# ===== TAB 3: ÜBERTRAG =====
			with ui.tab_panel(tab_transfer):
				_build_transfer_form(user_id)


def _build_domestic_payment_form(user_id: int) -> None:
	"""Rendert das Formular fuer eine neue Inlandszahlung (US10).

	Die Eingaben werden gesammelt und als Payload an den `PaymentController`
	weitergegeben.

	Args:
		user_id: ID des eingeloggten Users (wird u.a. fuer die Kontoliste benoetigt).
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.payment_controller import payment_controller
	from src.ui.controllers.category_controller import category_controller

	category_options = category_controller.list_categories()

	# hasattr() prueft, ob ein Objekt ein bestimmtes Attribut hat.
	# Warum noetig: Im echten Betrieb kommen die Daten als Python-Objekte (ORM-Modelle)
	# aus der Datenbank. In Tests kommen sie manchmal als einfache Dicts.
	# Mit hasattr() koennen wir beides lesen, ohne dass der Code abstuerzt.
	#
	# Konten laden (nur aktive Konten werden als Quelle angeboten).
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		account_options = {}
	else:
		account_options = {
			(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in result
			if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
		}

	with ui.card().classes("w-full"):
		# Ziel-IBAN
		iban_input = ui.input(label="Ziel-IBAN").props("outlined")
		iban_input.classes("w-full mb-4")

		# Betrag
		amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined")
		amount_input.classes("w-full mb-4")

		# Von-Konto
		from_account_select = ui.select(
			options=account_options,
			label="Von-Konto",
		).props("outlined")
		from_account_select.classes("w-full mb-4")

		# Kategorie
		category_select = ui.select(
			options=category_options,
			label="Kategorie",
		).props("outlined")
		category_select.classes("w-full mb-4")

		# Zweck
		char_count_label = ui.label("0 / 100 Zeichen").classes("text-xs text-gray-500 mb-4")

		def update_char_count(e) -> None:
			count = len(e.value)
			char_count_label.set_text(f"{count} / 100 Zeichen")
			if count >= 100:
				char_count_label.classes(remove="text-gray-500", add="text-red-600")
			else:
				char_count_label.classes(remove="text-red-600", add="text-gray-500")

		purpose_input = ui.textarea(label="Verwendungszweck", on_change=update_char_count).props("outlined maxlength=100")
		purpose_input.classes("w-full mb-1")

		# Ausführungsdatum
		execution_date_picker = ui.date_input("Ausführungsdatum", value=date.today().isoformat())
		execution_date_picker.classes("w-full mb-4")
		ui.label().bind_text_from(execution_date_picker, "value", lambda v: f"Datum: {v}" if v else "")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_create_payment() -> None:
			"""Validiert die UI-Felder und fuehrt die Zahlung aus.

			Die NiceGUI-Button-Callbacks koennen `async` sein. Das erlaubt es, spaeter
			(z.B. bei echten Netzwerk-/DB-Operationen) nicht-blockierende Ablaufe zu
			nutzen.

			Raises:
				ValueError: Wenn der Datepicker keinen gueltigen ISO-Datumsstring enthaelt.
			"""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
			if len(purpose_input.value) > 100:
				error_label.set_text("Verwendungszweck darf maximal 100 Zeichen enthalten.")
				return

			payload = {
				"target_iban": iban_input.value,
				"amount": amount_input.value or 0,
				"from_account_id": from_account_select.value,
				"category_id": category_select.value,
				"purpose": purpose_input.value,
				# Der Controller normalisiert ISO-Strings zu `datetime.date`.
				"date": execution_date_picker.value,
			}

			error = payment_controller.create_payment(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Zahlung erfolgreich ausgeführt", type="positive")
				iban_input.value = ""
				amount_input.value = 0
				from_account_select.value = None
				category_select.value = None
				purpose_input.value = ""
				execution_date_picker.value = date.today().isoformat()
				error_label.set_text("")

		ui.button("Zahlung ausführen", on_click=handle_create_payment).classes("w-full")


def _build_recurring_payments_section(user_id: int) -> None:
	"""Rendert den Tab "Dauerauftraege" (US6).

	Der Tab besteht aus:
	- einer Tabelle mit bestehenden Dauerauftraegen (inkl. Edit/Delete)
	- einem ausklappbaren Formular zum Erstellen eines neuen Dauerauftrags

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.recurring_controller import recurring_controller
	from src.ui.controllers.category_controller import category_controller

	with ui.column().classes("w-full gap-6"):

		category_map_names = category_controller.list_categories()

		# Konto-Mapping für Tabelle und Edit-Dialog
		accounts_result = account_controller.list_accounts(user_id)
		account_map = {
			int(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in (accounts_result if isinstance(accounts_result, list) else [])
			if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
		}

		# === TABELLE: DAUERAUFTRÄGE (direkt sichtbar, kein Klick nötig) ===

		def refresh_recurring_table():
			"""Laedt Dauerauftraege neu und befuellt die Tabelle.

			Der Controller kann Eintraege je nach Pfad als ORM-Objekte oder als Dicts
			liefern (z.B. in Tests). Deshalb wird hier robust mit `hasattr(...)`
			gelesen.
			"""
			recurring_list = recurring_controller.list_recurring(user_id)
			if isinstance(recurring_list, str):
				ui.notify(recurring_list, type="negative")
				return
			rows = []
			for rec in recurring_list:
				# Dauerauftraege koennen als ORM-Objekte oder als Dicts kommen.
				# Wir lesen die Felder deshalb robust aus.
				amount_val = rec.amount if hasattr(rec, 'amount') else rec.get('amount')
				interval_val = rec.interval if hasattr(rec, 'interval') else rec.get('interval')
				last_executed = rec.last_executed if hasattr(rec, 'last_executed') else rec.get('last_executed')
				# In manchen Pfaden kann `last_executed` als ISO-String vorliegen.
				if isinstance(last_executed, str):
					last_executed = date.fromisoformat(last_executed)
				# Naechste Ausfuehrung wird aus (last_executed, interval) berechnet.
				next_exec = recurring_controller.get_next_execution_date(last_executed, interval_val)
				# Falls ein Termin "heute oder frueher" ist, zeigen wir die *naechste* Ausfuehrung,
				# damit die Anzeige nicht wie "ueberfaellig" wirkt.
				if next_exec <= date.today():
					next_exec = recurring_controller.get_next_execution_date(next_exec, interval_val)
				rows.append({
					"recurring_id": rec.recurring_id if hasattr(rec, 'recurring_id') else rec.get('recurring_id'),
					"amount": f"{amount_val:,.2f}",
					"target_iban": ((rec.target_iban if hasattr(rec, "target_iban") else rec.get("target_iban")) or "").upper(),
					"category": category_map_names.get(
						rec.category_id if hasattr(rec, 'category_id') else rec.get('category_id'), "—"
					),
					"account_iban": account_map.get(
						int(rec.account_id if hasattr(rec, "account_id") else rec.get("account_id")), "N/A"
					),
					"interval": "Monatlich" if interval_val == "monthly" else "Jährlich",
					"next_execution": next_exec.strftime("%d.%m.%Y"),
				})
			recurring_table.rows = rows

		with ui.card().classes("w-full"):
			recurring_table = ui.table(columns=[
				{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
				{"name": "target_iban", "label": "Ziel-IBAN", "field": "target_iban", "align": "left"},
				{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
				{"name": "interval", "label": "Intervall", "field": "interval", "align": "left"},
				{"name": "next_execution", "label": "Nächste Ausführung", "field": "next_execution", "align": "left"},
				{"name": "account_iban", "label": "Belastungskonto", "field": "account_iban", "align": "left"},
				{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
			], rows=[]).props("dense")
			recurring_table.classes("w-full")
			with recurring_table.add_slot("no-data"):
				ui.label("Kein Dauerauftrag vorhanden").classes("text-gray-500 italic")

		recurring_table.add_slot("body-cell-actions", """
			<q-td :props="props">
				<q-btn label="Ändern" color="primary" size="sm" flat
					@click="$parent.$emit('edit_recurring', props.row)" />
				<q-btn label="Löschen" color="negative" size="sm" flat
					@click="$parent.$emit('delete_recurring', props.row)" />
			</q-td>
		""")

		def handle_delete_recurring(e) -> None:
			"""Bestaetigt und loescht einen Dauerauftrag.

			Args:
				e: NiceGUI-Event; relevante Daten stehen in `e.args` (die Tabellenzeile).
			"""
			row = e.args
			recurring_id = row.get("recurring_id")
			with ui.dialog() as confirm_dialog, ui.card():
				ui.label("Dauerauftrag wirklich löschen?").classes("text-subtitle1 font-semibold")
				ui.label(f"Betrag: {row.get('amount')} CHF | IBAN: {(row.get('target_iban') or '').upper()}").classes("text-gray-600")
				with ui.row().classes("gap-4 mt-4"):
					ui.button("Abbrechen", on_click=confirm_dialog.close).props("flat")
					def do_delete(rid=recurring_id):
						error = recurring_controller.delete_recurring(rid)
						confirm_dialog.close()
						if error:
							ui.notify(error, type="negative")
						else:
							ui.notify("Dauerauftrag gelöscht", type="positive")
							refresh_recurring_table()
					ui.button("Löschen", on_click=do_delete).props("color=negative unelevated")
			confirm_dialog.open()

		recurring_table.on("delete_recurring", handle_delete_recurring)

		def handle_edit_recurring(e) -> None:
			"""Oeffnet einen Dialog zum Bearbeiten eines Dauerauftrags.

			Args:
				e: NiceGUI-Event; relevante Daten stehen in `e.args` (die Tabellenzeile).
			"""
			row = e.args
			recurring_id = row.get("recurring_id")
			current_recurring = recurring_controller.get_by_id(recurring_id)
			if current_recurring is None:
				ui.notify("Dauerauftrag nicht gefunden", type="negative")
				return
			edit_category_options = category_controller.list_categories()

			with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
				ui.label("Dauerauftrag bearbeiten").classes("text-subtitle1 font-semibold mb-4")
				amount_edit = ui.number(
					label="Betrag (CHF)", value=current_recurring.amount, min=0.01, step=0.01
				).props("outlined").classes("w-full mb-4")
				category_edit = ui.select(
					options=edit_category_options, value=current_recurring.category_id, label="Kategorie"
				).props("outlined").classes("w-full mb-4")
				account_edit = ui.select(
					options=account_map, value=int(current_recurring.account_id), label="Belastungskonto"
				).props("outlined").classes("w-full mb-4")
				interval_edit = ui.select(
					options={"monthly": "Monatlich", "yearly": "Jährlich"},
					value=current_recurring.interval, label="Intervall"
				).props("outlined").classes("w-full mb-4")
				target_iban_edit = ui.input(
					label="Ziel-IBAN", value=current_recurring.target_iban
				).props("outlined").classes("w-full mb-4")
				with ui.row().classes("gap-4"):
					ui.button("Abbrechen", on_click=edit_dialog.close).props("flat")
					def do_edit(rid=recurring_id):
						"""Speichert Aenderungen und aktualisiert danach die Tabelle."""
						payload = {
							"amount": amount_edit.value or 0,
							"category_id": category_edit.value,
							"account_id": account_edit.value,
							"interval": interval_edit.value,
							"target_iban": target_iban_edit.value,
						}
						error = recurring_controller.update_recurring(rid, payload)
						edit_dialog.close()
						if error:
							ui.notify(error, type="negative")
						else:
							ui.notify("Dauerauftrag aktualisiert", type="positive")
							refresh_recurring_table()
					ui.button("Speichern", on_click=do_edit).props("color=primary unelevated")
			edit_dialog.open()

		recurring_table.on("edit_recurring", handle_edit_recurring)

		# Tabelle initial laden
		refresh_recurring_table()

		# === FORMULAR: NEUEN DAUERAUFTRAG ERSTELLEN (unter der Tabelle) ===
		with ui.expansion("Neuen Dauerauftrag erstellen", value=True).classes("w-full"):

			category_options = category_controller.list_categories()

			result = account_controller.list_accounts(user_id)
			if isinstance(result, str):
				form_account_options = {}
			else:
				form_account_options = {
					int(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
					((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
					for a in result
					if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
				}

			with ui.column().classes("w-full gap-4"):
				amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined").classes("w-full")
				category_select = ui.select(options=category_options, label="Kategorie").props("outlined").classes("w-full")
				account_select = ui.select(form_account_options, label="Konto").props("outlined").classes("w-full")
				iban_input = ui.input(label="Ziel-IBAN").props("outlined").classes("w-full")
				interval_select = ui.select(
					options={"monthly": "Monatlich", "yearly": "Jährlich"}, label="Intervall"
				).props("outlined").classes("w-full")
				start_date_picker = ui.date_input("Startdatum", value=date.today().isoformat()).classes("w-full")
				ui.label().bind_text_from(start_date_picker, "value", lambda v: f"Datum: {v}" if v else "")
				error_label = ui.label("").classes("text-red-600")

				async def handle_create_recurring() -> None:
					"""Legt einen neuen Dauerauftrag an.

					Der Controller erwartet die Datumswerte als ISO-String und normalisiert
					sie intern zu `datetime.date`.
				"""
					# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
					# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
					# Pflichtfeldprüfung
					if (not amount_input.value or not category_select.value
							or not account_select.value or not iban_input.value
							or not interval_select.value):
						error_label.set_text("Bitte alle Felder ausfüllen.")
						return
					error_label.set_text("")
					payload = {
						"user_id": user_id,
						"amount": amount_input.value,
						"category_id": category_select.value,
						"account_id": account_select.value,
						"target_iban": iban_input.value,
						"interval": interval_select.value,
						# Controller normalisiert ISO-String -> `date`.
						"start_date": start_date_picker.value,
					}
					error = recurring_controller.create_recurring(payload)
					if error:
						error_label.set_text(error)
						ui.notify(error, type="negative")
					else:
						ui.notify("Dauerauftrag erfolgreich erstellt", type="positive")
						amount_input.value = None
						category_select.value = None
						account_select.value = None
						iban_input.value = ""
						interval_select.value = None
						start_date_picker.value = date.today().isoformat()
						refresh_recurring_table()

				ui.button("Dauerauftrag erstellen", on_click=handle_create_recurring).classes("w-full")

def _build_transfer_form(user_id: int) -> None:
	"""Rendert das Formular fuer einen Uebertrag zwischen eigenen Konten.

	Ein Uebertrag ist eine Umbuchung zwischen zwei eigenen Konten (Quelle -> Ziel).
Die fachliche Validierung passiert im Service (z.B. Existenz der Konten,
ausreichender Kontostand, etc.).

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.payment_controller import payment_controller

	# Konten laden (nur aktive Konten koennen Quelle/Ziel sein).
	# Fachliche Validierung (z.B. "nur eigene Konten") passiert im Service.
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		account_options = {}
	else:
		account_options = {
			(a.account_id if hasattr(a, "account_id") else a.get("account_id")): 
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in result
			if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
		}

	with ui.card().classes("w-full"):

		# Von-Konto
		from_account_select = ui.select(
			options=account_options,
			label="Von-Konto",
		).props("outlined")
		from_account_select.classes("w-full mb-4")

		# Zu-Konto
		to_account_select = ui.select(
			options=account_options,
			label="Zu-Konto",
		).props("outlined")
		to_account_select.classes("w-full mb-4")

		# Betrag
		amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined")
		amount_input.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_transfer() -> None:
			"""Fuehrt die Umbuchung ueber den `PaymentController` aus."""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
			payload = {
				"from_account_id": from_account_select.value,
				"to_account_id": to_account_select.value,
				"amount": amount_input.value or 0,
			}

			error = payment_controller.create_transfer(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Übertrag erfolgreich", type="positive")
				amount_input.value = 0

		ui.button("Umbuchen", on_click=handle_transfer).classes("w-full")


def _build_sidebar() -> None:
	"""Baut die Navigation (Sidebar) fuer die Transaktions-View."""
	from nicegui import ui
	user_id = app_state.get("user_id")

	ui.label("BetterBank").classes("text-h6 font-bold text-white px-4 pt-4 pb-0")
	if user_id:
		from src.ui.controllers.auth_controller import auth_controller
		username = auth_controller.get_username(user_id)
		if username:
			ui.label(username).classes("text-sm text-white px-4 pb-3")

	ui.separator()

	with ui.column().classes("gap-1 px-2 pb-4 pt-2"):
		ui.button("Dashboard", icon="home", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Transaktionen", icon="show_chart", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated align=left").classes("w-full justify-start sidebar-active")
		ui.button("Budget", icon="savings", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Konten", icon="account_balance", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Karten", icon="credit_card", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated align=left").classes("w-full justify-start")


def _logout() -> None:
	"""Meldet den User ab und navigiert zur Login-Seite.

	WARUM NUR ZWEI ZEILEN?
	    Die eigentliche Arbeit (app_state zuruecksetzen, Logout-Flag setzen)
	    erledigt der Controller. Die View ist nur fuer die Navigation zustaendig.
	    Trennung: Controller = Logik, View = Anzeige & Navigation.

	WARUM KEIN ui.notify() HIER?
	    ui.notify() nach ui.navigate.to("/") funktioniert nicht zuverlaessig –
	    die Seite wechselt, bevor die Meldung angezeigt werden kann.
	    Stattdessen setzt der Controller ein Flag (show_logout_message = True),
	    das die Login-Seite beim Laden prueft und die Meldung dort anzeigt.
	"""
	from nicegui import ui
	# Logik-Aufgabe: Controller setzt app_state zurueck und setzt das Logout-Flag.
	auth_controller.logout()
	# View-Aufgabe: zur Login-Seite navigieren.
	ui.navigate.to("/")


def _open_settings_dialog(user_id: int) -> None:
	"""Oeffnet einen einfachen Dialog mit Kontoeinstellungen.

	Die Daten kommen aus dem `UserController`. In dieser View werden Telefon und
	Adresse aktuell nur angezeigt; Aenderungen werden als "beantragt" simuliert.
	"""
	from nicegui import ui
	from src.ui.controllers.user_controller import user_controller

	profile = user_controller.get_profile(user_id)
	if isinstance(profile, str):
		ui.notify(profile, type="negative")
		return

	with ui.dialog() as dlg, ui.card().classes("w-96"):
		ui.label("Kontoeinstellungen").classes("text-h6 font-semibold mb-4")

		# Telefonnummer (nur Anzeige)
		with ui.card().classes("w-full mb-3").props("flat bordered"):
			with ui.row().classes("w-full items-center justify-between p-2"):
				with ui.column().classes("gap-0"):
					ui.label("Telefonnummer").classes("text-sm text-gray-500")
					ui.label(profile.phone or "—").classes("text-base")
					ui.label("Format: +41 XX XXX XX XX").classes("text-xs text-gray-400")
				ui.button(
					"Telefonnummeränderung beantragen",
					on_click=lambda: ui.notify("Formular beantragt", type="positive")
				).props("flat color=primary no-caps")

		# Wohnadresse (nur Anzeige)
		with ui.card().classes("w-full mb-4").props("flat bordered"):
			with ui.row().classes("w-full items-center justify-between p-2"):
				with ui.column().classes("gap-0"):
					ui.label("Wohnadresse").classes("text-sm text-gray-500")
					ui.label(profile.address or "—").classes("text-base")
				ui.button(
					"Adressänderung beantragen",
					on_click=lambda: ui.notify("Formular beantragt", type="positive")
				).props("flat color=primary no-caps")

		ui.button("Schliessen", on_click=dlg.close).props("flat").classes("w-full")
	dlg.open()


    
