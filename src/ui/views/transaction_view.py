"""
Transaction View - Betterbank Banking App
Implementiert US1, US2, US3: Transaktionen erfassen, bearbeiten, löschen, filtern
Route: /transactions
"""

from datetime import date, timedelta

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

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_domestic = ui.tab("Neue Inlandszahlung")
			tab_list = ui.tab("Bewegungen")
			tab_recurring = ui.tab("Daueraufträge")
			tab_transfer = ui.tab("Übertrag")
			tab_statement = ui.tab("Kontoauszug")

		with ui.tab_panels(tabs):

			# ===== TAB 1: NEUE INLANDSZAHLUNG =====
			with ui.tab_panel(tab_domestic):
				_build_domestic_payment_form(user_id)

			# ===== TAB 2: BEWEGUNGEN =====
			with ui.tab_panel(tab_list):
				_build_transaction_list(user_id)

			# ===== TAB 3: DAUERAUFTRÄGE =====
			with ui.tab_panel(tab_recurring):
				_build_recurring_payments_section(user_id)

			# ===== TAB 4: ÜBERTRAG =====
			with ui.tab_panel(tab_transfer):
				_build_transfer_form(user_id)

			# ===== TAB 5: KONTOAUSZUG =====
			with ui.tab_panel(tab_statement):
				_build_statement_section(user_id)


def _build_domestic_payment_form(user_id: int) -> None:
	"""
	Formular für Inlandszahlung (US10).
	Eingabe: Ziel-IBAN, Betrag, Von-Konto, Zweck, Kategorie, Ausführungsdatum.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.payment_controller import payment_controller
	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

	# Kategorien laden
	with Session(engine) as session:
		category_repository = CategoryRepository(session)
		categories = category_repository.list_all()
	category_options = {c.category_id: c.name for c in categories}

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
		# Ziel-IBAN
		iban_input = ui.input(label="Ziel-IBAN").props("outlined")
		iban_input.classes("w-full mb-4")

		# Betrag
		amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined")
		amount_input.classes("w-full mb-4")

		# Von-Konto
		from_account_select = ui.select(
			options=account_options,
			label="Von-Konto",
		).props("outlined")
		from_account_select.classes("w-full mb-4")

		# Kategorie
		category_select = ui.select(
			options=category_options,
			label="Kategorie",
		).props("outlined")
		category_select.classes("w-full mb-4")

		# Zweck
		purpose_input = ui.textarea(label="Verwendungszweck").props("outlined")
		purpose_input.classes("w-full mb-4")

		# Ausführungsdatum
		ui.label("Ausführungsdatum").classes("text-sm text-gray-600")
		execution_date_picker = ui.date(value=date.today().isoformat()).props("outlined")
		execution_date_picker.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_create_payment() -> None:
			"""Führt die Zahlung aus."""
			execution_date = date.fromisoformat(execution_date_picker.value)
			if execution_date < date.today():
				error = "Ausführungsdatum darf nicht in der Vergangenheit liegen"
				error_label.set_text(error)
				ui.notify(error, type="negative")
				return

			payload = {
				"target_iban": iban_input.value,
				"amount": amount_input.value or 0,
				"from_account_id": from_account_select.value,
				"category_id": category_select.value,
				"purpose": purpose_input.value,
				"execution_date": execution_date_picker.value,
			}

			error = payment_controller.create_payment(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Zahlung erfolgreich ausgeführt", type="positive")
				iban_input.value = ""
				amount_input.value = 0
				from_account_select.value = None
				category_select.value = None
				purpose_input.value = ""
				execution_date_picker.value = date.today().isoformat()
				error_label.set_text("")

		ui.button("Zahlung ausführen", on_click=handle_create_payment).classes("w-full")


def _build_recurring_payments_section(user_id: int) -> None:
	"""
	Daueraufträge (US6).
	Liste aller Daueraufträge + Formular für neue.
	"""
	from nicegui import ui

	from src.services.recurring_service import recurring_service
	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.recurring_controller import recurring_controller
	from sqlmodel import Session

	with ui.column().classes("w-full gap-6"):

		# === NEUE DAUERAUFTRAG ERSTELLEN ===
		with ui.expansion("Neue Dauerauftrag erstellen").classes("w-full"):

			# Kategorien laden
			with Session(engine) as session:
				category_repository = CategoryRepository(session)
				categories = category_repository.list_all()
			category_options = {c.category_id: c.name for c in categories}

			# Konten laden
			result = account_controller.list_accounts(user_id)
			if isinstance(result, str):
				account_options = {}
			else:
				account_options = {
					(a.account_id if hasattr(a, "account_id") else a.get("account_id")): 
					(a.iban if hasattr(a, "iban") else a.get("iban"))
					for a in result
				}

			with ui.column().classes("w-full gap-4"):

				amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined")
				amount_input.classes("w-full")

				category_select = ui.select(options=category_options, label="Kategorie").props("outlined")
				category_select.classes("w-full")

				account_select = ui.select(account_options, label="Konto").props("outlined")
				account_select.classes("w-full")

				iban_input = ui.input(label="Ziel-IBAN").props("outlined")
				iban_input.classes("w-full")

				interval_select = ui.select(
					options={"monthly": "Monatlich", "yearly": "Jährlich"},
					label="Intervall",
				).props("outlined")
				interval_select.classes("w-full")

				ui.label("Startdatum").classes("text-sm text-gray-600")
				start_date_picker = ui.date(value=date.today().isoformat()).props("outlined")
				start_date_picker.classes("w-full")

				ui.label("Enddatum (optional)").classes("text-sm text-gray-600")
				end_date_picker = ui.date().props("outlined")
				end_date_picker.classes("w-full")

				error_label = ui.label("").classes("text-red-600")

				async def handle_create_recurring() -> None:
					"""Erstellt einen neuen Dauerauftrag."""
					if start_date_picker.value < date.today().isoformat():
						ui.notify("Startdatum darf nicht in der Vergangenheit liegen", type="negative")
						return

					payload = {
						"user_id": user_id,
						"amount": amount_input.value or 0,
						"category_id": category_select.value,
						"account_id": account_select.value,
						"target_iban": iban_input.value,
						"interval": interval_select.value,
						"start_date": start_date_picker.value,
						"end_date": end_date_picker.value or None,
					}

					error = recurring_controller.create_recurring(payload)

					if error:
						error_label.set_text(error)
						ui.notify(error, type="negative")
					else:
						ui.notify("Dauerauftrag erfolgreich erstellt", type="positive")
					# Formular zurücksetzen
					amount_input.value = 0
					category_select.value = None
					account_select.value = None
					iban_input.value = ""
					interval_select.value = None
					start_date_picker.value = date.today().isoformat()
					end_date_picker.value = ""
					error_label.set_text("")

				ui.button("Dauerauftrag erstellen", on_click=handle_create_recurring).classes("w-full")

			try:
				recurring = recurring_service.list_recurring(user_id)

				if isinstance(recurring, str):
					ui.notify(recurring, type="negative")
					return
			except Exception as e:
				ui.notify(f"Fehler beim Laden der Daueraufträge: {str(e)}", type="negative")
				return

			# Hilfsfunktion zum Neuladen der Daueraufträge-Liste
			def refresh_recurring_table():
				nonlocal recurring
				recurring = recurring_service.list_recurring(user_id)
				rows = []
				for rec in recurring:
					amount_val = rec.amount if hasattr(rec, 'amount') else rec.get('amount')
					interval_val = rec.interval if hasattr(rec, 'interval') else rec.get('interval')
					last_executed = rec.last_executed if hasattr(rec, 'last_executed') else rec.get('last_executed')
					
					if isinstance(last_executed, str):
						last_executed = date.fromisoformat(last_executed)
					
					next_exec = recurring_service._next_due_date(last_executed, interval_val)

					if next_exec <= date.today():
						next_exec = recurring_service._next_due_date(next_exec, interval_val)

					rows.append({
						"recurring_id": rec.recurring_id if hasattr(rec, 'recurring_id') else rec.get('recurring_id'),
						"amount": f"{amount_val:,.2f}",
						"target_iban": rec.target_iban if hasattr(rec, "target_iban") else rec.get("target_iban"),
						"interval": "Monatlich" if interval_val == "monthly" else "Jährlich",
						"next_execution": str(next_exec),
					})
				recurring_table.rows = rows

			# Tabelle mit actions-Spalte
			recurring_table = ui.table(columns=[
				{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
				{"name": "target_iban", "label": "Ziel-IBAN", "field": "target_iban", "align": "left"},
				{"name": "interval", "label": "Intervall", "field": "interval", "align": "left"},
				{"name": "next_execution", "label": "Nächste Ausführung", "field": "next_execution", "align": "left"},
				{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
			], rows=[]).props("dense")
			recurring_table.classes("w-full")

			# Button-Slot für Aktionen (Bearbeiten, Löschen)
			recurring_table.add_slot("body-cell-actions", """
				<q-td :props="props">
					<q-btn label="Ändern" color="primary" size="sm" flat
						@click="$parent.$emit('edit_recurring', props.row)" />
					<q-btn label="Löschen" color="negative" size="sm" flat
						@click="$parent.$emit('delete_recurring', props.row)" />
				</q-td>
			""")

			# Löschen mit Bestätigung
			def handle_delete_recurring(e) -> None:
				row = e.args
				recurring_id = row.get("recurring_id")

				with ui.dialog() as confirm_dialog, ui.card():
					ui.label("Dauerauftrag wirklich löschen?").classes("text-subtitle1 font-semibold")
					ui.label(f"Betrag: {row.get('amount')} CHF | IBAN: {row.get('target_iban')}").classes("text-gray-600")
					with ui.row().classes("gap-4 mt-4"):
						ui.button("Abbrechen", on_click=confirm_dialog.close).props("flat")
						def do_delete(rid=recurring_id):
							error = recurring_controller.delete_recurring(rid)
							confirm_dialog.close()
							if error:
								ui.notify(error, type="negative")
							else:
								ui.notify("Dauerauftrag gelöscht", type="positive")
								refresh_recurring_table()
						ui.button("Löschen", on_click=do_delete).props("color=negative unelevated")
				confirm_dialog.open()

			recurring_table.on("delete_recurring", handle_delete_recurring)

			# Bearbeiten-Dialog
			def handle_edit_recurring(e) -> None:
				row = e.args
				recurring_id = row.get("recurring_id")

				# Lade den aktuellen Dauerauftrag
				from src.data_access.repositories.recurring_repository import RecurringRepository
				with Session(engine) as session:
					recurring_repository = RecurringRepository(session)
					current_recurring = recurring_repository.get_by_id(recurring_id)
					if current_recurring is None:
						ui.notify("Dauerauftrag nicht gefunden", type="negative")
						return

					with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
						ui.label("Dauerauftrag bearbeiten").classes("text-subtitle1 font-semibold mb-4")

						amount_edit = ui.number(
							label="Betrag (CHF)",
							value=current_recurring.amount,
							min=0.01,
							step=0.01
						).props("outlined")
						amount_edit.classes("w-full mb-4")

						interval_edit = ui.select(
							options={"monthly": "Monatlich", "yearly": "Jährlich"},
							value=current_recurring.interval,
							label="Intervall"
						).props("outlined")
						interval_edit.classes("w-full mb-4")

						target_iban_edit = ui.input(
							label="Ziel-IBAN",
							value=current_recurring.target_iban
						).props("outlined")
						target_iban_edit.classes("w-full mb-4")

						ui.label("Enddatum (optional)").classes("text-sm text-gray-600")
						end_date_edit = ui.date(
							value=str(current_recurring.end_date) if current_recurring.end_date else ""
						).props("outlined")
						end_date_edit.classes("w-full mb-4")

						with ui.row().classes("gap-4"):
							ui.button("Abbrechen", on_click=edit_dialog.close).props("flat")
							def do_edit(rid=recurring_id):
								payload = {
									"amount": amount_edit.value or 0,
									"interval": interval_edit.value,
									"target_iban": target_iban_edit.value,
									"end_date": end_date_edit.value or None,
								}
								error = recurring_controller.update_recurring(rid, payload)
								edit_dialog.close()
								if error:
									ui.notify(error, type="negative")
								else:
									ui.notify("Dauerauftrag aktualisiert", type="positive")
									refresh_recurring_table()
							ui.button("Speichern", on_click=do_edit).props("color=primary unelevated")
					edit_dialog.open()

			recurring_table.on("edit_recurring", handle_edit_recurring)

			# Initialisiere die Tabelle
			refresh_recurring_table()




def _build_transfer_form(user_id: int) -> None:
	"""
	Formular für Übertrag zwischen eigenen Konten.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
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
		amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined")
		amount_input.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_transfer() -> None:
			"""Führt Übertrag aus."""
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
				ui.notify("Übertrag erfolgreich", type="positive")
				amount_input.value = 0

		ui.button("Umbuchen", on_click=handle_transfer).classes("w-full")


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
		category_repository = CategoryRepository(session)
		categories = category_repository.list_all()
	category_options = {c.category_id: c.name for c in categories}

	with ui.card().classes("w-full"):

		# Filter-Bereich
		with ui.row().classes("gap-4 mb-4"):
			start_date_picker = ui.date(value=(date.today() - timedelta(days=30)).isoformat()).props("outlined")
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
				transactions_table,
			))
		# Transaktionsliste (Tabelle)
		transactions_table = ui.table(columns=[
			{"name": "date", "label": "Datum", "field": "date", "align": "left"},
			{"name": "type", "label": "Typ", "field": "type", "align": "left"},
			{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
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
		category_repository = CategoryRepository(session)
		categories = category_repository.list_all()
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


def _logout() -> None:
	"""Meldet den User ab."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")


def _build_statement_section(user_id: int) -> None:
	"""
	Kontoauszug-Generator (US12).
	Konto-Auswahl, Zeitraum, PDF-Download.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
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

		# Konto-Auswahl
		account_select = ui.select(
			options=account_options,
			label="Konto auswählen",
		).props("outlined")
		account_select.classes("w-full mb-4")

		# Zeitraum
		start_date_picker = ui.date(value=date.today().isoformat()).props("outlined")
		start_date_picker.label = "Von"
		start_date_picker.classes("w-full mb-4")

		end_date_picker = ui.date(value=date.today().isoformat()).props("outlined")
		end_date_picker.label = "Bis"
		end_date_picker.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_generate_statement() -> None:
			"""Generiert einen Kontoauszug als PDF und bietet Download an."""
			start_date = date.fromisoformat(start_date_picker.value)
			end_date = date.fromisoformat(end_date_picker.value)

			result = payment_controller.generate_statement(
				account_select.value,
				start_date,
				end_date,
			)

			if isinstance(result, str) and result.endswith(".pdf"):
				ui.download(result, filename=f"kontoauszug_{start_date}_{end_date}.pdf")
				ui.notify("Kontoauszug erfolgreich generiert", type="positive")
			else:
				error_label.set_text(result)
				ui.notify(result, type="negative")

		ui.button("Kontoauszug generieren", on_click=handle_generate_statement).classes("w-full")
