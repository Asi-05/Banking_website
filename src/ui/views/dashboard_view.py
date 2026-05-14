"""src.ui.views.dashboard_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

=== WAS ZEIGT DAS DASHBOARD? ===
    1. ZEILE 1 – 3 Summary-Cards:
       - Gesamtsaldo (Summe aller Kontostaende)
       - Einnahmen im laufenden Monat
       - Ausgaben im laufenden Monat

    2. ZEILE 2 – Kontenübersicht + Histogramm:
       - Linke Card: Liste aller aktiven Konten mit IBAN und Saldo
       - Rechte Card: Balkendiagramm Einnahmen vs. Ausgaben (aktueller Monat)

    3. ZEILE 3 – Letzte Transaktionen:
       - Letzte Transaktionen des laufenden Monats

=== WAS DIESE VIEW NICHT TUT ===
Die View enthaelt KEINE Fachlogik. Sie ruft `DashboardController` auf und
gibt die Daten 1:1 an NiceGUI-Elemente weiter.

=== AUFRUF-KETTE BEIM LADEN ===
    Route "/dashboard" in __main__.py → show()
    → Login-Guard (app_state pruefen)
    → _refresh_dashboard(user_id, main_container)
    → dashboard_controller.get_dashboard_view_data(user_id)
    → DashboardService.dashboard(user_id, start_date, end_date)
    → AccountRepository.list_by_user(user_id)           [Kontostaende]
    → TransactionRepository.filter_transactions(...)    [Transaktionen]
    → DashboardSummary zurueck an View
    → View baut NiceGUI-Elemente auf

=== RUECKGABE-KETTE ===
    DashboardService → DashboardSummary(total_balance, total_income, ...)
    DashboardController → dict{summary, month_name, active_accounts, recent_transactions}
    _refresh_dashboard → baut ui.card / ui.echart neu auf

=== SIDEBAR / HEADER ===
    _build_sidebar()          → linke Navigation (links zu allen Views)
    _open_settings_dialog()   → Dialog mit Telefon/Adresse des Users
    _logout()                 → setzt app_state zurueck, navigiert zu "/"

=== LOGIN-GUARD ===
    if app_state.get("current_user") is None:
        ui.navigate.to("/")    # kein User eingeloggt → zurueck zum Login
        return

=== ARCHITEKTUR-KETTE ===
    Route "/dashboard" → show()
    → _refresh_dashboard() → dashboard_controller → DashboardService → Repositories → DB

Route: `/dashboard`
"""

from src.ui.controllers.auth_controller import auth_controller
from src.ui.app_state import app_state
from src.utils.formatters import format_chf


def _refresh_dashboard(user_id: int, main_container=None) -> None:
	from nicegui import ui
	from src.ui.controllers.dashboard_controller import dashboard_controller

	try:
		view_data = dashboard_controller.get_dashboard_view_data(user_id)
		if isinstance(view_data, str):
			ui.notify(f"Fehler: {view_data}", type="negative")
			return
		if main_container is None:
			return

		summary = view_data["summary"]
		month_name = view_data["month_name"]
		active_accounts = view_data["active_accounts"]
		recent_transactions = view_data["recent_transactions"]

		main_container.clear()

		with main_container:

			# ===== ZEILE 1: 3 SUMMARY CARDS =====
			with ui.row().classes("w-full gap-4"):

				with ui.card().classes("flex-1"):
					with ui.row().classes("w-full items-center justify-between"):
						ui.label("Gesamtsaldo").classes("text-subtitle2 text-gray-500")
						ui.icon("account_balance_wallet").classes("text-blue-500 text-2xl")
					ui.label(f"CHF {format_chf(summary.total_balance)}").classes("text-h4 font-bold")
					ui.label("Alle Konten").classes("text-sm text-gray-400")

				with ui.card().classes("flex-1"):
					with ui.row().classes("w-full items-center justify-between"):
						ui.label(f"Einnahmen ({month_name})").classes("text-subtitle2 text-gray-500")
						ui.icon("trending_up").classes("text-green-500 text-2xl")
					ui.label(f"CHF {format_chf(summary.total_income)}").classes("text-h4 font-bold text-green-600")
					ui.label("Laufender Monat").classes("text-sm text-gray-400")

				with ui.card().classes("flex-1"):
					with ui.row().classes("w-full items-center justify-between"):
						ui.label(f"Ausgaben ({month_name})").classes("text-subtitle2 text-gray-500")
						ui.icon("trending_down").classes("text-red-500 text-2xl")
					ui.label(f"CHF {format_chf(summary.total_expenses)}").classes("text-h4 font-bold text-red-600")
					ui.label("Laufender Monat").classes("text-sm text-gray-400")

				# ===== ZEILE 2: KONTENÜBERSICHT + HISTOGRAMM =====
			with ui.row().classes("w-full gap-4 items-stretch"):
				# Kontenübersicht (links)
				with ui.card().classes("flex-1"):
					ui.label("Kontenübersicht").classes("text-subtitle1 font-semibold mb-3")
					for account in active_accounts:
						with ui.row().classes("w-full items-center justify-between py-3") \
								.style("border-left: 3px solid #3b82f6; padding-left: 12px; margin-bottom: 8px;"):
							with ui.column().classes("gap-0"):
								ui.label(account["label"]).classes("font-semibold")
								ui.label(account["iban"]).classes("text-sm text-gray-500")
							ui.label(f"CHF {format_chf(account['balance'])}").classes("font-bold")

				# Ausgaben / Einnahmen (HISTOGRAMM)
				with ui.card().classes("flex-1"):
					ui.label(f"Einnahmen & Ausgaben ({month_name})").classes("text-subtitle1 font-semibold mb-3")
					ui.echart(options={
						"tooltip": {
							"trigger": "axis",
							"valueFormatter": "function (value) { return 'CHF ' + Number(value).toFixed(2); }"
						},
						"xAxis": {
							"type": "category",
							"data": ["Einnahmen", "Ausgaben"],
						},
						"yAxis": {"type": "value"},
						"series": [{
							"type": "bar",
							"data": [
								{"value": round(summary.total_income, 2), "itemStyle": {"color": "#10b981"}},
								{"value": round(summary.total_expenses, 2), "itemStyle": {"color": "#ef4444"}},
							],
						}],
					}).classes("w-full h-64")

			# ===== ZEILE 3: LETZTE TRANSAKTIONEN =====
			with ui.card().classes("w-full"):
				ui.label("Letzte Transaktionen").classes("text-subtitle1 font-semibold mb-3")
				if recent_transactions:
					for t in recent_transactions:
						with ui.row().classes("w-full items-center justify-between py-3 border-b last:border-0"):
							with ui.column().classes("gap-0"):
								ui.label(t["note"]).classes("font-medium")
								ui.label(t["date"]).classes("text-sm text-gray-500")
							with ui.column().classes("items-end gap-0"):
								ui.label(t["amount_str"]).classes(t["amount_class"])
								ui.label(t["category_name"]).classes("text-xs text-gray-400")
				else:
					ui.label("Keine Transaktionen in diesem Monat.").classes("text-gray-500 italic")

	except Exception as error:
		ui.notify(f"Fehler beim Laden des Dashboards: {str(error)}", type="negative")

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

		# Titel
		ui.label("Dashboard").classes("text-h4 font-bold")

		# Gesamtvermögen (bleibt oben)
		main_container = ui.column().classes("w-full gap-6")
		_refresh_dashboard(user_id, main_container)








def _build_sidebar() -> None:
	"""Baut die linke Sidebar (Navigation zwischen den Views).

	Die Sidebar zeigt zusaetzlich (falls verfuegbar) den Benutzernamen des aktuell
	eingeloggten Users.
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
		ui.button("Dashboard", icon="home", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated align=left").classes("w-full justify-start sidebar-active")
		ui.button("Transaktionen", icon="show_chart", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated align=left").classes("w-full justify-start")
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
