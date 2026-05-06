"""src.ui.views.budget_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

Budgets sind monatliche Limits (optional pro Kategorie). Die UI bietet:

- Budget-Liste, getrennt nach "aktiv" und "abgelaufen"
- Formular zum Anlegen eines neuen Budgets
- Statusberechnung (OK / Ueberschritten) ueber den `BudgetController`

Wichtiges Zusammenspiel:

- `BudgetController` delegiert an `BudgetService`, der u.a. die
	Unique-Constraint-Logik (Upsert) und die Verbrauchsberechnung implementiert.
- Die View rendert Tabellen und Dialoge und bleibt bewusst "duenn" in
	fachlichen Regeln.

Route: `/budget`
"""

from datetime import datetime

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

	# ===== TOP-RIGHT: LOGOUT =====
	with ui.header():
		with ui.row().classes("w-full justify-end items-center gap-2"):
			with ui.button(icon="settings").props("flat round").classes("text-white"):
				with ui.menu():
					ui.menu_item("Kontoeinstellungen", on_click=lambda: _open_settings_dialog(user_id))
			ui.button("Abmelden", icon="logout", on_click=lambda: _logout()) \
				.props("flat no-caps") \
				.classes("text-white font-semibold")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		ui.label("Budget").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_list = ui.tab("Budget-Übersicht")
			tab_create = ui.tab("Neues Budget")

		with ui.tab_panels(tabs, value=tab_list):

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

	with ui.card().classes("w-full max-w-md"):

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
			# Ein Budget ist eindeutig ueber (user_id, month, year, category_id).
			# Wenn `category_id` None ist, bedeutet das: globales Budget (alle Kategorien).
			payload = {
				"user_id": user_id,
				"month": month_select.value,
				"year": year_select.value,
				"limit_amount": limit_input.value or 0,
				"category_id": category_select.value,
			}

			error = budget_controller.set_budget(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Budget gespeichert", type="positive")
				limit_input.value = 0
				category_select.value = None

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
		active_table = ui.table(columns=COLUMNS, rows=[]).props("dense")
		active_table.classes("w-full")
		active_table.add_slot("body-cell-actions", ACTION_SLOT)

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
		expired_table = ui.table(columns=EXPIRED_COLUMNS, rows=[]).props("dense")
		expired_table.classes("w-full")
		expired_table.add_slot("body-cell-actions", EXPIRED_ACTION_SLOT)
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

	Wichtig: Der Budgetstatus (Verbrauch/Limit) wird pro Budget ueber den
	`BudgetController.check_budget_status(...)` abgefragt.

	Args:
		user_id: ID des eingeloggten Users.
		active_table: Tabelle, die die aktiven Budgets angezeigt bekommt.
		expired_table: Tabelle, die die abgelaufenen Budgets angezeigt bekommt.
		cur_year: Aktuelles Jahr (fuer die Aktiv/Abgelaufen-Sortierung).
		cur_month: Aktueller Monat (fuer die Aktiv/Abgelaufen-Sortierung).
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller

	try:
		# Controller liefert Liste oder Fehlertext.
		budgets = budget_controller.list_budgets(user_id)
		if isinstance(budgets, str):
			ui.notify(budgets, type="negative")
			return
		category_names = category_controller.list_categories()

		active_rows = []
		expired_rows = []
		month_names = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
					   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

		for budget in budgets:
			# Darstellung: "Monat/Jahr" fuer eine kompakte Tabellenanzeige.
			month_name = month_names[budget.month]
			month_year = f"{month_name} {budget.year}"
			try:
				# Statusberechnung: Service summiert Ausgaben im Monat und vergleicht mit Limit.
				# Der Controller gibt bei Fehlern einen String zurueck.
				status_data = budget_controller.check_budget_status(
					user_id=user_id, month=budget.month,
					year=budget.year, category_id=budget.category_id,
				)
				if isinstance(status_data, str):
					is_exceeded = False
					used_amount = 0
				else:
					is_exceeded = status_data.get("is_exceeded", False)
					used_amount = status_data.get("current_spending", 0)
			except Exception:
				is_exceeded = False
				used_amount = 0

			row = {
				"budget_id": budget.budget_id,
				"month_year": month_year,
				# `category_id is None` bedeutet: Budget gilt fuer *alle* Kategorien.
				"category": "Alle" if budget.category_id is None
					else category_names.get(budget.category_id, f"ID {budget.category_id}"),
				"limit": f"{budget.limit_amount:,.2f}",
				"used": f"{used_amount:,.2f}",
				"status": "OK ✓" if not is_exceeded else "ÜBERSCHRITTEN ⚠",
			}

			# Aktiv/abgelaufen: abgelaufen sind Budgets aus Monaten vor dem aktuellen Monat.
			# (Das ist reine UI-Sortierung; fachlich ist ein Budget immer an seinen Monat gebunden.)
			is_active = (budget.year > cur_year) or (
				budget.year == cur_year and budget.month >= cur_month
			)
			if is_active:
				active_rows.append(row)
			else:
				expired_rows.append(row)

		active_table.rows = active_rows
		expired_table.rows = expired_rows
	except Exception as ex:
		ui.notify(f"Fehler: {str(ex)}", type="negative")


def _build_sidebar() -> None:
	"""Baut die Sidebar-Navigation (Links zu den Views).

	Falls ein User eingeloggt ist, wird zusaetzlich der Username angezeigt.
	"""
	from nicegui import ui
	ui.label("BetterBank").classes("text-h6 font-bold p-4")

	user_id = app_state.get("user_id")
	if user_id:
		from src.ui.controllers.auth_controller import auth_controller
		username = auth_controller.get_username(user_id)
		if username:
			ui.label(username).classes("text-sm text-gray-500 px-4 pb-2")

	ui.separator()

	with ui.column().classes("gap-2 p-4"):
		ui.button("📊 Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💳 Transaktionen", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💰 Budget", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🏦 Konten", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🎫 Karten", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated").classes("w-full justify-start")


def _logout() -> None:
	"""Meldet den User ab und navigiert zur Startseite."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")


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
