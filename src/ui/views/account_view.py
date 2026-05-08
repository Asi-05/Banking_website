"""src.ui.views.account_view

Account-View (NiceGUI) fuer Konto-Uebersicht und Kontoeroeffnung.

Diese Datei gehoert zur **UI-View-Schicht**. Sie ist zustaendig fuer die
Darstellung und fuer das Ausloesen von Aktionen ueber Controller.

Funktionen der Seite:
- Konten anzeigen (aktive vs. geschlossene Konten)
- Neues Konto eroeffnen (Privat/Spar)
- Konto schliessen (fachliche Regeln liegen im Service)

Login-Guard:
	Die Seite ist geschuetzt und nutzt `app_state`, um zu pruefen, ob ein User
	eingeloggt ist.

Wichtig:
	Alle fachlichen Regeln (z.B. "nur schliessen wenn Saldo = 0") liegen im
	`AccountService` und werden ueber den `AccountController` aufgerufen.

Route: `/accounts`
"""

from src.ui.controllers.account_controller import account_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Konten-Seite (Tabs: Uebersicht und Konto eroeffnen).

	Die Seite ist geschuetzt: Ohne Login wird zur Startseite umgeleitet.
	"""
	from nicegui import ui

	# Sicherheitspruefung: ohne Login zurueck zur Startseite.
	if app_state.get("current_user") is None:
		ui.navigate.to("/")
		return

	user_id = app_state.get("user_id")

	# ===== SIDEBAR =====
	with ui.left_drawer():
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

		ui.label("Konten").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_overview = ui.tab("Konten-Übersicht")
			tab_open = ui.tab("Konto eröffnen")

		with ui.tab_panels(tabs, value=tab_overview):

			# ===== TAB 1: KONTEN-ÜBERSICHT =====
			with ui.tab_panel(tab_overview):
				_build_account_list(user_id)

			# ===== TAB 2: KONTO ERÖFFNEN =====
			with ui.tab_panel(tab_open):
				_build_open_account_form(user_id)


def _build_account_list(user_id: int) -> None:
	"""Zeigt eine Uebersicht aller Konten des Users.

	Die Anzeige trennt aktive und geschlossene Konten in zwei Karten.

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui

	# Controller liefert entweder Liste oder Fehlertext.
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		return

	# Konten in aktiv / geschlossen aufteilen
	# Hinweis: In Tests/Fixtures kommen teils Dicts statt ORM-Objekten vor.
	# Darum wird defensiv mit `hasattr(...)`/`.get(...)` gelesen.
	active_accounts = [a for a in result if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"]
	closed_accounts = [a for a in result if (a.status if hasattr(a, "status") else a.get("status")) != "aktiv"]

	def build_rows(accounts):
		"""Konvertiert Konto-Objekte in Tabellenzeilen (Dicts).

		Hinweis:
			In Tests/Fixtures koennen Konten auch als Dicts statt als ORM-Objekte
			vorliegen. Daher wird beim Lesen der Felder robust vorgegangen.
		"""
		rows = []
		for account in accounts:
			balance_val = account.balance if hasattr(account, "balance") else account.get("balance")
			rows.append({
				"account_id": account.account_id if hasattr(account, "account_id") else account.get("account_id"),
				"iban": ((account.iban if hasattr(account, "iban") else account.get("iban")) or "").upper(),
				"account_type": account.account_type if hasattr(account, "account_type") else account.get("account_type"),
				"balance": f"{balance_val:,.2f}",
				"status": account.status if hasattr(account, "status") else account.get("status"),
			})
		return rows

	COLUMNS = [
		{"name": "iban", "label": "IBAN", "field": "iban", "align": "left"},
		{"name": "account_type", "label": "Typ", "field": "account_type", "align": "left"},
		{"name": "balance", "label": "Saldo (CHF)", "field": "balance", "align": "right"},
		{"name": "status", "label": "Status", "field": "status", "align": "left"},
		{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
	]

	# === KASTEN 1: AKTIVE KONTEN ===
	with ui.card().classes("w-full"):
		ui.label("Aktive Konten").classes("text-subtitle1 font-semibold mb-2")
		if not active_accounts:
			ui.label("Keine aktiven Konten.").classes("text-gray-500 italic")
		else:
			active_table = ui.table(columns=COLUMNS, rows=build_rows(active_accounts)).props("dense")
			active_table.classes("w-full")
			active_table.add_slot("body-cell-actions", """
				<q-td :props="props">
					<q-btn label="Schliessen" color="negative" size="sm" flat
						@click="$parent.$emit('close_account', props.row)" />
				</q-td>
			""")
			def handle_close_active(e) -> None:
				"""Schliesst ein Konto ueber den Controller.

				Args:
					e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
				"""
				account_id = e.args.get("account_id")
				# Fachliche Regeln (z.B. "nur schliessen wenn Saldo = 0") werden im Service
				# geprueft; die UI zeigt hier nur die Fehlermeldung an.
				error = account_controller.close_account(account_id)
				if error:
					ui.notify(error, type="negative")
				else:
					ui.notify("Konto erfolgreich geschlossen", type="positive")
			active_table.on("close_account", handle_close_active)

	# === KASTEN 2: GESCHLOSSENE KONTEN ===
	with ui.card().classes("w-full mt-4"):
		ui.label("Geschlossene Konten").classes("text-subtitle1 font-semibold mb-2")
		if not closed_accounts:
			ui.label("Keine geschlossenen Konten.").classes("text-gray-500 italic")
		else:
			closed_table = ui.table(columns=COLUMNS, rows=build_rows(closed_accounts)).props("dense")
			closed_table.classes("w-full")
			closed_table.add_slot("body-cell-actions", """
				<q-td :props="props">
					<span class="text-grey-6">Geschlossen</span>
				</q-td>
			""")


def _build_open_account_form(user_id: int) -> None:
	"""Rendert das Formular zum Eroeffnen eines neuen Kontos.

	Der Nutzer waehlt den Kontotyp (Privat/Spar). Die fachliche Validierung (z.B.
gueltige Typen) passiert im Service.

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui

	with ui.card().classes("w-full max-w-md"):

		# Kontotyp-Auswahl
		type_select = ui.select(
			options={"privat": "Privatkonto", "spar": "Sparkonto"},
			label="Kontotyp",
		).props("outlined")
		type_select.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_open_account() -> None:
			"""Eroeffnet ein neues Konto ueber den Controller."""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
			payload = {
				"user_id": user_id,
				"account_type": type_select.value,
			}

			# Validierung des Kontotyps passiert im Service; die UI uebergibt nur die Auswahl.

			error = account_controller.open_account(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Konto erfolgreich eröffnet", type="positive")
				type_select.value = None

		ui.button("Konto eröffnen", on_click=handle_open_account).classes("w-full")


def _build_sidebar() -> None:
	"""Baut die Sidebar-Navigation (Links zu den Views)."""
	from nicegui import ui
	user_id = app_state.get("user_id")
	if user_id:
		from src.ui.controllers.auth_controller import auth_controller
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
	"""Meldet den User ab (setzt `app_state` zurueck) und navigiert zum Login."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")


def _open_settings_dialog(user_id: int) -> None:
	"""Oeffnet den Kontoeinstellungen-Dialog (aktuell nur Anzeige).

	Die Daten kommen aus dem `UserController`. In dieser View werden Telefonnummer
	und Adresse nur angezeigt; Aenderungen werden als "beantragt" simuliert.

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
