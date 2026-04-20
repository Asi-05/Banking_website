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
		ui.button(icon="logout", on_click=lambda: _logout()).props("flat")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		ui.label("Budget").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_create = ui.tab("Neues Budget")
			tab_list = ui.tab("Budget-Übersicht")

		with ui.tab_panels(tabs):

			# ===== TAB 1: BUDGET SETZEN =====
			with ui.tab_panel(tab_create):
				_build_budget_form(user_id)

			# ===== TAB 2: BUDGET-LISTE =====
			with ui.tab_panel(tab_list):
				_build_budget_list(user_id)


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
		categories = CategoryRepository.list_all(session)
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
	"""
	Zeigt Übersicht aller Budgets des Users mit Status (OK / ÜBERSCHRITTEN).
	"""
	from nicegui import ui

	from src.services.budget_service import budget_service

	with ui.card().classes("w-full"):

		budgets_table = ui.table(columns=[
			{"name": "month_year", "label": "Monat/Jahr", "field": "month_year", "align": "left"},
			{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
			{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
			{"name": "used", "label": "Genutzt (CHF)", "field": "used", "align": "right"},
			{"name": "status", "label": "Status", "field": "status", "align": "center"},
		], rows=[]).props("dense")
		budgets_table.classes("w-full")

		# Laden
		_refresh_budget_list(user_id, budgets_table)


def _refresh_budget_list(user_id: int, budgets_table=None) -> None:
	"""
	Lädt alle Budgets des Users und zeigt sie an.
	Berechnet die aktuelle Auslastung pro Budget.
	"""
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

		# Kategorienamen laden für Anzeige
		with Session(engine) as session:
			categories = CategoryRepository.list_all(session)
		category_names = {c.category_id: c.name for c in categories}

		rows = []
		for budget in budgets:
			month_name = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"][budget.month]
			month_year = f"{month_name} {budget.year}"

			# Budgetstatus prüfen (nutzt check_budget_status)
			try:
				status_data = budget_service.check_budget_status(
					user_id=user_id,
					month=budget.month,
					year=budget.year,
					category_id=budget.category_id,
				)
				is_exceeded = status_data.get("is_exceeded", False)
				used_amount = status_data.get("current_spending", 0)
			except Exception:
				is_exceeded = False
				used_amount = 0

			# Status-Badge
			status_badge = "OK ✓" if not is_exceeded else "ÜBERSCHRITTEN ⚠"
			status_color = "green-6" if not is_exceeded else "red-6"

			# Kategorienamen
			category_display = "Alle" if budget.category_id is None else category_names.get(budget.category_id, f"ID {budget.category_id}")

			rows.append({
				"month_year": month_year,
				"category": category_display,
				"limit": f"{budget.limit_amount:,.2f}",
				"used": f"{used_amount:,.2f}",
				"status": status_badge,
			})

		if budgets_table:
			budgets_table.rows = rows

	except Exception as e:
		ui.notify(f"Fehler beim Laden der Budgets: {str(e)}", type="negative")


def _build_sidebar() -> None:
	"""Baut die Navigation."""
	from nicegui import ui
	ui.label("Betterbank").classes("text-h6 font-bold p-4")
	ui.separator()

	with ui.column().classes("gap-2 p-4"):
		ui.button("📊 Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💳 Transaktionen", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💰 Budget", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🏦 Konten", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🎫 Karten", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💸 Zahlungen", on_click=lambda: ui.navigate.to("/payments")).props("flat unelevated").classes("w-full justify-start")


def _logout() -> None:
	"""Meldet den User ab."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")
