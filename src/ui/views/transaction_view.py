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
		ui.label("Datum").classes("text-sm text-gray-600")
		date_picker = ui.date(value=date.today().isoformat()).props("outlined")
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

		_source_options = {
			"account": account_options,
			"card": debit_card_options,
			"creditcard": credit_card_options,
		}
		_source_labels = {
			"account": "Konto auswählen",
			"card": "Debitkarte auswählen",
			"creditcard": "Kreditkarte auswählen",
		}

		_active = {"widget": None}

		# Stabiler Container – wird bei Wechsel geleert und neu befüllt
		source_container = ui.column().classes("w-full")

		def render_source_select(value: str) -> None:
			source_container.clear()
			with source_container:
				opts = _source_options.get(value, {})
				lbl = _source_labels.get(value, "")
				if opts:
					w = ui.select(options=opts, label=lbl).props("outlined").classes("w-full mb-4")
					_active["widget"] = w
				else:
					_active["widget"] = None

		render_source_select("account")

		def on_source_change(value: str) -> None:
			render_source_select(value)

		source_radio.on_value_change(on_source_change)

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

			w = _active["widget"]
			if source_type == "account":
				payload["account_id"] = w.value if w else None
			elif source_type == "card":
				payload["card_id"] = w.value if w else None
			elif source_type == "creditcard":
				payload["creditcard_id"] = w.value if w else None

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
				if _active["widget"]:
					_active["widget"].value = None
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

		# Button-Slot für Aktionen
		transactions_table.add_slot("body-cell-actions", """
			<q-td :props="props">
				<q-btn label="Ändern" color="primary" size="sm" flat
					@click="$parent.$emit('edit_transaction', props.row)" />
				<q-btn label="Löschen" color="negative" size="sm" flat
					@click="$parent.$emit('delete_transaction', props.row)" />
			</q-td>
		""")

		# Löschen mit Bestätigung (FR-FIN-05)
		def handle_delete(e) -> None:
			row = e.args
			transaction_id = row.get("transaction_id")

			with ui.dialog() as confirm_dialog, ui.card():
				ui.label("Transaktion wirklich löschen?").classes("text-subtitle1 font-semibold")
				ui.label(f"Datum: {row.get('date')}  |  Betrag: {row.get('amount')} €").classes("text-gray-600")
				with ui.row().classes("gap-4 mt-4"):
					ui.button("Abbrechen", on_click=confirm_dialog.close).props("flat")
					def do_delete(tid=transaction_id):
						error = transaction_controller.delete_transaction(tid, confirm=True)
						confirm_dialog.close()
						if error:
							ui.notify(error, type="negative")
						else:
							ui.notify("Transaktion gelöscht", type="positive")
							_refresh_transaction_list(user_id, start_date_picker, end_date_picker, category_filter, transactions_table)
					ui.button("Löschen", on_click=do_delete).props("color=negative unelevated")
			confirm_dialog.open()

		transactions_table.on("delete_transaction", handle_delete)

		# Bearbeiten-Dialog (FR-FIN-05)
		def handle_edit(e) -> None:
			row = e.args
			transaction_id = row.get("transaction_id")

			with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
				ui.label("Transaktion bearbeiten").classes("text-subtitle1 font-semibold mb-4")

				amount_edit = ui.number(label="Betrag (€)", value=float(row.get("amount", "0").replace(",", "").replace(".", ".")), min=0.01, step=0.01).props("outlined")
				amount_edit.classes("w-full mb-4")

				note_edit = ui.textarea(label="Notiz", value=row.get("note") if row.get("note") != "-" else "").props("outlined")
				note_edit.classes("w-full mb-4")

				with ui.row().classes("gap-4"):
					ui.button("Abbrechen", on_click=edit_dialog.close).props("flat")
					def do_edit(tid=transaction_id):
						payload = {
							"amount": amount_edit.value or 0,
							"note": note_edit.value,
						}
						error = transaction_controller.edit_transaction(tid, payload)
						edit_dialog.close()
						if error:
							ui.notify(error, type="negative")
						else:
							ui.notify("Transaktion gespeichert", type="positive")
							_refresh_transaction_list(user_id, start_date_picker, end_date_picker, category_filter, transactions_table)
					ui.button("Speichern", on_click=do_edit).props("color=primary unelevated")
			edit_dialog.open()

		transactions_table.on("edit_transaction", handle_edit)

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

	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

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
