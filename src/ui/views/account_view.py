"""src.ui.views.account_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

=== WAS KANN DER USER AUF DIESER SEITE TUN? ===
    Tab 1 – Konten-Übersicht:
        Alle eigenen Konten anzeigen (aktiv und geschlossen).
        Aktive Konten koennen geschlossen werden (wenn Saldo = 0).

    Tab 2 – Konto eröffnen:
        Neues Privat- oder Sparkonto eroeffnen.
        Die App generiert automatisch eine Schweizer IBAN.

    Tab 3 – Bewegungen:
        Konto auswaehlen, Transaktionen des aktuellen Monats anzeigen.
        Filter: Monat, Jahr, Kategorie (eingeklappt unter "Suchoptionen").
        Sub-Tab "Geplante Zahlungen": zukuenftige Zahlungen anzeigen,
        bearbeiten und stornieren.

    Tab 4 – Kontoauszug:
        PDF-Kontoauszug fuer ein Konto und einen Zeitraum herunterladen.

=== WAS DIESE VIEW NICHT TUT ===
Sie enthaelt KEINE fachlichen Regeln. Alle Regeln liegen im `AccountService`:
    - "Konto nur schliessen wenn Saldo 0" → AccountService.close_account()
    - "IBAN-Generierung (100 Versuche)" → AccountService._generate_iban()

=== AUFRUF-KETTE: KONTO EROEFFNEN ===
    User klickt "Konto eröffnen"
    → handle_open_account()                      [diese View]
    → account_controller.open_account(payload)   [AccountController]
    → AccountService.open_account(payload)        [AccountService]
    → AccountRepository.create(account)           [Repository → DB INSERT]
    → None bei Erfolg, String bei Fehler

=== AUFRUF-KETTE: KONTO SCHLIESSEN ===
    User klickt "Schliessen" in Tabelle
    → handle_close_active(e)                     [diese View]
    → account_controller.close_account(account_id)
    → AccountService.close_account(account_id)
    → Pruefung: balance == 0.0? → AccountRepository.update()

=== AUFRUF-KETTE: KONTOAUSZUG ===
    User klickt "Kontoauszug generieren"
    → handle_generate_statement()                [diese View]
    → payment_controller.generate_statement(...)
    → PaymentService.generate_statement(...)     [erstellt PDF-Datei]
    → Rueckgabe: Pfad zur PDF → ui.download(pfad)

=== AUFRUF-KETTE: BEWEGUNGEN (MONATSANSICHT) ===
    User oeffnet Tab "Bewegungen" oder klickt "Anwenden"
    → _refresh_bewegungen(user_id, account_id, month, year, category_id, table)
    → transaction_controller.filter_transactions(start_date, end_date, category_id, user_id)
    → TransactionService.filter_transactions(...)
    → TransactionRepository.filter_transactions(...) [DB SELECT mit JOINs]
    → Liste von Transaction-Dicts → clientseitig nach account_id gefiltert → Tabelle befuellen

    Standard beim Laden: aktueller Monat, erstes Konto des Users, keine Kategorie-Einschraenkung.
    Die Datumsberechnung (erster/letzter Tag des Monats) passiert in _refresh_bewegungen
    mit Pythons eingebautem `calendar.monthrange`.

=== AUFRUF-KETTE: GEPLANTE ZAHLUNGEN ===
    User oeffnet Sub-Tab "Geplante Zahlungen" oder klickt "Aktualisieren"
    → _refresh_planned(user_id, account_id, cat_filter, table)
    → transaction_controller.filter_transactions(morgen, 2099-12-31, category_id, user_id)
    → TransactionService.filter_transactions(...)
    → TransactionRepository.filter_transactions(...) [DB SELECT mit JOINs]
    → Liste von Transaction-Dicts → clientseitig nach account_id gefiltert → Tabelle befuellen

    User klickt "Ändern" in Zeile
    → handle_edit_planned(e)                        [diese View, Dialog oeffnen]
    → transaction_controller.edit_transaction(id, payload)
    → TransactionService.edit_transaction(...)
    → TransactionRepository.update()               [DB UPDATE]

    User klickt "Stornieren" in Zeile
    → handle_delete_planned(e)                      [diese View, Bestaetigung]
    → transaction_controller.delete_transaction(id, confirm=True)
    → TransactionService.delete_transaction(...)
    → TransactionRepository.delete()               [DB DELETE]

=== LOGIN-GUARD ===
    if app_state.get("current_user") is None:
        ui.navigate.to("/")    # kein User eingeloggt → zurueck zum Login
        return

=== ARCHITEKTUR-KETTE ===
    Route "/accounts" → show()
    → Tab 1: _build_account_list() → account_controller
    → Tab 2: _build_open_account_form() → account_controller
    → Tab 3: _build_bewegungen_section() → transaction_controller
    → Tab 4: _build_statement_section() → payment_controller

Route: `/accounts`
"""

from datetime import date, timedelta

from src.ui.controllers.auth_controller import auth_controller
from src.ui.controllers.account_controller import account_controller
from src.ui.controllers.transaction_controller import transaction_controller
from src.ui.app_state import app_state


def _build_statement_section(user_id: int) -> None:
	"""Rendert den Kontoauszug-Generator (US12).

	Der Nutzer waehlt ein Konto und einen Zeitraum. Danach wird ueber den
	`PaymentController` ein PDF erzeugt und zum Download angeboten.

	Args:
		user_id: ID des eingeloggten Users.
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
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in result
		}

	with ui.card().classes("w-full"):

		# Konto-Auswahl
		account_select = ui.select(
			options=account_options,
			label="Konto auswählen",
		).props("outlined")
		account_select.classes("w-full mb-4")

		# Zeitraum (Format: TT.MM.JJJJ)
		start_date_picker = ui.date_input("Von", value=date.today().strftime('%d.%m.%Y'))
		start_date_picker.classes("w-full mb-4")
		start_date_picker.picker.props('mask=DD.MM.YYYY')

		end_date_picker = ui.date_input("Bis", value=date.today().strftime('%d.%m.%Y'))
		end_date_picker.classes("w-full mb-4")
		end_date_picker.picker.props('mask=DD.MM.YYYY')

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_generate_statement() -> None:
			"""Generiert einen Kontoauszug als PDF und bietet einen Download an.

			Raises:
				ValueError: Wenn einer der Datepicker keinen gueltigen ISO-Datumsstring enthaelt.
			"""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
			if not account_select.value:
				error_label.set_text("Bitte wählen Sie ein Konto aus.")
				ui.notify("Bitte wählen Sie ein Konto aus.", type="warning")
				return

			# DD.MM.YYYY → YYYY-MM-DD für date.fromisoformat()
			_sd, _sm, _sy = start_date_picker.value.split(".")
			_ed, _em, _ey = end_date_picker.value.split(".")
			start_date = date.fromisoformat(f"{_sy}-{_sm}-{_sd}")
			end_date = date.fromisoformat(f"{_ey}-{_em}-{_ed}")

			# Service schreibt die PDF in das `statements/`-Verzeichnis und gibt den Pfad zurueck.
			result = payment_controller.generate_statement(
				account_select.value,
				start_date,
				end_date,
			)

			# UI-Heuristik: Erfolgsfall liefert einen Pfad, der auf ".pdf" endet.
			# Fehlerfaelle sind im Controller als Fehlermeldung (String) vereinheitlicht.
			if isinstance(result, str) and result.endswith(".pdf"):
				ui.download(result, filename=f"kontoauszug_{start_date}_{end_date}.pdf")
				ui.notify("Kontoauszug erfolgreich generiert", type="positive")
			else:
				error_label.set_text(result)
				ui.notify(result, type="negative")

		ui.button("Kontoauszug generieren", on_click=handle_generate_statement).classes("w-full")


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

		ui.label("Konten").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_overview = ui.tab("Konten-Übersicht")
			tab_open = ui.tab("Konto eröffnen")
			tab_bewegungen = ui.tab("Bewegungen")
			tab_statement = ui.tab("Kontoauszug")

		with ui.tab_panels(tabs, value=tab_overview).classes("w-full"):

			# ===== TAB 1: KONTEN-ÜBERSICHT =====
			with ui.tab_panel(tab_overview):
				_build_account_list(user_id)

			# ===== TAB 2: KONTO ERÖFFNEN =====
			with ui.tab_panel(tab_open):
				_build_open_account_form(user_id)

			# ===== TAB 3: BEWEGUNGEN =====
			with ui.tab_panel(tab_bewegungen):
				_build_bewegungen_section(user_id)

			# ===== TAB 4: KONTOAUSZUG =====
			with ui.tab_panel(tab_statement):
				_build_statement_section(user_id)


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

	with ui.card().classes("w-full"):

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


def _build_bewegungen_section(user_id: int) -> None:
	"""Rendert den Tab "Bewegungen" mit Kontoauswahl, Monatsfilter und Geplanten Zahlungen.

	Der Tab besteht aus drei Teilen:

	1. Konto-Dropdown (ganz oben, gilt fuer beide Sub-Tabs):
	   Der User waehlt hier, fuer welches seiner Konten er die Transaktionen
	   sehen moechte. Standard ist das erste Konto in der Liste.

	2. Sub-Tab "Bewegungen":
	   Zeigt alle Transaktionen des gewaehlten Kontos fuer einen bestimmten Monat.
	   Unter "Suchoptionen" (eingeklappt) kann der User Monat, Jahr und Kategorie
	   anpassen und dann auf "Anwenden" klicken. Standard beim Oeffnen: aktueller Monat.

	3. Sub-Tab "Geplante Zahlungen":
	   Zeigt Transaktionen mit einem Datum in der Zukunft (ab morgen).
	   Der User kann diese bearbeiten (Betrag, Notiz) oder stornieren (loeschen).

	AUFRUF-KETTE (vereinfacht):
	    show() → _build_bewegungen_section(user_id)
	    → Konto-Dropdown: account_controller.list_accounts(user_id)
	    → Tabelle befuellen: _refresh_bewegungen(...) bzw. _refresh_planned(...)

	Args:
	    user_id: ID des eingeloggten Users. Wird benoetigt, um seine Konten und
	             seine Transaktionen aus der Datenbank zu laden.
	"""
	from nicegui import ui
	import calendar as cal_module
	from src.ui.controllers.category_controller import category_controller

	category_options = category_controller.list_categories()

	# Konten laden für Auswahl
	accounts_result = account_controller.list_accounts(user_id)
	if isinstance(accounts_result, str) or not accounts_result:
		account_options = {}
	else:
		account_options = {}
		for a in accounts_result:
			aid = a.account_id if hasattr(a, "account_id") else a.get("account_id")
			atype = (a.account_type if hasattr(a, "account_type") else a.get("account_type") or "").capitalize()
			aiban = ((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			account_options[aid] = f"{atype} · {aiban}"

	first_account_id = next(iter(account_options), None)

	# Konto-Auswahl (gilt für beide Sub-Tabs)
	with ui.card().classes("w-full"):
		account_select = ui.select(
			options=account_options,
			value=first_account_id,
			label="Konto",
		).props("outlined").classes("w-full")

	MONTH_NAMES = {
		1: "Januar", 2: "Februar", 3: "März", 4: "April",
		5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
		9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
	}
	current_year = date.today().year
	current_month = date.today().month
	year_options = {y: str(y) for y in range(current_year - 2, current_year + 1)}

	with ui.tabs() as sub_tabs:
		tab_booked = ui.tab("Bewegungen")
		tab_planned = ui.tab("Geplante Zahlungen")

	with ui.tab_panels(sub_tabs, value=tab_booked).classes("w-full"):

		# ===== TAB: BEWEGUNGEN =====
		with ui.tab_panel(tab_booked):
			with ui.expansion("Suchoptionen", icon="search").classes("w-full rounded-lg mb-2").props("dense"):
				with ui.row().classes("gap-4 items-end flex-wrap p-2"):
					month_select = ui.select(
						options=MONTH_NAMES,
						value=current_month,
						label="Monat",
					).props("outlined").classes("min-w-36")
					year_select = ui.select(
						options=year_options,
						value=current_year,
						label="Jahr",
					).props("outlined").classes("min-w-24")
					cat_select = ui.select(
						options={None: "Alle Kategorien", **category_options},
						value=None,
						label="Kategorie",
					).props("outlined").classes("min-w-40")
					ui.button("Anwenden", on_click=lambda: _refresh_bewegungen(
						user_id, account_select.value, month_select.value, year_select.value, cat_select.value, booked_table
					)).props("unelevated color=primary")

			with ui.card().classes("w-full"):
				booked_table = ui.table(columns=[
					{"name": "date", "label": "Datum", "field": "date", "align": "left"},
					{"name": "type", "label": "Typ", "field": "type", "align": "left"},
					{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
					{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
					{"name": "note", "label": "Notiz", "field": "note", "align": "left"},
				], rows=[]).props("dense")
				booked_table.classes("w-full")
				with booked_table.add_slot("no-data"):
					ui.label("Keine Transaktionen vorhanden").classes("text-gray-500 italic")

			_refresh_bewegungen(user_id, first_account_id, current_month, current_year, None, booked_table)

		# ===== TAB: GEPLANTE ZAHLUNGEN =====
		with ui.tab_panel(tab_planned):
			with ui.card().classes("w-full"):
				with ui.row().classes("gap-4 mb-4"):
					planned_cat_filter = ui.select(
						options={None: "Alle Kategorien", **category_options},
						value=None, label="Kategorie",
					).props("outlined")
					ui.button("Aktualisieren", on_click=lambda: _refresh_planned(
						user_id, account_select.value, planned_cat_filter, planned_table
					)).props("flat size=sm")

				planned_table = ui.table(columns=[
					{"name": "date", "label": "Datum", "field": "date", "align": "left"},
					{"name": "type", "label": "Typ", "field": "type", "align": "left"},
					{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
					{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
					{"name": "note", "label": "Notiz", "field": "note", "align": "left"},
					{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
				], rows=[]).props("dense")
				planned_table.classes("w-full")
				with planned_table.add_slot("no-data"):
					ui.label("Keine geplanten Zahlungen vorhanden").classes("text-gray-500 italic")

				planned_table.add_slot("body-cell-actions", """
					<q-td :props="props">
						<q-btn label="Ändern" color="primary" size="sm" flat
							@click="$parent.$emit('edit_planned', props.row)" />
						<q-btn label="Stornieren" color="negative" size="sm" flat
							@click="$parent.$emit('delete_planned', props.row)" />
					</q-td>
				""")

				def handle_edit_planned(e) -> None:
					"""Event-Handler: bearbeitet eine geplante (zukuenftige) Zahlung."""
					row = e.args
					transaction_id = row.get("transaction_id")
					with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
						ui.label("Geplante Zahlung bearbeiten").classes("text-subtitle1 font-semibold mb-4")
						amount_edit = ui.number(
							label="Betrag (CHF)",
							value=float(str(row.get("amount", "0")).replace(",", "")),
							min=0.01, step=0.01
						).props("outlined").classes("w-full mb-4")
						note_edit = ui.textarea(
							label="Notiz",
							value=row.get("note") if row.get("note") != "-" else ""
						).props("outlined").classes("w-full mb-4")
						with ui.row().classes("gap-4"):
							ui.button("Abbrechen", on_click=edit_dialog.close).props("flat")
							def do_edit(tid=transaction_id):
								error = transaction_controller.edit_transaction(
									tid, {"amount": amount_edit.value or 0, "note": note_edit.value}
								)
								edit_dialog.close()
								if error:
									ui.notify(error, type="negative")
								else:
									ui.notify("Gespeichert", type="positive")
									_refresh_planned(user_id, account_select.value, planned_cat_filter, planned_table)
							ui.button("Speichern", on_click=do_edit).props("color=primary unelevated")
					edit_dialog.open()

				def handle_delete_planned(e) -> None:
					"""Event-Handler: storniert eine geplante Zahlung (Loeschen mit Confirm)."""
					row = e.args
					transaction_id = row.get("transaction_id")
					with ui.dialog() as confirm_dialog, ui.card():
						ui.label("Zahlung stornieren?").classes("text-subtitle1 font-semibold")
						with ui.row().classes("gap-4 mt-4"):
							ui.button("Abbrechen", on_click=confirm_dialog.close).props("flat")
							def do_delete(tid=transaction_id):
								error = transaction_controller.delete_transaction(tid, confirm=True)
								confirm_dialog.close()
								if error:
									ui.notify(error, type="negative")
								else:
									ui.notify("Storniert", type="positive")
									_refresh_planned(user_id, account_select.value, planned_cat_filter, planned_table)
							ui.button("Stornieren", on_click=do_delete).props("color=negative unelevated")
					confirm_dialog.open()

				planned_table.on("edit_planned", handle_edit_planned)
				planned_table.on("delete_planned", handle_delete_planned)

				_refresh_planned(user_id, first_account_id, planned_cat_filter, planned_table)


def _refresh_bewegungen(user_id, account_id, month, year, category_id, table) -> None:
	"""Laedt Transaktionen fuer den gewaehlten Monat/Jahr und befuellt die Tabelle.

	WOHER KOMMT DER AUFRUF?
	    - Beim ersten Laden des Tabs (Standard: aktueller Monat, erstes Konto)
	    - Wenn der User im "Suchoptionen"-Bereich auf "Anwenden" klickt

	WAS PASSIERT HIER?
	    1. Aus Monat + Jahr wird der erste und letzte Tag berechnet
	       (z.B. Mai 2026 → 01.05.2026 bis 31.05.2026).
	    2. Der TransactionController holt alle Transaktionen des Users in diesem Zeitraum.
	    3. Die Ergebnisse werden clientseitig nach account_id gefiltert, weil der
	       Controller keinen direkten account_id-Filter unterstuetzt.
	    4. Die fertige Liste wird in die NiceGUI-Tabelle geschrieben (table.rows).

	AUFRUF-KETTE:
	    _refresh_bewegungen(...)
	    → transaction_controller.filter_transactions(start, end, category_id, user_id)
	    → TransactionService.filter_transactions(...)
	    → TransactionRepository.filter_transactions(...) [DB SELECT]
	    → Ergebnis (Liste von Dicts) → nach account_id filtern → table.rows setzen

	Args:
	    user_id:     ID des eingeloggten Users (fuer den DB-Filter).
	    account_id:  ID des gewaehlten Kontos; None bedeutet kein Konto-Filter.
	    month:       Monat als Zahl (1–12).
	    year:        Jahr als Zahl (z.B. 2026).
	    category_id: Kategorie-ID fuer den Filter; None bedeutet alle Kategorien.
	    table:       Das NiceGUI-Tabellenobjekt, das befuellt werden soll.
	"""
	from nicegui import ui
	import calendar as cal_module
	from src.ui.controllers.category_controller import category_controller
	_, last_day = cal_module.monthrange(year, month)
	result = transaction_controller.filter_transactions(
		start_date=date(year, month, 1),
		end_date=date(year, month, last_day),
		category_id=category_id,
		user_id=user_id,
	)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		return
	cats = category_controller.list_categories()
	table.rows = [{
		"transaction_id": t["transaction_id"],
		"date": t["date"],
		"type": t["type"],
		"amount": f"{t['amount']:,.2f}",
		"category": cats.get(t["category_id"], "—"),
		"note": t["note"] or "-",
	} for t in result if account_id is None or t.get("account_id") == account_id]


def _refresh_planned(user_id, account_id, cat_filter, table) -> None:
	"""Laedt geplante Zahlungen (Datum ab morgen) gefiltert nach Konto und befuellt die Tabelle.

	WOHER KOMMT DER AUFRUF?
	    - Beim ersten Laden des Sub-Tabs "Geplante Zahlungen"
	    - Wenn der User auf "Aktualisieren" klickt
	    - Nach einem erfolgreichen Bearbeiten oder Stornieren einer Zahlung

	WAS PASSIERT HIER?
	    Der Controller wird mit einem Startdatum von "morgen" und einem weit in der
	    Zukunft liegenden Enddatum (31.12.2099) aufgerufen. So kommen nur Transaktionen
	    zurueck, die noch nicht gebucht sind. Danach wird clientseitig nach account_id
	    gefiltert und die Tabelle wird befuellt.

	AUFRUF-KETTE:
	    _refresh_planned(...)
	    → transaction_controller.filter_transactions(morgen, 2099-12-31, category_id, user_id)
	    → TransactionService.filter_transactions(...)
	    → TransactionRepository.filter_transactions(...) [DB SELECT]
	    → Ergebnis (Liste von Dicts) → nach account_id filtern → table.rows setzen

	Args:
	    user_id:    ID des eingeloggten Users (fuer den DB-Filter).
	    account_id: ID des gewaehlten Kontos; None bedeutet kein Konto-Filter.
	    cat_filter: NiceGUI-Select-Element; dessen `.value` gibt die Kategorie-ID oder
	                None (= alle) zurueck.
	    table:      Das NiceGUI-Tabellenobjekt, das befuellt werden soll.
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller
	result = transaction_controller.filter_transactions(
		start_date=date.today() + timedelta(days=1),
		end_date=date(2099, 12, 31),
		category_id=cat_filter.value,
		user_id=user_id,
	)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		return
	cats = category_controller.list_categories()
	table.rows = [{
		"transaction_id": t["transaction_id"],
		"date": t["date"],
		"type": t["type"],
		"amount": f"{t['amount']:,.2f}",
		"category": cats.get(t["category_id"], "—"),
		"note": t["note"] or "-",
	} for t in result if account_id is None or t.get("account_id") == account_id]





def _build_sidebar() -> None:
	"""Baut die Sidebar-Navigation (Links zu den Views)."""
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
		ui.button("Dashboard", icon="home", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Transaktionen", icon="show_chart", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Budget", icon="savings", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Konten", icon="account_balance", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated align=left").classes("w-full justify-start sidebar-active")
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
