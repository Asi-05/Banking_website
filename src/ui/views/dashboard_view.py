"""src.ui.views.dashboard_view

Dashboard-View (NiceGUI) fuer die Uebersichtsseite der Banking-App.

Diese Datei gehoert zur **UI-View-Schicht**. Eine View ist in diesem Projekt
zustaendig fuer:

- Layout und UI-Elemente (Buttons, Cards, Diagramme)
- Ausloesen von Aktionen (z.B. "Filter anwenden")
- Anzeigen von Fehlermeldungen/Notifications

Wichtig: Die View enthaelt **keine** Fachlogik. Stattdessen fragt sie Daten
ueber Controller/Services ab.

Was das Dashboard zeigt:
- Gesamtvermoegen (Summe aller Kontostaende)
- Einnahmen und Ausgaben im ausgewaehlten Zeitraum
- Monatsdiagramm (Einnahmen/Ausgaben pro Monat)

Zusammenarbeit:
- `DashboardController` kapselt den Zugriff auf `DashboardService`.
- Der Login-Status wird ueber `app_state` geprueft.

Route: `/dashboard`
"""

from datetime import date

from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Dashboard-Seite.

	Die Seite ist geschuetzt: Falls kein User eingeloggt ist, wird sofort zur
	Login-Seite umgeleitet.

	Hinweis:
		Diese Funktion wird beim Aufruf der Route `/dashboard` ausgefuehrt und baut
		die komplette UI-Struktur (Sidebar, Header, Inhalt) auf.
	"""
	from nicegui import ui

	# Sicherheitspruefung: Views duerfen nur fuer eingeloggte User sichtbar sein.
	if app_state.get("current_user") is None:
		ui.navigate.to("/")
		return

	user_id = app_state.get("user_id")

	# ===== SIDEBAR & LAYOUT =====
	with ui.left_drawer() as left_drawer:
		left_drawer.set_value(True)
		_build_sidebar()

	# ===== HEADER: BRAND LINKS + USER ACTIONS =====
	with ui.header():
		with ui.row().classes("w-full items-center justify-between"):
			ui.label("BetterBank").classes("text-h6 font-bold text-white")
			with ui.row().classes("items-center gap-2"):
				with ui.button(icon="settings").props("flat round").classes("text-white"):
					with ui.menu():
						ui.menu_item("Kontoeinstellungen", on_click=lambda: _open_settings_dialog(user_id))
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
				# NiceGUI-Datepicker liefert einen ISO-String (YYYY-MM-DD).
				start_date_picker = ui.date(
					value=date(date.today().year, date.today().month, 1).isoformat()
				).props("first-day-of-week=1")

			with ui.card().classes(""):
				ui.label("Bis").classes("text-sm text-gray-500 mb-1")
				# Default: Ende = heute.
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
			# Der Lambda-Handler greift auf Variablen zu, die weiter unten initialisiert
			# werden. Das ist in Python okay, weil der Klick erst nach dem Rendern
			# passiert ("late binding" bei Closures).

		# Zeile 2: Einnahmen und Ausgaben
		income_expense_container = ui.row().classes("w-full gap-4")

		# Zeile 3: Diagramm volle Breite
		chart_container = ui.column().classes("w-full gap-6")

		# Initiales Laden
		# (Beim ersten Render sollen sofort Daten angezeigt werden.)
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
	"""Laedt Dashboard-Daten neu und aktualisiert die UI-Container.

	Die Datumswerte kommen aus NiceGUI-Datepickern als ISO-Strings
	(`YYYY-MM-DD`). Fuer die Fachlogik werden sie zu `datetime.date` geparst.

	Wenn der Controller einen Fehler als String zurueckgibt, wird eine negative
	Notification angezeigt und der UI-Update wird abgebrochen.

	Args:
		user_id: Eingeloggter User.
		start_date_picker: UI-Element mit ISO-Datum im Feld `.value`.
		end_date_picker: UI-Element mit ISO-Datum im Feld `.value`.
		balance_container: Container fuer die Bilanzanzeige.
		income_expense_container: Container fuer Einnahmen/Ausgaben.
		chart_container: Container fuer Diagramm oder "keine Daten"-Hinweis.

	Raises:
		ValueError: Wenn ein Datepicker keinen gueltigen ISO-Datumsstring enthaelt.
	"""
	from nicegui import ui
	from src.ui.controllers.dashboard_controller import dashboard_controller

	# Datepicker liefern Strings; fuer den Controller brauchen wir echte `date`-Objekte.
	start_date = date.fromisoformat(start_date_picker.value)
	end_date = date.fromisoformat(end_date_picker.value)

	try:
		# Controller kapselt Fehler und liefert entweder Summary oder Fehlertext.
		summary = dashboard_controller.get_dashboard(user_id, start_date, end_date)
		if isinstance(summary, str):
			ui.notify(f"Fehler: {summary}", type="negative")
			return

		if balance_container is None or income_expense_container is None or chart_container is None:
			return

		# Container leeren, damit wir sauber "neu rendern" koennen.
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

				# ECharts-Options-Objekt: wird von NiceGUI an den Browser uebergeben.
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
					# Tooltip: zeigt Werte formatiert.
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
	"""Baut die linke Sidebar (Navigation zwischen den Views).

	Die Sidebar zeigt zusaetzlich (falls verfuegbar) den Benutzernamen des aktuell
	eingeloggten Users.
	"""
	from nicegui import ui
	user_id = app_state.get("user_id")
	if user_id:
		from src.ui.controllers.auth_controller import auth_controller
		# Username wird ueber den Controller geladen (Service-Logik bleibt ausserhalb der View).
		username = auth_controller.get_username(user_id)
		if username:
			ui.label(username).classes("text-sm text-gray-500 px-4 pb-2")

	ui.separator()

	with ui.column().classes("gap-2 px-4 pb-4 pt-0"):
		ui.button("📊 Dashboard", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💳 Transaktionen", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated").classes("w-full justify-start")
		ui.button("💰 Budget", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🏦 Konten", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated").classes("w-full justify-start")
		ui.button("🎫 Karten", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated").classes("w-full justify-start")


def _logout() -> None:
	"""Meldet den User ab und navigiert zum Login.

	Die Funktion setzt den Login-Zustand im globalen `app_state` zurueck und
	zeigt eine positive Bestaetigung.
	"""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")


def _open_settings_dialog(user_id: int) -> None:
	"""Oeffnet einen Dialog mit Kontoeinstellungen (Profil-Infos).

	Der Dialog dient in der aktuellen Version nur zur Anzeige von Daten und zum
	"Beantragen" von Aenderungen (hier als Notification simuliert). Die eigentliche
	Aenderungslogik (z.B. Formulare, Persistenz) liegt **nicht** in dieser View.

	Args:
		user_id: ID des eingeloggten Users, fuer den das Profil geladen wird.
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
