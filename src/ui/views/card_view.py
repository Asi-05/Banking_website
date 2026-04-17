"""
Card View - Betterbank Banking App
Implementiert US8, US9: Debitkarten und Kreditkarten verwalten
Route: /cards
"""

from src.ui.controllers.card_controller import card_controller
from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt Debitkarten- und Kreditkarten-Verwaltung.
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

		ui.label("Karten").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_debit = ui.tab("Debitkarten")
			tab_credit = ui.tab("Kreditkarten")

		with ui.tab_panels(tabs):

			# ===== TAB 1: DEBITKARTEN =====
			with ui.tab_panel(tab_debit):
				_build_debit_cards_section(user_id)

			# ===== TAB 2: KREDITKARTEN =====
			with ui.tab_panel(tab_credit):
				_build_credit_cards_section(user_id)


def _build_debit_cards_section(user_id: int) -> None:
	"""
	Debitkarten-Verwaltung (US8).
	Liste aller Debitkarten, Bestellen, Sperren, Ersetzen.
	"""
	from nicegui import ui

	from src.services.card_service import card_service
	from src.ui.controllers.account_controller import account_controller

	with ui.column().classes("w-full gap-6"):

		# === NEUE DEBITKARTE BESTELLEN ===
		with ui.expansion("Neue Debitkarte bestellen").classes("w-full"):

			# Konto-Auswahl (nur Privatkonten)
			result = account_controller.list_accounts(user_id)
			if isinstance(result, str):
				ui.notify(result, type="negative")
				account_options = {}
			else:
				# Nur Privatkonten filtern
				account_options = {
					(a.account_id if hasattr(a, "account_id") else a.get("account_id")): 
					(a.iban if hasattr(a, "iban") else a.get("iban"))
					for a in result
					if (a.account_type if hasattr(a, "account_type") else a.get("account_type")) == "private"
				}

			account_select = ui.select(
				options=account_options,
				label="Privatkonto auswählen",
			).props("outlined")
			account_select.classes("w-full mb-4")

			error_label = ui.label("").classes("text-red-600 mb-4")

			async def handle_order_debit_card() -> None:
				"""Bestellt eine neue Debitkarte."""
				error = card_controller.order_debit_card(account_select.value)

				if error:
					error_label.set_text(error)
					ui.notify(error, type="negative")
				else:
					ui.notify("Debitkarte erfolgreich bestellt", type="positive")
					account_select.value = None

			ui.button("Bestellen", on_click=handle_order_debit_card).classes("w-full")

		# === DEBITKARTEN-LISTE ===
		with ui.card().classes("w-full"):

			ui.label("Meine Debitkarten").classes("text-subtitle2 font-semibold")

			# Debitkarten laden
			try:
				debit_cards = card_service.list_debit_cards(user_id)

				if isinstance(debit_cards, str):
					ui.notify(debit_cards, type="negative")
					return

				# Tabelle
				debit_table = ui.table(columns=[
					{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
					{"name": "expire_date", "label": "Ablaufdatum", "field": "expire_date", "align": "left"},
					{"name": "account", "label": "Konto", "field": "account", "align": "left"},
					{"name": "status", "label": "Status", "field": "status", "align": "left"},
					{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
				], rows=[]).props("dense")
				debit_table.classes("w-full")

				# Daten mit Konto-IBAN laden
				from src.ui.controllers.account_controller import account_controller
				accounts = account_controller.list_accounts(user_id)
				account_map = {}
				if not isinstance(accounts, str):
					account_map = {
						(a.account_id if hasattr(a, "account_id") else a.get("account_id")): 
						(a.iban if hasattr(a, "iban") else a.get("iban"))
						for a in accounts
					}

				rows = []
				for card in debit_cards:
					account_iban = account_map.get(card.account_id if hasattr(card, "account_id") else card.get("account_id"), "N/A")
					rows.append({
						"card_id": card.card_id if hasattr(card, "card_id") else card.get("card_id"),
						"card_number": (card.card_number if hasattr(card, "card_number") else card.get("card_number"))[-4:],  # Letzte 4 Ziffern
						"expire_date": card.expire_date if hasattr(card, "expire_date") else card.get("expire_date"),
						"account": account_iban,
						"status": card.status if hasattr(card, "status") else card.get("status"),
						"actions": "Sperren" if (card.status if hasattr(card, "status") else card.get("status")) == "aktiv" else "Ersetzen",
					})

				debit_table.rows = rows

			except Exception as e:
				ui.notify(f"Fehler beim Laden der Debitkarten: {str(e)}", type="negative")
def _build_credit_cards_section(user_id: int) -> None:
	"""
	Kreditkarten-Verwaltung (US9).
	Liste aller Kreditkarten, Beantragen, Sperren, Ersetzen.
	"""
	from nicegui import ui

	from src.services.card_service import card_service

	with ui.column().classes("w-full gap-6"):

		# === NEUE KREDITKARTE BEANTRAGEN ===
		with ui.expansion("Neue Kreditkarte beantragen").classes("w-full"):

			# Gewünschtes Limit
			limit_input = ui.number(label="Gewünschtes Limit (CHF)", min=100, step=100).props("outlined")
			limit_input.classes("w-full mb-4")

			error_label = ui.label("").classes("text-red-600 mb-4")

			async def handle_create_credit_card() -> None:
				"""Beantragt eine neue Kreditkarte."""
				payload = {
					"user_id": user_id,
					"desired_limit": limit_input.value or 1000,
				}

				error = card_controller.create_credit_card(payload)

				if error:
					error_label.set_text(error)
					ui.notify(error, type="negative")
				else:
					ui.notify("Kreditkarte erfolgreich beantragt", type="positive")
					limit_input.value = 0

			ui.button("Beantragen", on_click=handle_create_credit_card).classes("w-full")

		# === KREDITKARTEN-LISTE ===
		with ui.card().classes("w-full"):

			ui.label("Meine Kreditkarten").classes("text-subtitle2 font-semibold")

			# Kreditkarten laden
			try:
				credit_cards = card_service.list_credit_cards(user_id)

				if isinstance(credit_cards, str):
					ui.notify(credit_cards, type="negative")
					return

				# Tabelle
				credit_table = ui.table(columns=[
					{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
					{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
					{"name": "balance", "label": "Genutzt (CHF)", "field": "balance", "align": "right"},
					{"name": "available", "label": "Verfügbar (CHF)", "field": "available", "align": "right"},
					{"name": "status", "label": "Status", "field": "status", "align": "left"},
					{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
				], rows=[]).props("dense")
				credit_table.classes("w-full")

				# Daten
				rows = []
				for card in credit_cards:
					limit_val = card.limit if hasattr(card, "limit") else card.get("limit")
					balance_val = card.balance if hasattr(card, "balance") else card.get("balance")
					available = limit_val - balance_val

					rows.append({
						"card_id": card.creditcard_id if hasattr(card, "creditcard_id") else card.get("creditcard_id"),
						"card_number": (card.card_number if hasattr(card, "card_number") else card.get("card_number"))[-4:],  # Letzte 4 Ziffern
						"limit": f"{limit_val:,.2f}",
						"balance": f"{balance_val:,.2f}",
						"available": f"{available:,.2f}",
						"status": card.status if hasattr(card, "status") else card.get("status"),
						"actions": "Sperren" if (card.status if hasattr(card, "status") else card.get("status")) == "aktiv" else "Ersetzen",
					})

				credit_table.rows = rows

			except Exception as e:
				ui.notify(f"Fehler beim Laden der Kreditkarten: {str(e)}", type="negative")


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
