"""
Dashboard View - Betterbank Banking App
Implementiert US4: Dashboard mit Gesamtbilanz, Summen und Diagrammen
Route: /dashboard
"""

from datetime import date

from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt das Dashboard mit Gesamtbilanz, Einnahmen/Ausgaben und Diagrammen.
	Enthält Sidebar-Navigation und geschützten Zugriff.
	"""
	from nicegui import ui

	# Sicherheitsprüfung: Nur für eingeloggte User
	if app_state.get("current_user") is None:
		ui.navigate.to("/")
		return

	user_id = app_state.get("user_id")

	# ===== SIDEBAR & LAYOUT =====
	with ui.left_drawer() as left_drawer:
		left_drawer.set_value(True)
		_build_sidebar()

	# ===== TOP-RIGHT: USERNAME + LOGOUT =====
	with ui.header():
		with ui.row().classes("w-full justify-end items-center"):
			ui.button("Abmelden", icon="logout", on_click=lambda: _logout()) \
				.props("flat no-caps") \
				.classes("text-white font-semibold")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		# Titel
		ui.label("Dashboard").classes("text-h4 font-bold")

		# Gesamtvermögen (bleibt oben)
		balance_container = ui.column().classes("w-full")

		# Kalender nebeneinander + Filter-Button auf gleicher Höhe
		with ui.row().classes("w-full gap-4 items-center"):
			with ui.card().classes(""):
				ui.label("Von").classes("text-sm text-gray-500 mb-1")
				start_date_picker = ui.date(
					value=date(date.today().year, date.today().month, 1).isoformat()
				).props("first-day-of-week=1")

			with ui.card().classes(""):
				ui.label("Bis").classes("text-sm text-gray-500 mb-1")
				end_date_picker = ui.date(
					value=date.today().isoformat()
				).props("first-day-of-week=1")

			ui.button("Filter anwenden", on_click=lambda: _refresh_dashboard(
				user_id,
				start_date_picker,
				end_date_picker,
				balance_container,
				income_expense_container,
				chart_container,
			)).props("unelevated color=primary")

		# Zeile 2: Einnahmen und Ausgaben
		income_expense_container = ui.row().classes("w-full gap-4")

		# Zeile 3: Diagramm volle Breite
		chart_container = ui.column().classes("w-full gap-6")

		# Initiales Laden
		_refresh_dashboard(
			user_id,
			start_date_picker,
			end_date_picker,
			balance_container,
			income_expense_container,
			chart_container,
		)


def _refresh_dashboard(
	user_id: int,
	start_date_picker,
	end_date_picker,
	balance_container=None,
	income_expense_container=None,
	chart_container=None,
) -> None:
	"""
	Lädt Dashboard-Daten vom Service und aktualisiert die Anzeige.
	Zeigt Bilanz, Summen und Diagramm.
	"""
	from nicegui import ui

	# Import here to avoid circular imports
	from src.ui.controllers.dashboard_controller import dashboard_controller

	start_date = date.fromisoformat(start_date_picker.value)
	end_date = date.fromisoformat(end_date_picker.value)

	try:
		# Dashboard-Daten laden
		summary = dashboard_controller.get_dashboard(user_id, start_date, end_date)

		if balance_container is None or income_expense_container is None or chart_container is None:
			return

		# Container leeren
		balance_container.clear()
		income_expense_container.clear()
		chart_container.clear()

		with balance_container:
			# === GESAMTVERMÖGEN ===
			with ui.card().classes("w-full"):
				ui.label("Gesamtvermögen").classes("text-subtitle2 font-semibold")
				ui.label(f"CHF {summary.total_balance:,.2f}").classes("text-h4 text-blue-600 font-bold")

		with income_expense_container:
			# === EINNAHMEN & AUSGABEN ===
			with ui.card().classes("flex-1"):
				ui.label("Einnahmen").classes("text-subtitle2 font-semibold")
				ui.label(f"CHF {summary.total_income:,.2f}").classes("text-h5 text-green-600 font-bold")

			with ui.card().classes("flex-1"):
				ui.label("Ausgaben").classes("text-subtitle2 font-semibold")
				ui.label(f"CHF {summary.total_expenses:,.2f}").classes("text-h5 text-red-600 font-bold")

		with chart_container:
			# === DIAGRAMM ===
			if summary.chart_data:
				ui.label("Einnahmen & Ausgaben pro Monat").classes("text-subtitle2 font-semibold mt-6")

				# EChart für Balkendiagramm
				chart_option = {
					"xAxis": {
						"type": "category",
						"data": [d.label for d in summary.chart_data],
					},
					"yAxis": {
						"type": "value",
					},
					"series": [
						{
							"name": "Einnahmen",
							"data": [round(d.income, 2) for d in summary.chart_data],
							"type": "bar",
							"itemStyle": {"color": "#10b981"},
						},
						{
							"name": "Ausgaben",
							"data": [round(d.expenses, 2) for d in summary.chart_data],
							"type": "bar",
							"itemStyle": {"color": "#ef4444"},
						},
					],
					"tooltip": {
						"trigger": "axis",
						"valueFormatter": "function (value) { return Number(value).toFixed(2); }",
					},
				}

				ui.echart(options=chart_option).classes("w-full h-96")
			else:
				ui.label("Keine Daten für den gewählten Zeitraum.").classes("text-gray-500 italic")

	except Exception as error:
		# Fehlerbehandlung
		ui.notify(f"Fehler beim Laden des Dashboards: {str(error)}", type="negative")


def _build_sidebar() -> None:
	"""
	Baut die linke Sidebar mit Navigation zu allen Views.
	"""
	from nicegui import ui
	from src.ui.controllers.account_controller import account_controller
	ui.label("BetterBank").classes("text-h6 font-bold p-4")
	
	# Benutzername laden und anzeigen
	user_id = app_state.get("user_id")
	if user_id:
		user_display_name = account_controller.get_current_user_display_name(user_id)
		if user_display_name:
			ui.label(user_display_name).classes("text-sm text-gray-500 px-4 pb-2")
	
	ui.separator()

	with ui.column().classes("gap-2 p-4"):
		ui.button("📊 Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💳 Transaktionen", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💰 Budget", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🏦 Konten", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🎫 Karten", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated").classes("w-full justify-start")


def _logout() -> None:
	"""
	Meldet den User ab und navigiert zum Login.
	"""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")
