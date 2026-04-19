"""
Payment View - Betterbank Banking App
Implementiert US6, US10, US12: Zahlungen, Daueraufträge, Kontoauszüge
Route: /payments
"""

from datetime import date

from src.ui.controllers.payment_controller import payment_controller
from src.ui.controllers.recurring_controller import recurring_controller
from src.ui.app_state import app_state


def show() -> None:
	"""
	Zeigt Zahlungen, Daueraufträge und Kontoauszüge.
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

		ui.label("Zahlungen").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_domestic = ui.tab("Inlandszahlung")
			tab_recurring = ui.tab("Daueraufträge")
			tab_statement = ui.tab("Kontoauszug")

		with ui.tab_panels(tabs):

			# ===== TAB 1: INLANDSZAHLUNG =====
			with ui.tab_panel(tab_domestic):
				_build_domestic_payment_form(user_id)

			# ===== TAB 2: DAUERAUFTRÄGE =====
			with ui.tab_panel(tab_recurring):
				_build_recurring_payments_section(user_id)

			# ===== TAB 3: KONTOAUSZUG =====
			with ui.tab_panel(tab_statement):
				_build_statement_section(user_id)


def _build_domestic_payment_form(user_id: int) -> None:
	"""
	Formular für Inlandszahlung (US10).
	Eingabe: Ziel-IBAN, Betrag, Von-Konto, Zweck, Kategorie.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.data_access.repositories.category_repository import CategoryRepository
	from src.data_access.db import engine
	from sqlmodel import Session

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

	# Kategorien laden
	with Session(engine) as session:
		categories = CategoryRepository.list_all(session)
	category_options = {c.category_id: c.name for c in categories}

	with ui.card().classes("w-full max-w-md"):

		# Ziel-IBAN
		iban_input = ui.input(label="Ziel-IBAN").props("outlined")
		iban_input.classes("w-full mb-4")

		# Betrag
		amount_input = ui.number(label="Betrag (€)", min=0.01, step=0.01).props("outlined")
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

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_create_payment() -> None:
			"""Führt die Zahlung aus."""
			payload = {
				"target_iban": iban_input.value,
				"amount": amount_input.value or 0,
				"from_account_id": from_account_select.value,
				"category_id": category_select.value,
				"purpose": purpose_input.value,
			}

			error = payment_controller.create_payment(payload)

			if error:
				error_label.set_text(error)
				ui.notify(error, type="negative")
			else:
				ui.notify("Zahlung erfolgreich ausgeführt", type="positive")
				iban_input.value = ""
				amount_input.value = 0
				category_select.value = None
				purpose_input.value = ""

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
	from sqlmodel import Session

	with ui.column().classes("w-full gap-6"):

		# === NEUE DAUERAUFTRAG ERSTELLEN ===
		with ui.expansion("Neue Dauerauftrag erstellen").classes("w-full"):

			# Kategorien laden
			with Session(engine) as session:
				categories = CategoryRepository.list_all(session)
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

				amount_input = ui.number(label="Betrag (€)", min=0.01, step=0.01).props("outlined")
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

				error_label = ui.label("").classes("text-red-600")

				async def handle_create_recurring() -> None:
					"""Erstellt einen neuen Dauerauftrag."""
					payload = {
						"user_id": user_id,
						"amount": amount_input.value or 0,
						"category_id": category_select.value,
						"account_id": account_select.value,
						"target_iban": iban_input.value,
						"interval": interval_select.value,
						"start_date": start_date_picker.value,
					}

					error = recurring_controller.create_recurring(payload)

					if error:
						error_label.set_text(error)
						ui.notify(error, type="negative")
					else:
						ui.notify("Dauerauftrag erfolgreich erstellt", type="positive")

				ui.button("Dauerauftrag erstellen", on_click=handle_create_recurring)

		# === DAUERAUFTRÄGE-LISTE ===
		with ui.card().classes("w-full"):

			ui.label("Meine Daueraufträge").classes("text-subtitle2 font-semibold")

			try:
				recurring = recurring_service.list_recurring(user_id)

				if isinstance(recurring, str):
					ui.notify(recurring, type="negative")
					return

				# Tabelle
				recurring_table = ui.table(columns=[
					{"name": "amount", "label": "Betrag (€)", "field": "amount", "align": "right"},
					{"name": "target_iban", "label": "Ziel-IBAN", "field": "target_iban", "align": "left"},
					{"name": "interval", "label": "Intervall", "field": "interval", "align": "left"},
					{"name": "next_execution", "label": "Nächste Ausführung", "field": "next_execution", "align": "left"},
				], rows=[]).props("dense")
				recurring_table.classes("w-full")

				# Daten mit berechneter nächster Ausführung
				from datetime import timedelta
				rows = []
				for rec in recurring:
					amount_val = rec.amount if hasattr(rec, 'amount') else rec.get('amount')
					interval_val = rec.interval if hasattr(rec, 'interval') else rec.get('interval')
					last_executed = rec.last_executed if hasattr(rec, 'last_executed') else rec.get('last_executed')
					
					# Nächste Ausführung berechnen
					if isinstance(last_executed, str):
						from datetime import datetime
						last_executed = datetime.fromisoformat(last_executed).date()
					
					if interval_val == "monthly":
						# Berechne nächsten Monat
						next_exec = last_executed.replace(day=1) + timedelta(days=32)
						next_exec = next_exec.replace(day=1)
					elif interval_val == "yearly":
						# Berechne nächstes Jahr
						next_exec = last_executed.replace(year=last_executed.year + 1)
					else:
						next_exec = last_executed

					rows.append({
						"amount": f"{amount_val:,.2f}",
						"target_iban": rec.target_iban if hasattr(rec, "target_iban") else rec.get("target_iban"),
						"interval": "Monatlich" if interval_val == "monthly" else "Jährlich",
						"next_execution": str(next_exec),
					})

				recurring_table.rows = rows

			except Exception as e:
				ui.notify(f"Fehler beim Laden der Daueraufträge: {str(e)}", type="negative")


def _build_statement_section(user_id: int) -> None:
	"""
	Kontoauszug-Generator (US12).
	Konto-Auswahl, Zeitraum, PDF-Download.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller

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
