"""src.ui.views.budget_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

=== WAS IST EIN BUDGET? ===
Ein Budget ist ein monatliches Ausgabenlimit. Es kann:
    - Global gelten (alle Kategorien zusammen)
    - Pro Kategorie gelten (z.B. "maximal CHF 200 fuer Transport im Mai")

Der Budget-Status zeigt "OK ✓" oder "ÜBERSCHRITTEN ⚠" je nachdem ob die
Ausgaben in diesem Monat das Limit ueberschreiten.

=== WAS KANN DER USER AUF DIESER SEITE TUN? ===
    Tab 1 – Budget-Übersicht:
        Alle Budgets anzeigen, getrennt nach "aktiv" (aktueller Monat oder
        Zukunft) und "abgelaufen" (vergangene Monate).
        Jedes Budget zeigt: Monat/Jahr, Kategorie, Limit, Genutzt, Status.
        Aktive Budgets koennen bearbeitet oder geloescht werden.

    Tab 2 – Neues Budget:
        Neues Budget anlegen (Monat, Jahr, Limit, Kategorie optional).
        UPSERT: wenn schon ein Budget fuer diesen Zeitraum + Kategorie
        existiert, wird es aktualisiert statt neu angelegt.

=== WAS DIESE VIEW NICHT TUT ===
Sie enthaelt KEINE fachliche Logik. Alle Regeln liegen im `BudgetService`:
    - UPSERT-Logik (vorhanden → update, nicht vorhanden → create)
    - Verbrauchsberechnung (Summe aller Ausgaben im Zeitraum)

=== AUFRUF-KETTE: BUDGET SETZEN ===
    User klickt "Budget speichern"
    → handle_set_budget()                        [diese View]
    → budget_controller.set_budget(payload)       [BudgetController]
    → BudgetService.set_budget(payload)           [UPSERT-Logik]
    → BudgetRepository.get_by_scope(...)          [existiert schon?]
    → create ODER update → DB commit
    → None bei Erfolg, String bei Fehler

=== AUFRUF-KETTE: BUDGETSTATUS PRUEFEN ===
    _refresh_split_budget_list(...)
    → budget_controller.list_budgets(user_id)
    → pro Budget: budget_controller.check_budget_status(user_id, month, year, ...)
    → BudgetService.check_budget_status(...)
    → TransactionRepository (Ausgaben summieren)
    → is_exceeded + current_spending zurueck → Tabelle befuellen

=== AKTIV / ABGELAUFEN ===
    Aktiv: Budget-Monat/Jahr >= heutiger Monat/Jahr
    Abgelaufen: Budget-Monat/Jahr < heutiger Monat/Jahr
    Diese Trennung ist reine UI-Logik (kein fachlicher Unterschied).

=== LOGIN-GUARD ===
    if app_state.get("current_user") is None:
        ui.navigate.to("/")    # kein User eingeloggt → zurueck zum Login
        return

=== ARCHITEKTUR-KETTE ===
    Route "/budget" → show()
    → Tab 1: _build_budget_list() → _refresh_split_budget_list()
             → budget_controller → BudgetService → TransactionRepository
    → Tab 2: _build_budget_form() → budget_controller.set_budget()
             → BudgetService → BudgetRepository → DB

Route: `/budget`
"""

from datetime import datetime

from src.ui.controllers.auth_controller import auth_controller
from src.ui.controllers.budget_controller import budget_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Budget-Seite (Tabs: Uebersicht und neues Budget).

	Die Seite ist geschuetzt: Ohne Login wird zur Startseite umgeleitet.
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

		ui.label("Budget").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_list = ui.tab("Budget-Übersicht")
			tab_create = ui.tab("Neues Budget")

		with ui.tab_panels(tabs, value=tab_list).classes("w-full"):

			# ===== TAB 1: BUDGET-LISTE =====
			with ui.tab_panel(tab_list):
				_build_budget_list(user_id)

			# ===== TAB 2: BUDGET SETZEN =====
			with ui.tab_panel(tab_create):
				_build_budget_form(user_id)


def _build_budget_form(user_id: int) -> None:
	"""Rendert das Formular zum Setzen eines neuen Budgets.

	Der Nutzer waehlt Monat/Jahr, ein Limit und optional eine Kategorie.
Wenn keine Kategorie gewaehlt ist (`category_id is None`), gilt das Budget
global fuer alle Kategorien.

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller

	category_options = category_controller.list_categories()

	# Monats-Optionen (deutsche Namen) fuer ein lesbares Dropdown.
	monat_optionen = {
		1: "Januar",
		2: "Februar",
		3: "März",
		4: "April",
		5: "Mai",
		6: "Juni",
		7: "Juli",
		8: "August",
		9: "September",
		10: "Oktober",
		11: "November",
		12: "Dezember",
	}

	# Jahre dynamisch berechnen: so kann man auch Budgets fuer naechstes Jahr setzen.
	current_year = datetime.now().year
	jahr_optionen = list(range(2020, current_year + 3))

	with ui.card().classes("w-full"):

		# Monat
		month_select = ui.select(
			options=monat_optionen,
			value=datetime.now().month,
			label="Monat",
		).props("outlined")
		month_select.classes("w-full mb-4")

		# Jahr
		year_select = ui.select(
			options=jahr_optionen,
			value=current_year,
			label="Jahr",
		).props("outlined")
		year_select.classes("w-full mb-4")

		# Limit
		limit_input = ui.number(label="Limit (CHF)", min=0.01, step=0.01).props("outlined")
		limit_input.classes("w-full mb-4")

		# Kategorie (optional)
		category_select = ui.select(
			options={None: "Globales Budget", **category_options},
			value=None,
			label="Kategorie (optional)",
		).props("outlined")
		category_select.classes("w-full mb-4")

		# Fehlerbehandlung
		error_label = ui.label("").classes("text-red-600 mb-4")

		# Speichern
		async def handle_set_budget() -> None:
			"""Speichert ein Budget ueber den Controller.

			Hinweis:
				Ein Budget ist eindeutig ueber (user_id, month, year, category_id).
				Der Service kann deshalb ein vorhandenes Budget fuer den gleichen
				Zeitraum/die gleiche Kategorie aktualisieren (Upsert).
			"""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
			if not limit_input.value:
				error_label.set_text("Bitte geben Sie ein Limit an.")
				ui.notify("Bitte geben Sie ein Limit an.", type="warning")
				return

			# Ein Budget ist eindeutig ueber (user_id, month, year, category_id).
			# Wenn `category_id` None ist, bedeutet das: globales Budget (alle Kategorien).
			payload = {
				"user_id": user_id,
				"month": month_select.value,
				"year": year_select.value,
				"limit_amount": limit_input.value or 0,
				"category_id": category_select.value,
			}

			category_display = "Globales Budget" if not category_select.value else category_options.get(category_select.value, "")

			with ui.dialog() as dlg, ui.card().classes("w-96"):
				ui.label("Budget bestätigen").classes("text-subtitle1 font-semibold mb-3")
				with ui.card().classes("w-full mb-3").props("flat bordered"):
					ui.label(f"Monat/Jahr: {monat_optionen.get(month_select.value, '')} {year_select.value}").classes("text-sm text-gray-700")
					ui.label(f"Limit: {limit_input.value:,.2f} CHF").classes("text-sm text-gray-700 font-medium")
					ui.label(f"Kategorie: {category_display}").classes("text-sm text-gray-600")
				with ui.row().classes("gap-4 mt-4 justify-end"):
					ui.button("Abbrechen", on_click=dlg.close).props("flat")
					def do_save(p=payload):
						error = budget_controller.set_budget(p)
						dlg.close()
						if error:
							error_label.set_text(error)
							ui.notify(error, type="negative")
						else:
							ui.notify("Budget gespeichert", type="positive")
							limit_input.value = 0
							category_select.value = None
					ui.button("Budget speichern", on_click=do_save).props("color=primary unelevated")
			dlg.open()

		ui.button("Budget speichern", on_click=handle_set_budget).classes("w-full")


def _build_budget_list(user_id: int) -> None:
	"""Rendert die Budget-Listen (aktive vs. abgelaufene Budgets).

	Die Trennung passiert anhand des aktuellen Monats/Jahres.

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui
	from datetime import date

	today = date.today()
	cur_year = today.year
	cur_month = today.month

	ui.add_css('''
		.budget-table .q-table { table-layout: fixed; width: 100%; }
		.budget-table .q-table th:nth-child(1), .budget-table .q-table td:nth-child(1) { width: 12%; }
		.budget-table .q-table th:nth-child(2), .budget-table .q-table td:nth-child(2) { width: 22%; }
		.budget-table .q-table th:nth-child(3), .budget-table .q-table td:nth-child(3) { width: 17%; }
		.budget-table .q-table th:nth-child(4), .budget-table .q-table td:nth-child(4) { width: 17%; }
		.budget-table .q-table th:nth-child(5), .budget-table .q-table td:nth-child(5) { width: 15%; }
		.budget-table .q-table th:nth-child(6), .budget-table .q-table td:nth-child(6) { width: 17%; }
	''')

	COLUMNS = [
		{"name": "month_year", "label": "Monat/Jahr", "field": "month_year", "align": "left"},
		{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
		{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
		{"name": "used", "label": "Genutzt (CHF)", "field": "used", "align": "right"},
		{"name": "status", "label": "Status", "field": "status", "align": "center"},
		{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
	]

	EXPIRED_COLUMNS = [
		{"name": "month_year", "label": "Monat/Jahr", "field": "month_year", "align": "left"},
		{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
		{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
		{"name": "used", "label": "Genutzt (CHF)", "field": "used", "align": "right"},
		{"name": "status", "label": "Status", "field": "status", "align": "center"},
		{"name": "actions", "label": "Löschen", "field": "actions", "align": "center"},
	]

	ACTION_SLOT = """
		<q-td :props="props">
			<q-btn label="Bearbeiten" color="primary" size="sm" flat
				@click="$parent.$emit('edit_budget', props.row)" />
			<q-btn label="Löschen" color="negative" size="sm" flat
				@click="$parent.$emit('delete_budget', props.row)" />
		</q-td>
	"""

	EXPIRED_ACTION_SLOT = """
		<q-td :props="props">
			<q-btn label="Löschen" color="negative" size="sm" flat
				@click="$parent.$emit('delete_budget', props.row)" />
		</q-td>
	"""

	# === KASTEN 1: AKTIVE BUDGETS ===
	with ui.card().classes("w-full"):
		ui.label("Aktive Budgets").classes("text-subtitle1 font-semibold mb-2")
		active_table = ui.table(columns=COLUMNS, rows=[]).props("dense").classes("w-full budget-table")
		with active_table.add_slot("no-data"):
			ui.label("Kein aktives Budget vorhanden").classes("text-gray-500 italic")
		active_table.add_slot("body-cell-actions", ACTION_SLOT)
		active_table.add_slot("body-cell-status", """
			<q-td :props="props">
				<span :class="props.row.status.includes('OK') ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'">
					{{ props.row.status }}
				</span>
			</q-td>
		""")

		def handle_edit_active(e) -> None:
			"""Oeffnet den Edit-Dialog fuer ein aktives Budget.

			Args:
				e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
			"""
			_open_edit_dialog(e, user_id, active_table, expired_table, cur_year, cur_month)
		def handle_delete_active(e) -> None:
			"""Oeffnet den Delete-Dialog fuer ein aktives Budget.

			Args:
				e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
			"""
			_open_delete_dialog(e, user_id, active_table, expired_table, cur_year, cur_month)
		active_table.on("edit_budget", handle_edit_active)
		active_table.on("delete_budget", handle_delete_active)

	# === KASTEN 2: ABGELAUFENE BUDGETS ===
	with ui.card().classes("w-full mt-4"):
		ui.label("Abgelaufene Budgets").classes("text-subtitle1 font-semibold mb-2")
		expired_table = ui.table(columns=EXPIRED_COLUMNS, rows=[]).props("dense").classes("w-full budget-table")
		with expired_table.add_slot("no-data"):
			ui.label("Kein abgelaufenes Budget vorhanden").classes("text-gray-500 italic")
		expired_table.add_slot("body-cell-actions", EXPIRED_ACTION_SLOT)
		expired_table.add_slot("body-cell-status", """
			<q-td :props="props">
				<span :class="props.row.status.includes('OK') ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'">
					{{ props.row.status }}
				</span>
			</q-td>
		""")
		def handle_delete_expired(e) -> None:
			"""Oeffnet den Delete-Dialog fuer ein abgelaufenes Budget.

			Args:
				e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
			"""
			_open_delete_dialog(e, user_id, active_table, expired_table, cur_year, cur_month)
		expired_table.on("delete_budget", handle_delete_expired)

	_refresh_split_budget_list(user_id, active_table, expired_table, cur_year, cur_month)


def _open_edit_dialog(e, user_id, active_table, expired_table, cur_year, cur_month) -> None:
	"""Oeffnet einen Dialog zum Bearbeiten eines Budgets (Limit aendern).

	Args:
		e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
		user_id: ID des eingeloggten Users.
		active_table: Tabelle mit aktiven Budgets (wird nach dem Speichern refreshed).
		expired_table: Tabelle mit abgelaufenen Budgets (wird nach dem Speichern refreshed).
		cur_year: Aktuelles Jahr (fuer die Aktiv/Abgelaufen-Sortierung).
		cur_month: Aktueller Monat (fuer die Aktiv/Abgelaufen-Sortierung).
	"""
	from nicegui import ui
	row = e.args
	budget_id = row.get("budget_id")
	with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
		ui.label("Budget bearbeiten").classes("text-subtitle1 font-semibold mb-4")
		limit_edit = ui.number(
			label="Limit (CHF)",
			value=float(str(row.get("limit", "0")).replace(",", "")),
			min=0.01, step=0.01,
		).props("outlined").classes("w-full mb-4")
		with ui.row().classes("gap-4"):
			ui.button("Abbrechen", on_click=edit_dialog.close).props("flat")
			def do_edit(bid=budget_id):
				"""Bestaetigt das Update und aktualisiert danach die Tabellen."""
				error = budget_controller.update_budget(bid, limit_edit.value or 0)
				edit_dialog.close()
				if error:
					ui.notify(error, type="negative")
				else:
					ui.notify("Budget aktualisiert", type="positive")
					_refresh_split_budget_list(user_id, active_table, expired_table, cur_year, cur_month)
			ui.button("Speichern", on_click=do_edit).props("color=primary unelevated")
	edit_dialog.open()


def _open_delete_dialog(e, user_id, active_table, expired_table, cur_year, cur_month) -> None:
	"""Oeffnet einen Dialog zum Loeschen eines Budgets.

	Args:
		e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
		user_id: ID des eingeloggten Users.
		active_table: Tabelle mit aktiven Budgets (wird nach dem Loeschen refreshed).
		expired_table: Tabelle mit abgelaufenen Budgets (wird nach dem Loeschen refreshed).
		cur_year: Aktuelles Jahr (fuer die Aktiv/Abgelaufen-Sortierung).
		cur_month: Aktueller Monat (fuer die Aktiv/Abgelaufen-Sortierung).
	"""
	from nicegui import ui
	row = e.args
	budget_id = row.get("budget_id")
	with ui.dialog() as confirm_dialog, ui.card():
		ui.label("Budget wirklich löschen?").classes("text-subtitle1 font-semibold")
		ui.label(f"Zeitraum: {row.get('month_year')} | Kategorie: {row.get('category')}").classes("text-gray-600")
		with ui.row().classes("gap-4 mt-4"):
			ui.button("Abbrechen", on_click=confirm_dialog.close).props("flat")
			def do_delete(bid=budget_id):
				"""Bestaetigt das Loeschen und aktualisiert danach die Tabellen."""
				error = budget_controller.delete_budget(bid)
				confirm_dialog.close()
				if error:
					ui.notify(error, type="negative")
				else:
					ui.notify("Budget gelöscht", type="positive")
					_refresh_split_budget_list(user_id, active_table, expired_table, cur_year, cur_month)
			ui.button("Löschen", on_click=do_delete).props("color=negative unelevated")
	confirm_dialog.open()


def _refresh_split_budget_list(user_id, active_table, expired_table, cur_year, cur_month) -> None:
	"""Laedt Budgets neu und splittet sie in aktive/abgelaufene Tabellen.

	Args:
		user_id: ID des eingeloggten Users.
		active_table: Tabelle fuer aktive Budgets.
		expired_table: Tabelle fuer abgelaufene Budgets.
		cur_year: Nicht mehr verwendet (Logik im Controller).
		cur_month: Nicht mehr verwendet (Logik im Controller).
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller

	try:
		category_names = category_controller.list_categories()
		grouped = budget_controller.list_budgets_grouped(user_id, category_names)
		if isinstance(grouped, str):
			ui.notify(grouped, type="negative")
			return
		active_table.rows = grouped["active"]
		expired_table.rows = grouped["expired"]
	except Exception as ex:
		ui.notify(f"Fehler: {str(ex)}", type="negative")


def _build_sidebar() -> None:
	"""Baut die Sidebar-Navigation (Links zu den Views).

	Falls ein User eingeloggt ist, wird zusaetzlich der Username angezeigt.
	"""
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
		ui.button("Transaktionen", icon="show_chart", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Budget", icon="savings", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated align=left").classes("w-full justify-start sidebar-active")
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
	"""Oeffnet den Kontoeinstellungen-Dialog (aktuell nur Anzeige).

	Die Daten werden ueber den `UserController` geladen. In dieser View werden
	Telefonnummer und Adresse nur angezeigt; Aenderungen werden als "beantragt"
	simuliert.

	Args:
		user_id: ID des eingeloggten Users.
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
