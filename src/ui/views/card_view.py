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
					((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
					for a in result
					if (a.account_type if hasattr(a, "account_type") else a.get("account_type")) == "privat"
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

				# Button-Slot: Sperren (bei aktiv) oder Ersetzen (bei gesperrt) — FR-CARD-01/02
				debit_table.add_slot("body-cell-actions", """
					<q-td :props="props">
						<q-btn v-if="props.row.status === 'aktiv'"
							label="Sperren" color="negative" size="sm" flat
							@click="$parent.$emit('block_debit', props.row)" />
						<q-btn v-else
							label="Ersetzen" color="primary" size="sm" flat
							@click="$parent.$emit('replace_debit', props.row)" />
					</q-td>
				""")

				def handle_block_debit(e) -> None:
					card_id = e.args.get("card_id")
					error = card_controller.block_debit_card(card_id)
					if error:
						ui.notify(error, type="negative")
					else:
						ui.notify("Debitkarte gesperrt", type="positive")
						debit_table.rows = [r for r in debit_table.rows if r["card_id"] != card_id or not True]
						# Status in Tabelle aktualisieren
						for row in debit_table.rows:
							if row["card_id"] == card_id:
								row["status"] = "gesperrt"
						debit_table.update()

				def handle_replace_debit(e) -> None:
					card_id = e.args.get("card_id")
					error = card_controller.replace_debit_card(card_id)
					if error:
						ui.notify(error, type="negative")
					else:
						ui.notify("Ersatzkarte bestellt", type="positive")

				debit_table.on("block_debit", handle_block_debit)
				debit_table.on("replace_debit", handle_replace_debit)

				# Daten mit Konto-IBAN laden
				from src.ui.controllers.account_controller import account_controller
				accounts = account_controller.list_accounts(user_id)
				account_map = {}
				if not isinstance(accounts, str):
					account_map = {
						(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
						((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
						for a in accounts
					}

				rows = []
				for card in debit_cards:
					account_iban = account_map.get(card.account_id if hasattr(card, "account_id") else card.get("account_id"), "N/A")
					rows.append({
						"card_id": card.card_id if hasattr(card, "card_id") else card.get("card_id"),
						"card_number": f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}",
						"expire_date": str(card.expire_date if hasattr(card, "expire_date") else card.get("expire_date")),
						"account": account_iban,
						"status": card.status if hasattr(card, "status") else card.get("status"),
					})

				debit_table.rows = rows

			except Exception as e:
				ui.notify(f"Fehler beim Laden der Debitkarten: {str(e)}", type="negative")
def _build_credit_cards_section(user_id: int) -> None:
	"""
	Kreditkarten-Verwaltung (US9).
	Liste aller Kreditkarten, Beantragen, Sperren, Ersetzen.
	Trennt aktive Kreditkarten von Anträgen.
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
					ui.notify("Kreditkartenantrag wurde erfolgreich eingereicht", type="positive")

			ui.button("Beantragen", on_click=handle_create_credit_card).classes("w-full")

		# === KREDITKARTEN LADEN ===
		try:
			credit_cards = card_service.list_credit_cards(user_id)

			if isinstance(credit_cards, str):
				ui.notify(credit_cards, type="negative")
				return

			# Trennung: aktive Karten vs. Anträge/Pending
			active_cards = [c for c in credit_cards if (c.status if hasattr(c, "status") else c.get("status")) in ["aktiv", "gesperrt"]]
			pending_cards = [c for c in credit_cards if (c.status if hasattr(c, "status") else c.get("status")) not in ["aktiv", "gesperrt"]]

			# === AKTIVE KREDITKARTEN-LISTE ===
			with ui.card().classes("w-full"):

				ui.label("Meine aktiven Kreditkarten").classes("text-subtitle2 font-semibold")

				if not active_cards:
					ui.label("Keine aktiven Kreditkarten.").classes("text-gray-500 italic")
				else:
					# Tabelle für aktive Karten
					credit_table = ui.table(columns=[
						{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
						{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
						{"name": "balance", "label": "Genutzt (CHF)", "field": "balance", "align": "right"},
						{"name": "available", "label": "Verfügbar (CHF)", "field": "available", "align": "right"},
						{"name": "status", "label": "Status", "field": "status", "align": "left"},
						{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
					], rows=[]).props("dense")
					credit_table.classes("w-full")

					# Button-Slot: Sperren (bei aktiv) oder Ersetzen (bei gesperrt) — FR-CC-03
					credit_table.add_slot("body-cell-actions", """
						<q-td :props="props">
							<q-btn v-if="props.row.status === 'aktiv'"
								label="Sperren" color="negative" size="sm" flat
								@click="$parent.$emit('block_credit', props.row)" />
							<q-btn v-else
								label="Ersetzen" color="primary" size="sm" flat
								@click="$parent.$emit('replace_credit', props.row)" />
						</q-td>
					""")

					def handle_block_credit(e) -> None:
						creditcard_id = e.args.get("card_id")
						error = card_controller.block_credit_card(creditcard_id)
						if error:
							ui.notify(error, type="negative")
						else:
							ui.notify("Kreditkarte gesperrt", type="positive")
							for row in credit_table.rows:
								if row["card_id"] == creditcard_id:
									row["status"] = "gesperrt"
							credit_table.update()

					def handle_replace_credit(e) -> None:
						creditcard_id = e.args.get("card_id")
						error = card_controller.replace_credit_card(creditcard_id)
						if error:
							ui.notify(error, type="negative")
						else:
							ui.notify("Ersatzkreditkarte bestellt", type="positive")

					credit_table.on("block_credit", handle_block_credit)
					credit_table.on("replace_credit", handle_replace_credit)

					# Daten: aktive Karten
					rows = []
					for card in active_cards:
						limit_val = card.limit if hasattr(card, "limit") else card.get("limit")
						balance_val = card.balance if hasattr(card, "balance") else card.get("balance")
						available = limit_val - balance_val

						rows.append({
							"card_id": card.creditcard_id if hasattr(card, "creditcard_id") else card.get("creditcard_id"),
							"card_number": f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}",
							"limit": f"{limit_val:,.2f}",
							"balance": f"{balance_val:,.2f}",
							"available": f"{available:,.2f}",
							"status": card.status if hasattr(card, "status") else card.get("status"),
						})

					credit_table.rows = rows

			# === KREDITKARTENANTRÄGE-LISTE ===
			with ui.card().classes("w-full"):

				ui.label("Meine Kreditkartenanträge").classes("text-subtitle2 font-semibold")

				if not pending_cards:
					ui.label("Keine offenen Anträge.").classes("text-gray-500 italic")
				else:
					# Tabelle für beantragte Karten
					pending_table = ui.table(columns=[
						{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
						{"name": "limit", "label": "Gewünschtes Limit (CHF)", "field": "limit", "align": "right"},
						{"name": "status", "label": "Status", "field": "status", "align": "left"},
					], rows=[]).props("dense")
					pending_table.classes("w-full")

					# Daten: beantragte Karten
					pending_rows = []
					for card in pending_cards:
						limit_val = card.limit if hasattr(card, "limit") else card.get("limit")

						pending_rows.append({
							"card_id": card.creditcard_id if hasattr(card, "creditcard_id") else card.get("creditcard_id"),
							"card_number": f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}",
							"limit": f"{limit_val:,.2f}",
							"status": card.status if hasattr(card, "status") else card.get("status"),
						})

					pending_table.rows = pending_rows

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


def _logout() -> None:
	"""Meldet den User ab."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")
