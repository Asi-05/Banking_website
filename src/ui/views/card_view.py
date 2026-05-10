"""src.ui.views.card_view

Card-View (NiceGUI) fuer die Kartenverwaltung.

Diese Datei gehoert zur **UI-View-Schicht**. Die View ist zustaendig fuer die
Darstellung (Tabs, Tabellen, Buttons) und das Ausloesen von Aktionen ueber
Controller.

Use-Cases:
- Debitkarten (US8): bestellen, sperren, ersetzen
- Kreditkarten (US9): beantragen, sperren, ersetzen, Abrechnungskonto setzen

Wichtig fuer das Verstaendnis:
- Fachregeln (z.B. "Debitkarte nur fuer Privatkonto", "max. 1 aktive Debitkarte",
  Kreditkartenlimit) liegen im `CardService`.
- Diese View ruft Regeln ausschliesslich ueber den `CardController` auf und
  zeigt nur das Ergebnis (Success/Fehler) in der UI an.

Route: `/cards`
"""

from src.ui.controllers.card_controller import card_controller
from src.ui.app_state import app_state


def show() -> None:
	"""Rendert die Karten-Seite (Tabs: Debitkarten und Kreditkarten).

	Die Seite ist geschuetzt: Ohne Login wird zur Startseite umgeleitet.
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
			ui.label("BetterBank").classes("text-h5 font-bold text-white pl-4")
			with ui.row().classes("items-center gap-2"):
				with ui.button(icon="settings").props("flat round").classes("text-white"):
					with ui.menu():
						ui.menu_item("Kontoeinstellungen", on_click=lambda: _open_settings_dialog(user_id))
				ui.button("Abmelden", icon="logout", on_click=lambda: _logout()) \
					.props("flat no-caps") \
					.classes("text-white font-semibold")

	# ===== MAIN CONTENT =====
	with ui.column().classes("w-full gap-6 p-6"):

		ui.label("Karten").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_debit = ui.tab("Debitkarten")
			tab_credit = ui.tab("Kreditkarten")

		with ui.tab_panels(tabs, value=tab_debit):

			# ===== TAB 1: DEBITKARTEN =====
			with ui.tab_panel(tab_debit):
				_build_debit_cards_section(user_id)

			# ===== TAB 2: KREDITKARTEN =====
			with ui.tab_panel(tab_credit):
				_build_credit_cards_section(user_id)


def _build_debit_cards_section(user_id: int) -> None:
	"""Rendert den Bereich fuer Debitkarten (US8).

	Der Bereich bietet:
	- Bestellung einer neuen Debitkarte (nur fuer Privatkonten)
	- Anzeige aktiver und inaktiver Debitkarten
	- Aktionen wie Sperren/Ersetzen ueber den Controller

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui
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
				# hasattr() prueft, ob ein Objekt ein bestimmtes Attribut hat.
				# Warum noetig: Im echten Betrieb kommen die Daten als Python-Objekte (ORM-Modelle)
				# aus der Datenbank. In Tests kommen sie manchmal als einfache Dicts.
				# Mit hasattr() koennen wir beides lesen, ohne dass der Code abstuerzt.
				# Hier filtern wir zusaetzlich nur Privatkonten.
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
				"""Bestellt eine Debitkarte ueber den Controller.

				Die UI uebergibt nur die Auswahl (Konto). Fachliche Regeln (z.B.
				"max. 1 aktive Debitkarte") werden im Service geprueft.
				"""
				# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
				# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
				# Der Service prueft u.a. "max. 1 aktive Debitkarte" und ob das Konto
				# wirklich geeignet ist. Die UI zeigt hier nur den Fehlertext an.
				error = card_controller.order_debit_card(account_select.value)

				if error:
					error_label.set_text(error)
					ui.notify(error, type="negative")
				else:
					ui.notify("Debitkarte erfolgreich bestellt", type="positive")
					account_select.value = None

			ui.button("Bestellen", on_click=handle_order_debit_card).classes("w-full")

		# === DEBITKARTEN-LISTE ===
		try:
			debit_cards = card_controller.list_debit_cards(user_id)
			if isinstance(debit_cards, str):
				ui.notify(debit_cards, type="negative")
				return

			from src.ui.controllers.account_controller import account_controller
			accounts = account_controller.list_accounts(user_id)
			account_map = {}
			if not isinstance(accounts, str):
				account_map = {
					(a.account_id if hasattr(a, "account_id") else a.get("account_id")):
					((a.iban if hasattr(a, "iban") else a.get("iban")) or "").upper()
					for a in accounts
				}

			def make_row(card):
				"""Konvertiert eine Karte in eine Tabellenzeile.

				In manchen Tests/Fixtures kommen Dicts statt ORM-Objekten vor.
				Darum wird defensiv mit `hasattr(...)`/`.get(...)` gelesen.
				"""
				account_iban = account_map.get(
					card.account_id if hasattr(card, "account_id") else card.get("account_id"), "N/A"
				)
				return {
					"card_id": card.card_id if hasattr(card, "card_id") else card.get("card_id"),
					"card_number": f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}",
					"expire_date": str(card.expire_date if hasattr(card, "expire_date") else card.get("expire_date")),
					"account": account_iban,
					"status": card.status if hasattr(card, "status") else card.get("status"),
				}

			COLUMNS = [
				{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
				{"name": "expire_date", "label": "Ablaufdatum", "field": "expire_date", "align": "left"},
				{"name": "account", "label": "Konto", "field": "account", "align": "left"},
				{"name": "status", "label": "Status", "field": "status", "align": "left"},
				{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
			]

			INACTIVE_COLUMNS = [
				{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
				{"name": "expire_date", "label": "Ablaufdatum", "field": "expire_date", "align": "left"},
				{"name": "account", "label": "Konto", "field": "account", "align": "left"},
				{"name": "status", "label": "Status", "field": "status", "align": "left"},
			]

			active_cards = [c for c in debit_cards if (c.status if hasattr(c, "status") else c.get("status")) == "aktiv"]
			inactive_cards = [c for c in debit_cards if (c.status if hasattr(c, "status") else c.get("status")) != "aktiv"]

			# === KASTEN 1: AKTIVE DEBITKARTE ===
			with ui.card().classes("w-full"):
				ui.label("Aktive Debitkarte").classes("text-subtitle2 font-semibold mb-2")
				if not active_cards:
					ui.label("Keine aktive Debitkarte.").classes("text-gray-500 italic")
				else:
					active_table = ui.table(columns=COLUMNS, rows=[make_row(c) for c in active_cards]).props("dense")
					active_table.classes("w-full")
					active_table.add_slot("body-cell-actions", """
						<q-td :props="props">
							<q-btn label="Sperren & Ersetzen" color="negative" size="sm" unelevated
								@click="$parent.$emit('block_and_replace_debit', props.row)" />
							<q-btn label="PIN bestellen" color="primary" size="sm" flat
								@click="$parent.$emit('order_pin_debit', props.row)" />
						</q-td>
					""")
					def handle_block_and_replace_debit(e) -> None:
						"""Sperrt die Karte und bestellt danach eine Ersatzkarte.

						Args:
							e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
						"""
						card_id = e.args.get("card_id")
						# Zwei Schritte: erst sperren (Sicherheitsmassnahme), dann ersetzen
						# (neue Kartennummer/Gueltigkeit).
						error = card_controller.block_debit_card(card_id)
						if error:
							ui.notify(f"Sperren fehlgeschlagen: {error}", type="negative")
							return
						error = card_controller.replace_debit_card(card_id)
						if error:
							ui.notify(f"Ersetzen fehlgeschlagen: {error}", type="negative")
						else:
							ui.notify("Karte gesperrt und Ersatzkarte bestellt", type="positive")
					def handle_order_pin_debit(e) -> None:
						"""UI-Demoaktion: PIN bestellen (hier nur Notification).

						Args:
							e: NiceGUI-Event; wird hier nicht ausgewertet.
						"""
						ui.notify("PIN bestellt", type="positive")
					active_table.on("block_and_replace_debit", handle_block_and_replace_debit)
					active_table.on("order_pin_debit", handle_order_pin_debit)

			# === KASTEN 2: GESPERRTE / ERSETZTE DEBITKARTEN ===
			with ui.card().classes("w-full mt-4"):
				ui.label("Gesperrte / Ersetzte Debitkarten").classes("text-subtitle2 font-semibold mb-2")
				if not inactive_cards:
					ui.label("Keine gesperrten oder ersetzten Karten.").classes("text-gray-500 italic")
				else:
					inactive_table = ui.table(columns=INACTIVE_COLUMNS, rows=[{**make_row(c), "status": "inaktiv"} for c in inactive_cards]).props("dense")
					inactive_table.classes("w-full")

		except Exception as e:
			ui.notify(f"Fehler beim Laden der Debitkarten: {str(e)}", type="negative")

def _build_credit_cards_section(user_id: int) -> None:
	"""Rendert den Bereich fuer Kreditkarten (US9).

	Der Bereich umfasst:
	- Kreditkartenantrag (gewuenschtes Limit)
	- Anzeige aktiver/gesperrter Karten, ersetzter Karten und offener Antraege
	- Setzen eines Abrechnungskontos fuer aktive Kreditkarten

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui
	from src.ui.controllers.account_controller import account_controller

	with ui.column().classes("w-full gap-6"):

		# === NEUE KREDITKARTE BEANTRAGEN ===
		with ui.expansion("Neue Kreditkarte beantragen").classes("w-full"):

			# Gewünschtes Limit
			limit_input = ui.number(label="Gewünschtes Limit (CHF)", min=100, step=100).props("outlined")
			limit_input.classes("w-full mb-4")

			error_label = ui.label("").classes("text-red-600 mb-4")

			async def handle_create_credit_card() -> None:
				"""Event-Handler: beantragt eine Kreditkarte.

				Die Limit-Regel (max. 10'000) ist eine UI-Vorpruefung; die echte
				Validierung liegt im Service.
				"""
				# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
				# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
				if (limit_input.value or 0) > 10000:
					error_label.set_text("Das maximale Kreditlimit beträgt CHF 10'000.")
					return

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
			credit_cards = card_controller.list_credit_cards(user_id)

			if isinstance(credit_cards, str):
				ui.notify(credit_cards, type="negative")
				return

			# Trennung: aktive Karten, ersetzte Karten und offene Antraege.
			active_cards = [
				c
				for c in credit_cards
				if (c.status if hasattr(c, "status") else c.get("status")) in ["aktiv", "gesperrt"]
			]
			replaced_cards = [
				c
				for c in credit_cards
				if (c.status if hasattr(c, "status") else c.get("status")) == "ersetzt"
			]
			pending_cards = [
				c
				for c in credit_cards
				if (c.status if hasattr(c, "status") else c.get("status")) == "beantragt"
			]

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
						{"name": "billing_account", "label": "Abrechnungskonto", "field": "billing_account", "align": "left"},
						{"name": "last_billed", "label": "Letzte Abrechnung", "field": "last_billed", "align": "left"},
						{"name": "status", "label": "Status", "field": "status", "align": "left"},
						{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
					], rows=[]).props("dense")
					credit_table.classes("w-full")

					credit_table.add_slot("body-cell-actions", """
						<q-td :props="props">
							<q-btn label="Sperren & Ersetzen" color="negative" size="sm" unelevated
								@click="$parent.$emit('block_and_replace_credit', props.row)" />
							<q-btn label="PIN bestellen" color="primary" size="sm" flat
								@click="$parent.$emit('order_pin_credit', props.row)" />
						</q-td>
					""")

					def handle_block_and_replace_credit(e) -> None:
						"""Sperrt und ersetzt eine Kreditkarte.

						Args:
							e: NiceGUI-Event; die Tabellenzeile steht in `e.args`.
						"""
						creditcard_id = e.args.get("card_id")
						# Sperren + Ersetzen ist ein bewusstes Sicherheitsmuster.
						error = card_controller.block_credit_card(creditcard_id)
						if error:
							ui.notify(f"Sperren fehlgeschlagen: {error}", type="negative")
							return
						error = card_controller.replace_credit_card(creditcard_id)
						if error:
							ui.notify(f"Ersetzen fehlgeschlagen: {error}", type="negative")
						else:
							ui.notify("Kreditkarte gesperrt und Ersatzkarte bestellt", type="positive")
					
					def handle_order_pin_credit(e) -> None:
						"""UI-Demoaktion: PIN bestellen (hier nur Notification).

						Args:
							e: NiceGUI-Event; wird hier nicht ausgewertet.
						"""
						ui.notify("PIN bestellt", type="positive")
					
					credit_table.on("block_and_replace_credit", handle_block_and_replace_credit)
					credit_table.on("order_pin_credit", handle_order_pin_credit)

					# Daten: aktive Karten
					rows = []
					for card in active_cards:
						limit_val = card.limit if hasattr(card, "limit") else card.get("limit")
						balance_val = card.balance if hasattr(card, "balance") else card.get("balance")
						# In dieser App bedeutet `balance`: bereits genutzter Kredit.
						# Verfuegbar = Limit - genutzter Kredit.
						available = limit_val - balance_val
						
						# Abrechnungskonto anzeigen (optional, kann noch nicht gesetzt sein).
						billing_account = card.billing_account if hasattr(card, "billing_account") else card.get("billing_account")
						if billing_account is not None:
							billing_account_display = (billing_account.iban if hasattr(billing_account, "iban") else billing_account.get("iban", "N/A")).upper()
						else:
							billing_account_display = "Nicht gesetzt"
						
						# Letzte Abrechnung anzeigen. Hier kommt teils ein ISO-String aus der DB/Fixture.
						# Wir normalisieren auf `date`, um ein einheitliches Anzeigeformat zu haben.
						last_billed = card.last_billed if hasattr(card, "last_billed") else card.get("last_billed")
						if last_billed is not None:
							from datetime import date as date_type
							if isinstance(last_billed, str):
								from datetime import datetime
								last_billed = datetime.fromisoformat(last_billed).date()
							last_billed_display = last_billed.strftime("%d.%m.%Y")
						else:
							last_billed_display = "Noch keine"

						rows.append({
							"card_id": card.creditcard_id if hasattr(card, "creditcard_id") else card.get("creditcard_id"),
							"card_number": f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}",
							"limit": f"{limit_val:,.2f}",
							"balance": f"{balance_val:,.2f}",
							"available": f"{available:,.2f}",
							"billing_account": billing_account_display,
							"last_billed": last_billed_display,
							"status": card.status if hasattr(card, "status") else card.get("status"),
						})

					credit_table.rows = rows

			# === ABRECHNUNGSKONTO FESTLEGEN ===
			with ui.card().classes("w-full"):
				ui.label("Abrechnungskonto festlegen").classes("text-subtitle2 font-semibold mb-4")
				
				if not active_cards:
					ui.label("Keine aktiven Kreditkarten.").classes("text-gray-500 italic")
				else:
					# Karten-Dropdown
					card_options = {
						(card.creditcard_id if hasattr(card, "creditcard_id") else card.get("creditcard_id")):
						f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}"
						for card in active_cards
					}
					
					# Konto-Dropdown (nur Privatkonten)
					# (Fachregel im Service: Abrechnungskonto muss aktiv sein und dem User gehoeren.)
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
					
					with ui.row().classes("w-full gap-4"):
						card_select = ui.select(
							options=card_options,
							label="Kreditkarte auswählen",
						).props("outlined").classes("flex-1")
						
						account_select = ui.select(
							options=account_options,
							label="Privatkonto auswählen",
						).props("outlined").classes("flex-1")
					
					error_label = ui.label("").classes("text-red-600 mb-4 w-full")
					
					async def handle_set_billing_account() -> None:
						"""Setzt das Abrechnungskonto fuer eine Kreditkarte.

						Das Abrechnungskonto ist notwendig, damit spaeter eine Monatsabrechnung
						fuer die Kreditkarte erstellt werden kann.
						"""
						# `async` erlaubt NiceGUI, die UI reaktionsfaehig zu halten waehrend der Handler
						# laeuft — auch wenn spaeter laengere Operationen (z.B. Datenbankzugriffe) dazukommen.
						if not card_select.value or not account_select.value:
							error_label.set_text("Bitte Kreditkarte und Konto auswählen.")
							ui.notify("Bitte Kreditkarte und Konto auswählen", type="warning")
							return
						
						error = card_controller.handle_set_billing_account(
							card_select.value,
							account_select.value
						)
						
						if error:
							error_label.set_text(error)
							ui.notify(error, type="negative")
						else:
							error_label.set_text("")
							ui.notify("Abrechnungskonto gespeichert", type="positive")
							card_select.value = None
							account_select.value = None
					
					ui.button("Speichern", on_click=handle_set_billing_account).classes("w-full")
				
				# === WARNUNG: KEIN ABRECHNUNGSKONTO ===
				# Ohne Billing-Account kann `CreditCardBillingService` keine Monatsabrechnung ausfuehren.
				cards_without_billing = [
					c for c in active_cards 
					if (c.billing_account_id if hasattr(c, "billing_account_id") else c.get("billing_account_id")) is None
				]
				
				if cards_without_billing:
					ui.separator().classes("my-4")
					with ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-400"):
						ui.label("⚠️ Kein Abrechnungskonto gesetzt").classes("text-subtitle2 font-semibold text-yellow-800 mb-2")
						ui.label(
							f"{len(cards_without_billing)} Kreditkarte(n) haben kein Abrechnungskonto. "
							"Der Monatsabschluss ist für diese Karten inaktiv."
						).classes("text-sm text-yellow-700")

			# === ERSETZTE KREDITKARTEN ===
			with ui.card().classes("w-full"):

				ui.label("Ersetzte Kreditkarten").classes("text-subtitle2 font-semibold")

				if not replaced_cards:
					ui.label("Keine ersetzten Kreditkarten.").classes("text-gray-500 italic")
				else:
					replaced_table = ui.table(columns=[
						{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
						{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
						{"name": "status", "label": "Status", "field": "status", "align": "left"},
					], rows=[]).props("dense")
					replaced_table.classes("w-full")

					replaced_rows = []
					for card in replaced_cards:
						limit_val = card.limit if hasattr(card, "limit") else card.get("limit")
						replaced_rows.append({
							"card_id": card.creditcard_id if hasattr(card, "creditcard_id") else card.get("creditcard_id"),
							"card_number": f"**** {(card.card_number if hasattr(card, 'card_number') else card.get('card_number'))[-4:]}",
							"limit": f"{limit_val:,.2f}",
							"status": card.status if hasattr(card, "status") else card.get("status"),
						})

					replaced_table.rows = replaced_rows

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
	"""Baut die Sidebar-Navigation (Links zu den Views).

	Falls ein User eingeloggt ist, wird zusaetzlich der Username angezeigt.
	"""
	from nicegui import ui
	user_id = app_state.get("user_id")
	if user_id:
		from src.ui.controllers.auth_controller import auth_controller
		username = auth_controller.get_username(user_id)
		if username:
			ui.label("Willkommen,").classes("text-xs text-gray-500 px-4 pt-2")
			ui.label(username).classes("text-sm font-semibold text-gray-500 px-4 pb-2")

	ui.separator()

	with ui.column().classes("gap-2 px-4 pb-4 pt-0"):
		ui.button("Dashboard", icon="home", on_click=lambda: ui.navigate.to("/dashboard")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Transaktionen", icon="show_chart", on_click=lambda: ui.navigate.to("/transactions")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Budget", icon="savings", on_click=lambda: ui.navigate.to("/budget")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Konten", icon="account_balance", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Karten", icon="credit_card", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated align=left").classes("w-full justify-start")


def _logout() -> None:
	"""Meldet den User ab und navigiert zur Startseite.

	Der Login-Status wird im globalen `app_state` zurueckgesetzt.
	"""
	from nicegui import ui
	app_state["current_user"] = None
	app_state["user_id"] = None
	ui.navigate.to("/")
	ui.notify("Erfolgreich abgemeldet", type="positive")


def _open_settings_dialog(user_id: int) -> None:
	"""Oeffnet den Kontoeinstellungen-Dialog (aktuell nur Anzeige).

	Die Daten werden ueber den `UserController` geladen. In dieser View werden
	Telefonnummer und Adresse nur angezeigt; Aenderungen werden als "beantragt"
	simuliert.

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
