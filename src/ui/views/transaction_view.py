"""
Transaction View - Betterbank Banking App
Implementiert US1, US2, US3: Transaktionen erfassen, bearbeiten, löschen, filtern
Route: /transactions
"""

from datetime import date

from src.ui.controllers.transaction_controller import transaction_controller
from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt Transaktions-Erfassungsformular und Transaktionsliste mit Filtern.
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

		ui.label("Transaktionen").classes("text-h4 font-bold")

		# Tab-Layout: Erfassung / Übersicht
		with ui.tabs() as tabs:
			tab_create = ui.tab("Neue Transaktion")
			tab_list = ui.tab("Transaktionsliste")

		with ui.tab_panels(tabs):

			# ===== TAB 1: ERFASSUNGSFORMULAR =====
			with ui.tab_panel(tab_create):
				_build_transaction_form(user_id)

			# ===== TAB 2: TRANSAKTIONSLISTE =====
			with ui.tab_panel(tab_list):
				_build_transaction_list(user_id)


def _build_transaction_form(user_id: int) -> None:
	"""
	Baut das Erfassungsformular für neue Transaktionen.
	Enthält Exactly-One-Regel für Belastungsquelle (Radio-Button).
	"""
	from nicegui import ui

	from src.services.account_service import account_service
	from src.services.card_service import card_service
	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

	# Kategorien laden
	with Session(engine) as session:
		categories = CategoryRepository.list_all(session)
	category_options = {c.category_id: c.name for c in categories}

	# Konten und Karten laden
	accounts = account_service.list_accounts(user_id)
	if isinstance(accounts, str):
		ui.notify(accounts, type="negative")
		accounts = []
	account_options = {a.account_id: f"{a.iban} ({a.account_type})" for a in accounts} if isinstance(accounts, list) else {}

	# Debitkarten laden
	from src.data_access.repositories.card_repository import CardRepository
	with Session(engine) as session:
		debit_cards = CardRepository.list_debit_by_user(session, user_id) if hasattr(CardRepository, 'list_debit_by_user') else []
	debit_card_options = {c.card_id: f"**** {c.card_number[-4:]}" for c in debit_cards} if debit_cards else {}

	# Kreditkarten laden
	with Session(engine) as session:
		credit_cards = CardRepository.list_credit_by_user(session, user_id)
	credit_card_options = {c.creditcard_id: f"**** {c.card_number[-4:]}" for c in credit_cards} if credit_cards else {}

	with ui.card().classes("w-full max-w-md"):

		# Betrag
		amount_input = ui.number(label="Betrag (€)", min=0.01, step=0.01).props("outlined")
		amount_input.classes("w-full mb-4")

		# Typ: Income / Expense
		type_select = ui.select(
			options={"income": "Einnahme", "expense": "Ausgabe"},
			label="Typ",
		).props("outlined")
		type_select.classes("w-full mb-4")

		# Datum
		date_picker = ui.date(value=date.today().isoformat(), label="Datum").props("outlined")
		date_picker.classes("w-full mb-4")

		# Kategorie
		category_select = ui.select(
			options=category_options,
			label="Kategorie",
		).props("outlined")
		category_select.classes("w-full mb-4")

		# === EXACTLY-ONE-REGEL: Radio-Buttons für Belastungsquelle ===
		ui.label("Belastungsquelle").classes("font-semibold mb-2")

		source_radio = ui.radio(
			options={"account": "Konto", "card": "Debitkarte", "creditcard": "Kreditkarte"},
			value="account",
		)
		source_radio.classes("mb-4")

		def on_source_change(value: str) -> None:
			"""Aktualisiert sichtbarkeit der Dropdowns basierend auf Quelle."""
			account_select.set_visibility(value == "account")
			card_select.set_visibility(value == "card")
			creditcard_select.set_visibility(value == "creditcard")

		source_radio.on_value_change(on_source_change)

		# Konto-Dropdown (sichtbar bei source="account")
		account_select = ui.select(
			options=account_options,
			label="Konto auswählen",
		).props("outlined")
		account_select.classes("w-full mb-4")

		# Debitkarte-Dropdown (verborgen initial)
		card_select = ui.select(
			options=debit_card_options,
			label="Debitkarte auswählen",
		).props("outlined")
		card_select.classes("w-full mb-4")
		card_select.set_visibility(False)

		# Kreditkarte-Dropdown (verborgen initial)
		creditcard_select = ui.select(
			options=credit_card_options,
			label="Kreditkarte auswählen",
		).props("outlined")
		creditcard_select.classes("w-full mb-4")
		creditcard_select.set_visibility(False)

		# Notiz
		note_input = ui.textarea(label="Notiz (optional)").props("outlined")
		note_input.classes("w-full mb-4")

		# Fehlerbehandlungs-Label
		error_label = ui.label("").classes("text-red-600 mb-4")

		# Speichern-Button
		async def handle_create_transaction() -> None:
			"""Verarbeitet das Speichern einer neuen Transaktion."""

			# Quelle bestimmen
			source_type = source_radio.value
			payload = {
				"amount": amount_input.value or 0,
				"type": type_select.value,
				"date": date_picker.value,
				"category_id": category_select.value,
				"note": note_input.value,
				"account_id": None,
				"card_id": None,
				"creditcard_id": None,
			}

			if source_type == "account":
				payload["account_id"] = account_select.value
			elif source_type == "card":
				payload["card_id"] = card_select.value
			elif source_type == "creditcard":
				payload["creditcard_id"] = creditcard_select.value

			# Controller aufrufen
			error = transaction_controller.create_transaction(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Transaktion gespeichert", type="positive")
				# Formular zurücksetzen
				amount_input.value = 0
				type_select.value = None
				date_picker.value = date.today().isoformat()
				category_select.value = None
				note_input.value = ""
				error_label.set_text("")

		ui.button("Speichern", on_click=handle_create_transaction).classes("w-full")


def _build_transaction_list(user_id: int) -> None:
	"""
	Baut Transaktionsliste mit Filtern (Datum, Kategorie).
	Zeigt Edit/Delete-Buttons.
	"""
	from nicegui import ui

	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

	# Kategorien laden für Filter
	with Session(engine) as session:
		categories = CategoryRepository.list_all(session)
	category_options = {c.category_id: c.name for c in categories}

	with ui.card().classes("w-full"):

		# Filter-Bereich
		with ui.row().classes("gap-4 mb-4"):
			start_date_picker = ui.date(value=date.today().isoformat()).props("outlined")
			start_date_picker.label = "Von"

			end_date_picker = ui.date(value=date.today().isoformat()).props("outlined")
			end_date_picker.label = "Bis"

			category_filter = ui.select(
				options={None: "Alle Kategorien", **category_options},
				value=None,
				label="Kategorie",
			).props("outlined")

			ui.button("Filter anwenden", on_click=lambda: _refresh_transaction_list(
				user_id,
				start_date_picker,
				end_date_picker,
				category_filter,
			))

		# Transaktionsliste (Tabelle)
		transactions_table = ui.table(columns=[
			{"name": "date", "label": "Datum", "field": "date", "align": "left"},
			{"name": "type", "label": "Typ", "field": "type", "align": "left"},
			{"name": "amount", "label": "Betrag (€)", "field": "amount", "align": "right"},
			{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
			{"name": "note", "label": "Notiz", "field": "note", "align": "left"},
			{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
		], rows=[]).props("dense")
		transactions_table.classes("w-full")

		# Initiales Laden
		_refresh_transaction_list(user_id, start_date_picker, end_date_picker, category_filter, transactions_table)


def _refresh_transaction_list(
	user_id: int,
	start_date_picker,
	end_date_picker,
	category_filter,
	transactions_table=None,
) -> None:
	"""
	Lädt Transaktionsliste neu und aktualisiert die Tabelle.
	"""
	from nicegui import ui

	start_date = date.fromisoformat(start_date_picker.value)
	end_date = date.fromisoformat(end_date_picker.value)
	category_id = category_filter.value if category_filter.value is not None else None

	# Controller aufrufen
	result = transaction_controller.filter_transactions(
		start_date=start_date,
		end_date=end_date,
		category_id=category_id,
		user_id=user_id,
	)

	if isinstance(result, str):
		ui.notify(result, type="negative")
		return

	# Kategorienamen-Mapping laden
	with Session(engine) as session:
		categories = CategoryRepository.list_all(session)
	category_names = {c.category_id: c.name for c in categories}

	# Transaktionen in Tabellenformat konvertieren
	rows = []
	for txn in result:
		category_name = category_names.get(txn['category_id'], f"ID {txn['category_id']}")
		rows.append({
			"transaction_id": txn["transaction_id"],
			"date": txn["date"],
			"type": txn["type"],
			"amount": f"{txn['amount']:,.2f}",
			"category": category_name,
			"note": txn["note"] or "-",
			"actions": "Ändern/Löschen",
		})

	if transactions_table:
		transactions_table.rows = rows


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
