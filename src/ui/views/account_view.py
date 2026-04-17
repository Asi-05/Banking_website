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
		ui.button(icon="logout", on_click=lambda: _logout()).props("flat")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		ui.label("Konten").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_overview = ui.tab("Konten-Übersicht")
			tab_open = ui.tab("Konto eröffnen")
			tab_transfer = ui.tab("Umbuchung")

		with ui.tab_panels(tabs):

			# ===== TAB 1: KONTEN-ÜBERSICHT =====
			with ui.tab_panel(tab_overview):
				_build_account_list(user_id)

			# ===== TAB 2: KONTO ERÖFFNEN =====
			with ui.tab_panel(tab_open):
				_build_open_account_form(user_id)

			# ===== TAB 3: UMBUCHUNG =====
			with ui.tab_panel(tab_transfer):
				_build_transfer_form(user_id)


def _build_account_list(user_id: int) -> None:
	"""
	Zeigt Übersicht aller Konten des Users.
	Pro Zeile: IBAN, Typ, Saldo, Status + Schliessen-Button (FR-ACC-02: nur bei Saldo 0).
	"""
	from nicegui import ui

	with ui.card().classes("w-full"):

		# Konten laden
		result = account_controller.list_accounts(user_id)

		if isinstance(result, str):
			ui.notify(result, type="negative")
			return

		accounts_table = ui.table(columns=[
			{"name": "iban", "label": "IBAN", "field": "iban", "align": "left"},
			{"name": "account_type", "label": "Typ", "field": "account_type", "align": "left"},
			{"name": "balance", "label": "Saldo (€)", "field": "balance", "align": "right"},
			{"name": "status", "label": "Status", "field": "status", "align": "left"},
			{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
		], rows=[]).props("dense")
		accounts_table.classes("w-full")

		# Button-Slot: Schliessen nur aktiv wenn status=aktiv (Saldo-Prüfung im Service)
		accounts_table.add_slot("body-cell-actions", """
			<q-td :props="props">
				<q-btn
					v-if="props.row.status === 'aktiv'"
					label="Schliessen"
					color="negative"
					size="sm"
					flat
					@click="$parent.$emit('close_account', props.row)"
				/>
				<span v-else class="text-grey-6">Geschlossen</span>
			</q-td>
		""")

		def handle_close(e) -> None:
			account_id = e.args.get("account_id")
			error = account_controller.close_account(account_id)
			if error:
				ui.notify(error, type="negative")
			else:
				ui.notify("Konto erfolgreich geschlossen", type="positive")
				# Tabelle neu laden
				_reload_account_rows(accounts_table, user_id)

		accounts_table.on("close_account", handle_close)

		_reload_account_rows(accounts_table, user_id)


def _reload_account_rows(accounts_table, user_id: int) -> None:
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		return
	rows = []
	for account in result:
		balance_val = account.balance if hasattr(account, "balance") else account.get("balance")
		rows.append({
			"account_id": account.account_id if hasattr(account, "account_id") else account.get("account_id"),
			"iban": account.iban if hasattr(account, "iban") else account.get("iban"),
			"account_type": account.account_type if hasattr(account, "account_type") else account.get("account_type"),
			"balance": f"{balance_val:,.2f}",
			"status": account.status if hasattr(account, "status") else account.get("status"),
		})
	accounts_table.rows = rows


def _build_open_account_form(user_id: int) -> None:
	"""
	Formular zum Eröffnen eines neuen Kontos.
	Auswahl: Privatkonto / Sparkonto.
	"""
	from nicegui import ui

	with ui.card().classes("w-full max-w-md"):

		# Kontotyp-Auswahl
		type_select = ui.select(
			options={"private": "Privatkonto", "savings": "Sparkonto"},
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


def _build_transfer_form(user_id: int) -> None:
	"""
	Formular für Umbuchung zwischen eigenen Konten.
	"""
	from nicegui import ui

	from src.ui.controllers.payment_controller import payment_controller

	# Konten laden
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		account_options = {}
	else:
		account_options = {
			(a.account_id if hasattr(a, "account_id") else a.get("account_id")): 
			(a.iban if hasattr(a, "iban") else a.get("iban"))
			for a in result
		}

	with ui.card().classes("w-full max-w-md"):

		# Von-Konto
		from_account_select = ui.select(
			options=account_options,
			label="Von-Konto",
		).props("outlined")
		from_account_select.classes("w-full mb-4")

		# Zu-Konto
		to_account_select = ui.select(
			options=account_options,
			label="Zu-Konto",
		).props("outlined")
		to_account_select.classes("w-full mb-4")

		# Betrag
		amount_input = ui.number(label="Betrag (€)", min=0.01, step=0.01).props("outlined")
		amount_input.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_transfer() -> None:
			"""Führt Umbuchung aus."""
			payload = {
				"from_account_id": from_account_select.value,
				"to_account_id": to_account_select.value,
				"amount": amount_input.value or 0,
			}

			error = payment_controller.create_transfer(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Umbuchung erfolgreich", type="positive")
				amount_input.value = 0

		ui.button("Umbuchen", on_click=handle_transfer).classes("w-full")


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
