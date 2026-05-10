"""src.ui.views.transaction_view

Transaktions-View (NiceGUI) als Sammelseite rund um Zahlungen und Bewegungen.

Diese Datei gehoert zur **UI-View-Schicht**. Die View ist zustaendig fuer:

- Rendern von Tabs und Formularen
- Einlesen von Nutzereingaben
- Aufruf von Controllern (die wiederum Services nutzen)
- Anzeigen von Fehlern/Success-Meldungen in der UI

Die Transaktions-View deckt u.a. folgende Use-Cases ab:

- Inlandszahlung: Externe Zahlung (Ausgabe-Transaktion + Payment-Daten)
- Bewegungen: gebuchte (bis heute) und geplante (ab morgen) Zahlungen
- Dauerauftraege: anlegen, anzeigen, bearbeiten, loeschen
- Uebertrag: Umbuchung zwischen eigenen Konten
- Kontoauszug: PDF-Auszug fuer ein Konto und einen Zeitraum

Wichtige Zusammenarbeit:

- Controller kapseln Service-Aufrufe und geben Fehler meist als String zurueck.
- Fachlogik (Validierungen, Salden, etc.) liegt in den Services.
- `app_state` steuert den Login-Guard fuer geschuetzte Seiten.

Route: `/transactions`
"""

from datetime import date, timedelta

from src.ui.controllers.transaction_controller import transaction_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Transaktions-Seite (Tabs fuer Zahlungen, Bewegungen, ...).

	Die Seite ist geschuetzt: Ohne Login wird zur Startseite umgeleitet.

	Hinweis:
		Die View baut ein Tab-Layout auf. Die eigentlichen Inhalte pro Tab werden
		in Hilfsfunktionen erzeugt (z.B. `_build_domestic_payment_form`).
	"""
	from nicegui import ui

	# Sicherheitspruefung: ohne Login zur Startseite.
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

		ui.label("Transaktionen").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_domestic = ui.tab("Neue Inlandszahlung")
			tab_list = ui.tab("Bewegungen")
			tab_recurring = ui.tab("Daueraufträge")
			tab_transfer = ui.tab("Übertrag")

		with ui.tab_panels(tabs, value=tab_domestic):

			# ===== TAB 1: NEUE INLANDSZAHLUNG =====
			with ui.tab_panel(tab_domestic):
				_build_domestic_payment_form(user_id)

			# ===== TAB 2: BEWEGUNGEN =====
			with ui.tab_panel(tab_list):
				_build_bewegungen_section(user_id)

			# ===== TAB 3: DAUERAUFTRÄGE =====
			with ui.tab_panel(tab_recurring):
				_build_recurring_payments_section(user_id)

			# ===== TAB 4: ÜBERTRAG =====
			with ui.tab_panel(tab_transfer):
				_build_transfer_form(user_id)


def _build_domestic_payment_form(user_id: int) -> None:
	"""Rendert das Formular fuer eine neue Inlandszahlung (US10).

	Die Eingaben werden gesammelt und als Payload an den `PaymentController`
	weitergegeben.

	Args:
		user_id: ID des eingeloggten Users (wird u.a. fuer die Kontoliste benoetigt).
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.payment_controller import payment_controller
	from src.ui.controllers.category_controller import category_controller

	category_options = category_controller.list_categories()

	# hasattr() prueft, ob ein Objekt ein bestimmtes Attribut hat.
	# Warum noetig: Im echten Betrieb kommen die Daten als Python-Objekte (ORM-Modelle)
	# aus der Datenbank. In Tests kommen sie manchmal als einfache Dicts.
	# Mit hasattr() koennen wir beides lesen, ohne dass der Code abstuerzt.
	#
	# Konten laden (nur aktive Konten werden als Quelle angeboten).
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		account_options = {}
	else:
		account_options = {
			(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in result
			if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
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
		execution_date_picker = ui.date(value=date.today().isoformat()).props("outlined first-day-of-week=1")
		execution_date_picker.classes("w-full mb-4")

		error_label = ui.label("").classes("text-red-600 mb-4")

		async def handle_create_payment() -> None:
			"""Validiert die UI-Felder und fuehrt die Zahlung aus.

			Die NiceGUI-Button-Callbacks koennen `async` sein. Das erlaubt es, spaeter
			(z.B. bei echten Netzwerk-/DB-Operationen) nicht-blockierende Ablaufe zu
			nutzen.

			Raises:
				ValueError: Wenn der Datepicker keinen gueltigen ISO-Datumsstring enthaelt.
			"""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
			execution_date = date.fromisoformat(execution_date_picker.value)
			# UI-Regel: Zahlungen duerfen nicht rueckdatiert werden.
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
				# Der Controller normalisiert ISO-Strings zu `datetime.date`.
				"date": execution_date_picker.value,
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
	"""Rendert den Tab "Dauerauftraege" (US6).

	Der Tab besteht aus:
	- einer Tabelle mit bestehenden Dauerauftraegen (inkl. Edit/Delete)
	- einem ausklappbaren Formular zum Erstellen eines neuen Dauerauftrags

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.recurring_controller import recurring_controller
	from src.ui.controllers.category_controller import category_controller

	with ui.column().classes("w-full gap-6"):

		category_map_names = category_controller.list_categories()

		# Konto-Mapping für Tabelle und Edit-Dialog
		accounts_result = account_controller.list_accounts(user_id)
		account_map = {
			int(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in (accounts_result if isinstance(accounts_result, list) else [])
			if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
		}

		# === TABELLE: DAUERAUFTRÄGE (direkt sichtbar, kein Klick nötig) ===

		def refresh_recurring_table():
			"""Laedt Dauerauftraege neu und befuellt die Tabelle.

			Der Controller kann Eintraege je nach Pfad als ORM-Objekte oder als Dicts
			liefern (z.B. in Tests). Deshalb wird hier robust mit `hasattr(...)`
			gelesen.
			"""
			recurring_list = recurring_controller.list_recurring(user_id)
			if isinstance(recurring_list, str):
				ui.notify(recurring_list, type="negative")
				return
			rows = []
			for rec in recurring_list:
				# Dauerauftraege koennen als ORM-Objekte oder als Dicts kommen.
				# Wir lesen die Felder deshalb robust aus.
				amount_val = rec.amount if hasattr(rec, 'amount') else rec.get('amount')
				interval_val = rec.interval if hasattr(rec, 'interval') else rec.get('interval')
				last_executed = rec.last_executed if hasattr(rec, 'last_executed') else rec.get('last_executed')
				# In manchen Pfaden kann `last_executed` als ISO-String vorliegen.
				if isinstance(last_executed, str):
					last_executed = date.fromisoformat(last_executed)
				# Naechste Ausfuehrung wird aus (last_executed, interval) berechnet.
				next_exec = recurring_controller.get_next_execution_date(last_executed, interval_val)
				# Falls ein Termin "heute oder frueher" ist, zeigen wir die *naechste* Ausfuehrung,
				# damit die Anzeige nicht wie "ueberfaellig" wirkt.
				if next_exec <= date.today():
					next_exec = recurring_controller.get_next_execution_date(next_exec, interval_val)
				rows.append({
					"recurring_id": rec.recurring_id if hasattr(rec, 'recurring_id') else rec.get('recurring_id'),
					"amount": f"{amount_val:,.2f}",
					"target_iban": ((rec.target_iban if hasattr(rec, "target_iban") else rec.get("target_iban")) or "").upper(),
					"category": category_map_names.get(
						rec.category_id if hasattr(rec, 'category_id') else rec.get('category_id'), "—"
					),
					"account_iban": account_map.get(
						int(rec.account_id if hasattr(rec, "account_id") else rec.get("account_id")), "N/A"
					),
					"interval": "Monatlich" if interval_val == "monthly" else "Jährlich",
					"next_execution": next_exec.strftime("%d.%m.%Y"),
				})
			recurring_table.rows = rows

		recurring_table = ui.table(columns=[
			{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
			{"name": "target_iban", "label": "Ziel-IBAN", "field": "target_iban", "align": "left"},
			{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
			{"name": "interval", "label": "Intervall", "field": "interval", "align": "left"},
			{"name": "next_execution", "label": "Nächste Ausführung", "field": "next_execution", "align": "left"},
			{"name": "account_iban", "label": "Belastungskonto", "field": "account_iban", "align": "left"},
			{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
		], rows=[]).props("dense")
		recurring_table.classes("w-full")

		recurring_table.add_slot("body-cell-actions", """
			<q-td :props="props">
				<q-btn label="Ändern" color="primary" size="sm" flat
					@click="$parent.$emit('edit_recurring', props.row)" />
				<q-btn label="Löschen" color="negative" size="sm" flat
					@click="$parent.$emit('delete_recurring', props.row)" />
			</q-td>
		""")

		def handle_delete_recurring(e) -> None:
			"""Bestaetigt und loescht einen Dauerauftrag.

			Args:
				e: NiceGUI-Event; relevante Daten stehen in `e.args` (die Tabellenzeile).
			"""
			row = e.args
			recurring_id = row.get("recurring_id")
			with ui.dialog() as confirm_dialog, ui.card():
				ui.label("Dauerauftrag wirklich löschen?").classes("text-subtitle1 font-semibold")
				ui.label(f"Betrag: {row.get('amount')} CHF | IBAN: {(row.get('target_iban') or '').upper()}").classes("text-gray-600")
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

		def handle_edit_recurring(e) -> None:
			"""Oeffnet einen Dialog zum Bearbeiten eines Dauerauftrags.

			Args:
				e: NiceGUI-Event; relevante Daten stehen in `e.args` (die Tabellenzeile).
			"""
			row = e.args
			recurring_id = row.get("recurring_id")
			current_recurring = recurring_controller.get_by_id(recurring_id)
			if current_recurring is None:
				ui.notify("Dauerauftrag nicht gefunden", type="negative")
				return
			edit_category_options = category_controller.list_categories()

			with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
				ui.label("Dauerauftrag bearbeiten").classes("text-subtitle1 font-semibold mb-4")
				amount_edit = ui.number(
					label="Betrag (CHF)", value=current_recurring.amount, min=0.01, step=0.01
				).props("outlined").classes("w-full mb-4")
				category_edit = ui.select(
					options=edit_category_options, value=current_recurring.category_id, label="Kategorie"
				).props("outlined").classes("w-full mb-4")
				account_edit = ui.select(
					options=account_map, value=int(current_recurring.account_id), label="Belastungskonto"
				).props("outlined").classes("w-full mb-4")
				interval_edit = ui.select(
					options={"monthly": "Monatlich", "yearly": "Jährlich"},
					value=current_recurring.interval, label="Intervall"
				).props("outlined").classes("w-full mb-4")
				target_iban_edit = ui.input(
					label="Ziel-IBAN", value=current_recurring.target_iban
				).props("outlined").classes("w-full mb-4")
				with ui.row().classes("gap-4"):
					ui.button("Abbrechen", on_click=edit_dialog.close).props("flat")
					def do_edit(rid=recurring_id):
						"""Speichert Aenderungen und aktualisiert danach die Tabelle."""
						payload = {
							"amount": amount_edit.value or 0,
							"category_id": category_edit.value,
							"account_id": account_edit.value,
							"interval": interval_edit.value,
							"target_iban": target_iban_edit.value,
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

		# Tabelle initial laden
		refresh_recurring_table()

		# === FORMULAR: NEUEN DAUERAUFTRAG ERSTELLEN (unter der Tabelle) ===
		with ui.expansion("Neuen Dauerauftrag erstellen").classes("w-full"):

			category_options = category_controller.list_categories()

			result = account_controller.list_accounts(user_id)
			if isinstance(result, str):
				form_account_options = {}
			else:
				form_account_options = {
					int(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
					((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
					for a in result
					if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
				}

			with ui.column().classes("w-full gap-4"):
				amount_input = ui.number(label="Betrag (CHF)", min=0.01, step=0.01).props("outlined").classes("w-full")
				category_select = ui.select(options=category_options, label="Kategorie").props("outlined").classes("w-full")
				account_select = ui.select(form_account_options, label="Konto").props("outlined").classes("w-full")
				iban_input = ui.input(label="Ziel-IBAN").props("outlined").classes("w-full")
				interval_select = ui.select(
					options={"monthly": "Monatlich", "yearly": "Jährlich"}, label="Intervall"
				).props("outlined").classes("w-full")
				ui.label("Startdatum").classes("text-sm text-gray-600")
				start_date_picker = ui.date(value=date.today().isoformat()).props("outlined first-day-of-week=1").classes("w-full")
				error_label = ui.label("").classes("text-red-600")

				async def handle_create_recurring() -> None:
					"""Legt einen neuen Dauerauftrag an.

					Der Controller erwartet die Datumswerte als ISO-String und normalisiert
					sie intern zu `datetime.date`.
				"""
					# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
					# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
					# Pflichtfeldprüfung
					if (not amount_input.value or not category_select.value
							or not account_select.value or not iban_input.value
							or not interval_select.value):
						error_label.set_text("Bitte alle Felder ausfüllen.")
						return
					if start_date_picker.value < date.today().isoformat():
						error_label.set_text("Startdatum darf nicht in der Vergangenheit liegen.")
						return
					error_label.set_text("")
					payload = {
						"user_id": user_id,
						"amount": amount_input.value,
						"category_id": category_select.value,
						"account_id": account_select.value,
						"target_iban": iban_input.value,
						"interval": interval_select.value,
						# Controller normalisiert ISO-String -> `date`.
						"start_date": start_date_picker.value,
					}
					error = recurring_controller.create_recurring(payload)
					if error:
						error_label.set_text(error)
						ui.notify(error, type="negative")
					else:
						ui.notify("Dauerauftrag erfolgreich erstellt", type="positive")
						amount_input.value = None
						category_select.value = None
						account_select.value = None
						iban_input.value = ""
						interval_select.value = None
						start_date_picker.value = date.today().isoformat()
						refresh_recurring_table()

				ui.button("Dauerauftrag erstellen", on_click=handle_create_recurring).classes("w-full")



def _build_bewegungen_section(user_id: int) -> None:
	"""Rendert den Tab "Bewegungen" (gebucht vs. geplant).

	Gebucht: alle Transaktionen bis einschliesslich heute.
	Geplant: alle Transaktionen ab morgen (z.B. vorgeplante Zahlungen).
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller

	category_options = category_controller.list_categories()

	with ui.tabs() as sub_tabs:
		tab_booked = ui.tab("Gebuchte Zahlungen")
		tab_planned = ui.tab("Geplante Zahlungen")

	with ui.tab_panels(sub_tabs, value=tab_booked):

		# ===== GEBUCHTE ZAHLUNGEN (date <= today, mit Von/Bis Filter) =====
		with ui.tab_panel(tab_booked):
			with ui.card().classes("w-full"):
				with ui.row().classes("gap-4 mb-4 items-end"):
					booked_start = ui.date(value=(date.today() - timedelta(days=30)).isoformat()).props("outlined first-day-of-week=1")
					booked_start.label = "Von"

					with ui.column().classes("gap-1"):
						ui.label("Bis").classes("text-sm text-gray-500")
						# Designentscheidung: Enddatum ist fix "heute" und nicht editierbar.
						# Das vermeidet Missverstaendnisse bei "gebucht": gebuchte Zahlungen
						# sind per Definition nicht in der Zukunft.
						ui.label(date.today().strftime("%d.%m.%Y")).classes(
							"text-body1 font-semibold text-gray-700 px-2 py-1 bg-gray-100 rounded"
						)
					booked_cat_filter = ui.select(
						options={None: "Alle Kategorien", **category_options},
						value=None, label="Kategorie",
					).props("outlined")
					ui.button("Filter anwenden", on_click=lambda: _refresh_booked(
						user_id, booked_start, booked_cat_filter, booked_table
					)).props("unelevated color=primary size=sm")

				booked_table = ui.table(columns=[
					{"name": "date", "label": "Datum", "field": "date", "align": "left"},
					{"name": "type", "label": "Typ", "field": "type", "align": "left"},
					{"name": "amount", "label": "Betrag (CHF)", "field": "amount", "align": "right"},
					{"name": "category", "label": "Kategorie", "field": "category", "align": "left"},
					{"name": "note", "label": "Notiz", "field": "note", "align": "left"},
				], rows=[]).props("dense")
				booked_table.classes("w-full")

				_refresh_booked(user_id, booked_start, booked_cat_filter, booked_table)

		# ===== GEPLANTE ZAHLUNGEN (date > heute, automatisch ab morgen) =====
		with ui.tab_panel(tab_planned):
			with ui.card().classes("w-full"):
				with ui.row().classes("gap-4 mb-4"):
					planned_cat_filter = ui.select(
						options={None: "Alle Kategorien", **category_options},
						value=None, label="Kategorie",
					).props("outlined")
					ui.button("Aktualisieren", on_click=lambda: _refresh_planned(
						user_id, planned_cat_filter, planned_table
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
									_refresh_planned(user_id, planned_cat_filter, planned_table)
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
									_refresh_planned(user_id, planned_cat_filter, planned_table)
							ui.button("Stornieren", on_click=do_delete).props("color=negative unelevated")
					confirm_dialog.open()

				planned_table.on("edit_planned", handle_edit_planned)
				planned_table.on("delete_planned", handle_delete_planned)

				_refresh_planned(user_id, planned_cat_filter, planned_table)



def _build_transfer_form(user_id: int) -> None:
	"""Rendert das Formular fuer einen Uebertrag zwischen eigenen Konten.

	Ein Uebertrag ist eine Umbuchung zwischen zwei eigenen Konten (Quelle -> Ziel).
Die fachliche Validierung passiert im Service (z.B. Existenz der Konten,
ausreichender Kontostand, etc.).

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui

	from src.ui.controllers.account_controller import account_controller
	from src.ui.controllers.payment_controller import payment_controller

	# Konten laden (nur aktive Konten koennen Quelle/Ziel sein).
	# Fachliche Validierung (z.B. "nur eigene Konten") passiert im Service.
	result = account_controller.list_accounts(user_id)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		account_options = {}
	else:
		account_options = {
			(a.account_id if hasattr(a, "account_id") else a.get("account_id")): 
			((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
			for a in result
			if (a.status if hasattr(a, "status") else a.get("status")) == "aktiv"
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
			"""Fuehrt die Umbuchung ueber den `PaymentController` aus."""
			# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
			# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
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
	"""Rendert eine Transaktionsliste mit Filtern (Datum, Kategorie).

	Die Tabelle bietet Aktionen zum Bearbeiten und Loeschen einzelner
	Transaktionen.

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller

	category_options = category_controller.list_categories()

	with ui.card().classes("w-full"):

		# Filter-Bereich
		with ui.row().classes("gap-4 mb-4"):
			start_date_picker = ui.date(value=(date.today() - timedelta(days=30)).isoformat()).props("outlined first-day-of-week=1")
			start_date_picker.label = "Von"

			end_date_picker = ui.date(value=date.today().isoformat()).props("outlined first-day-of-week=1")
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
			"""Event-Handler: bestaetigt und loescht eine Transaktion."""
			row = e.args
			transaction_id = row.get("transaction_id")

			with ui.dialog() as confirm_dialog, ui.card():
				ui.label("Transaktion wirklich löschen?").classes("text-subtitle1 font-semibold")
				# Hinweis: Das Euro-Zeichen stammt aus einer frueheren Version; die App nutzt
				# in der Regel CHF. (Nur Anzeige, keine fachliche Logik.)
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
			"""Event-Handler: oeffnet Dialog zum Bearbeiten einer Transaktion."""
			row = e.args
			transaction_id = row.get("transaction_id")

			with ui.dialog() as edit_dialog, ui.card().classes("w-96"):
				ui.label("Transaktion bearbeiten").classes("text-subtitle1 font-semibold mb-4")

				# Hinweis: Das Label "€" ist hier ein Ueberbleibsel aus einer frueheren Version.
				# Die App arbeitet durchgehend mit CHF — diese Anzeige ist nur ein Label-Fehler
				# und hat keinen Einfluss auf die gespeicherten Daten.
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
	"""Laedt Transaktionsliste neu und aktualisiert die Tabelle.

	Args:
		user_id: ID des eingeloggten Users.
		start_date_picker: NiceGUI-Datepicker; ISO-Datum in `.value`.
		end_date_picker: NiceGUI-Datepicker; ISO-Datum in `.value`.
		category_filter: Select-Element; `None` bedeutet "alle Kategorien".
		transactions_table: Tabelle, deren `rows` neu gesetzt werden.

	Raises:
		ValueError: Wenn einer der Datepicker keinen gueltigen ISO-Datumsstring enthaelt.
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller

	start_date = date.fromisoformat(start_date_picker.value)
	end_date = date.fromisoformat(end_date_picker.value)
	category_id = category_filter.value if category_filter.value is not None else None

	# Controller liefert serialisierbare Dicts (Datum/Typ bereits formatiert).
	result = transaction_controller.filter_transactions(
		start_date=start_date,
		end_date=end_date,
		category_id=category_id,
		user_id=user_id,
	)

	if isinstance(result, str):
		ui.notify(result, type="negative")
		return

	category_names = category_controller.list_categories()

	# Transaktionen in Tabellenformat konvertieren.
	rows = []
	for txn in result:
		category_name = category_names.get(txn['category_id'], f"ID {txn['category_id']}")
		rows.append({
			"transaction_id": txn["transaction_id"],
			"date": str(txn["date"]).replace("-", "."),
			"type": txn["type"],
			"amount": f"{txn['amount']:,.2f}",
			"category": category_name,
			"note": txn["note"] or "-",
		})

	if transactions_table:
		transactions_table.rows = rows


def _refresh_booked(user_id, start_picker, cat_filter, table) -> None:
	"""Laedt gebuchte Zahlungen (Datum <= heute) und befuellt die Tabelle.

	Die obere UI laesst den Nutzer nur ein Startdatum waehlen. Das Enddatum ist
	fix auf "heute" gesetzt (siehe Tab-Layout), damit "gebuchte" Zahlungen nicht
	versehentlich in die Zukunft gefiltert werden.
	"""
	from nicegui import ui
	from src.ui.controllers.category_controller import category_controller
	result = transaction_controller.filter_transactions(
		start_date=date.fromisoformat(start_picker.value),
		end_date=date.today(),
		category_id=cat_filter.value,
		user_id=user_id,
	)
	if isinstance(result, str):
		ui.notify(result, type="negative")
		return
	cats = category_controller.list_categories()
	table.rows = [{
		"transaction_id": t["transaction_id"],
		"date": str(t["date"]).replace("-", "."),
		"type": t["type"],
		"amount": f"{t['amount']:,.2f}",
		"category": cats.get(t["category_id"], "—"),
		"note": t["note"] or "-",
	} for t in result]


def _refresh_planned(user_id, cat_filter, table) -> None:
	"""Laedt geplante Zahlungen (Datum > heute, ab morgen) und befuellt die Tabelle.

	Wir filtern hier bewusst ab morgen bis zu einem weit in der Zukunft liegenden
	Datum, um "zukuenftige" Transaktionen zu bekommen.
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
		"date": str(t["date"]).replace("-", "."),
		"type": t["type"],
		"amount": f"{t['amount']:,.2f}",
		"category": cats.get(t["category_id"], "—"),
		"note": t["note"] or "-",
	} for t in result]


def _build_sidebar() -> None:
	"""Baut die Navigation (Sidebar) fuer die Transaktions-View."""
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
	"""Meldet den User ab und navigiert zur Startseite."""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")


def _open_settings_dialog(user_id: int) -> None:
	"""Oeffnet einen einfachen Dialog mit Kontoeinstellungen.

	Die Daten kommen aus dem `UserController`. In dieser View werden Telefon und
	Adresse aktuell nur angezeigt; Aenderungen werden als "beantragt" simuliert.
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


    
