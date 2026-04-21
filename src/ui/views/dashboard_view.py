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
		with ui.row().classes("w-full justify-end"):
			ui.button("Logout", icon="logout", on_click=lambda: _logout()) \
				.props("unelevated no-caps") \
				.classes("bg-white font-semibold px-4 py-2 rounded") \
				.style("color: #1d4ed8 !important;")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		# Titel
		ui.label("Dashboard").classes("text-h4 font-bold")

		# Bereich für Kennzahlen (oberhalb des Kalenders)
		summary_container = ui.column().classes("w-full gap-6")

		# Datumsbereich-Filter (zwischen Kennzahlen und Histogramm)
		with ui.card().classes("w-full"):
			with ui.row().classes("gap-4 items-start"):
				today = date.today()
				first_day_of_month = date(today.year, today.month, 1)
				default_end = today

				start_date_picker = ui.date(value=first_day_of_month.isoformat()).props("outlined")
				start_date_picker.label = "Von"

				end_date_picker = ui.date(value=default_end.isoformat()).props("outlined")
				end_date_picker.label = "Bis"

				ui.button("Filter anwenden", on_click=lambda: _refresh_dashboard(
					user_id,
					start_date_picker,
					end_date_picker,
					summary_container,
					chart_container,
				)).props("unelevated color=primary")

		# Bereich für Histogramm (unterhalb des Kalenders)
		chart_container = ui.column().classes("w-full gap-6")

		# Initiales Laden
		_refresh_dashboard(user_id, start_date_picker, end_date_picker, summary_container, chart_container)


def _refresh_dashboard(
	user_id: int,
	start_date_picker,
	end_date_picker,
	summary_container=None,
	chart_container=None,
) -> None:
	"""
	Lädt Dashboard-Daten vom Service und aktualisiert die Anzeige.
	Zeigt Bilanz, Summen und Diagramm.
	"""
	from nicegui import ui

	# Import here to avoid circular imports
	from src.services.dashboard_service import dashboard_service

	start_date = date.fromisoformat(start_date_picker.value)
	end_date = date.fromisoformat(end_date_picker.value)

	try:
		# Dashboard-Daten laden
		summary = dashboard_service.dashboard(user_id, start_date, end_date)

		if summary_container is None or chart_container is None:
			return

		# Container leeren
		summary_container.clear()
		chart_container.clear()

		with summary_container:
			# === BILANZ-KARTEN ===
			with ui.row().classes("gap-4 w-full"):

				# Gesamtbilanz
				with ui.card().classes("flex-1"):
					ui.label("Gesamtbilanz").classes("text-subtitle2 font-semibold")
					ui.label(f"CHF {summary.total_balance:,.2f}").classes("text-h5 text-blue-600 font-bold")

				# Einnahmen
				with ui.card().classes("flex-1"):
					ui.label("Einnahmen").classes("text-subtitle2 font-semibold")
					ui.label(f"CHF {summary.total_income:,.2f}").classes("text-h5 text-green-600 font-bold")

				# Ausgaben
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
	ui.label("Betterbank").classes("text-h6 font-bold p-4")
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
