"""
Account View - Betterbank Banking App
Implementiert US7, US11: Konten eröffnen/schließen und Umbuchungen
Route: /accounts
"""

from src.ui.controllers.account_controller import account_controller
from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt Konten-Übersicht, Kontoeroeffnung und Umbuchung.
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
	"""
	Zeigt Übersicht aller Konten des Users.
	Trennt aktive und geschlossene Konten in zwei separate Kästen.
	"""
	from nicegui import ui

	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		return

	# Konten in aktiv / geschlossen aufteilen
	active_accounts = [a for a in result if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"]
	closed_accounts = [a for a in result if (a.status if hasattr(a, "status") else a.get("status")) != "aktiv"]

	def build_rows(accounts):
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
				account_id = e.args.get("account_id")
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
	"""
	Formular zum Eröffnen eines neuen Kontos.
	Auswahl: Privatkonto / Sparkonto.
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
			"""Eröffnet ein neues Konto."""
			payload = {
				"user_id": user_id,
				"account_type": type_select.value,
			}

			error = account_controller.open_account(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Konto erfolgreich eröffnet", type="positive")
				type_select.value = None

		ui.button("Konto eröffnen", on_click=handle_open_account).classes("w-full")


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


def _logout() -> None:
	"""Meldet den User ab."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")
