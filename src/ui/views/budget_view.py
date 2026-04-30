"""
Budget View - Betterbank Banking App
Implementiert US5: Monatliche Limits setzen und Budget-Status anzeigen
Route: /budget
"""

from datetime import datetime

from src.ui.controllers.budget_controller import budget_controller
from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt Budget-Erfassungsformular und Budget-Übersicht.
	"""
	from nicegui import ui

	# Sicherheitsprüfung
	if app_state.get("current_user") is None:
		ui.navigate.to("/")
		return

	user_id = app_state.get("user_id")

	# ===== SIDEBAR =====
	with ui.left_drawer():
		_build_sidebar()

	# ===== TOP-RIGHT: LOGOUT =====
	with ui.header():
		with ui.row().classes("w-full justify-end items-center"):
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
	"""
	Baut Formular zum Setzen eines neuen Budgets.
	Monat: Dropdown 1-12 mit Namen, Jahr: dynamisch 2020 bis current+2, Limit, Kategorie optional.
	"""
	from nicegui import ui

	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

	# Kategorien laden
	with Session(engine) as session:
		category_repository = CategoryRepository(session)
		categories = category_repository.list_all()
	category_options = {c.category_id: c.name for c in categories}

	# Monats-Optionen (deutscher Name)
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

	# Jahre dynamisch berechnen
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
			"""Speichert das neue Budget."""
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
			_open_edit_dialog(e, user_id, active_table, expired_table, cur_year, cur_month)
		def handle_delete_active(e) -> None:
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
			_open_delete_dialog(e, user_id, active_table, expired_table, cur_year, cur_month)
		expired_table.on("delete_budget", handle_delete_expired)

	_refresh_split_budget_list(user_id, active_table, expired_table, cur_year, cur_month)


def _open_edit_dialog(e, user_id, active_table, expired_table, cur_year, cur_month) -> None:
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
	from nicegui import ui
	row = e.args
	budget_id = row.get("budget_id")
	with ui.dialog() as confirm_dialog, ui.card():
		ui.label("Budget wirklich löschen?").classes("text-subtitle1 font-semibold")
		ui.label(f"Zeitraum: {row.get('month_year')} | Kategorie: {row.get('category')}").classes("text-gray-600")
		with ui.row().classes("gap-4 mt-4"):
			ui.button("Abbrechen", on_click=confirm_dialog.close).props("flat")
			def do_delete(bid=budget_id):
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
	from nicegui import ui
	from src.services.budget_service import budget_service
	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

	try:
		budgets = budget_service.list_budgets(user_id)
		if isinstance(budgets, str):
			ui.notify(budgets, type="negative")
			return
		with Session(engine) as session:
			category_names = {c.category_id: c.name for c in CategoryRepository(session).list_all()}

		active_rows = []
		expired_rows = []
		month_names = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
					   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

		for budget in budgets:
			month_name = month_names[budget.month]
			month_year = f"{month_name} {budget.year}"
			try:
				status_data = budget_service.check_budget_status(
					user_id=user_id, month=budget.month,
					year=budget.year, category_id=budget.category_id,
				)
				is_exceeded = status_data.get("is_exceeded", False)
				used_amount = status_data.get("current_spending", 0)
			except Exception:
				is_exceeded = False
				used_amount = 0

			row = {
				"budget_id": budget.budget_id,
				"month_year": month_year,
				"category": "Alle" if budget.category_id is None
					else category_names.get(budget.category_id, f"ID {budget.category_id}"),
				"limit": f"{budget.limit_amount:,.2f}",
				"used": f"{used_amount:,.2f}",
				"status": "OK ✓" if not is_exceeded else "ÜBERSCHRITTEN ⚠",
			}

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
	"""Baut die Navigation."""
	from nicegui import ui
	ui.label("BetterBank").classes("text-h6 font-bold p-4")
	
	# Benutzername laden und anzeigen
	user_id = app_state.get("user_id")
	if user_id:
		from src.data_access.repositories.user_repository import UserRepository
		from src.data_access.db import engine
		from sqlmodel import Session
		
		with Session(engine) as session:
			user = UserRepository(session).get_by_id(user_id)
			if user:
				ui.label(f"{user.first_name} {user.last_name}").classes("text-sm text-gray-500 px-4 pb-2")
	
	ui.separator()

	with ui.column().classes("gap-2 p-4"):
		ui.button("📊 Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💳 Transaktionen", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💰 Budget", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🏦 Konten", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🎫 Karten", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated").classes("w-full justify-start")


def _logout() -> None:
	"""Meldet den User ab."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")
