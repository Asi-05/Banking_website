"""src.ui.views.card_view

Diese Datei gehoert zur **UI-View-Schicht** (NiceGUI).

=== WAS KANN DER USER AUF DIESER SEITE TUN? ===
    Tab 1 – Debitkarten (US8):
        - Neue Debitkarte bestellen (nur fuer Privatkonten)
        - Aktive Debitkarte anzeigen (Kartennummer maskiert: "**** XXXX")
        - Sperren + Ersetzen (zwei Schritte: erst sperren, dann Ersatzkarte)
        - Gesperrte/Ersetzte Karten anzeigen

    Tab 2 – Kreditkarten (US9):
        - Neue Kreditkarte beantragen (gewuenschtes Limit angeben)
        - Aktive Kreditkarten anzeigen: Limit, Genutzt, Verfuegbar, Abrechnungskonto
        - Sperren + Ersetzen
        - Abrechnungskonto festlegen (notwendig fuer monatliche Abrechnung)
        - Ersetzte Karten und offene Antraege anzeigen

=== WICHTIG: KREDITKARTE `balance` = SCHULDEN ===
Im Kreditkarten-Tab bedeutet "Genutzt (CHF)":
    CreditCard.balance = bereits ausgegeben (Schulden)
    Verfuegbar = limit - balance

Das ist NICHT der Kontostand eines Kontos! Verwechslungsgefahr!
Bei der monatlichen Abrechnung wird `balance` auf 0 gesetzt und der
Betrag vom `billing_account` (Privatkonto) abgezogen.

=== WAS DIESE VIEW NICHT TUT ===
Sie enthaelt KEINE fachlichen Regeln. Alle Regeln liegen im `CardService`:
    - "Max. 1 aktive Debitkarte pro User" → CardService._ensure_user_has_no_active_debit_card()
    - "Debitkarte nur fuer Privatkonto" → CardService.order_debit_card()
    - "Kreditlimit kann nicht ueberschritten werden" → CardService.create_credit_card()

=== AUFRUF-KETTE: DEBITKARTE BESTELLEN ===
    User klickt "Bestellen"
    → handle_order_debit_card()                    [diese View]
    → card_controller.order_debit_card(account_id) [CardController]
    → CardService.order_debit_card(account_id)     [Fachregel-Pruefung]
    → DebitCardRepository.create(debit_card)       [DB INSERT]
    → None bei Erfolg, String bei Fehler

=== AUFRUF-KETTE: SPERREN + ERSETZEN ===
    User klickt "Sperren & Ersetzen"
    → handle_block_and_replace_debit(e)
    → card_controller.block_debit_card(card_id)  [Schritt 1: sperren]
    → card_controller.replace_debit_card(card_id) [Schritt 2: ersetzen]
    Beide Schritte gehen ueber CardController → CardService → Repository

=== AUFRUF-KETTE: ABRECHNUNGSKONTO SETZEN ===
    User klickt "Speichern" (Abrechnungskonto)
    → handle_set_billing_account()
    → card_controller.handle_set_billing_account(creditcard_id, account_id)
    → CardService.set_billing_account(creditcard_id, account_id)
    → CreditCardRepository.update() → DB UPDATE

=== LOGIN-GUARD ===
    if app_state.get("current_user") is None:
        ui.navigate.to("/")    # kein User eingeloggt → zurueck zum Login
        return

=== ARCHITEKTUR-KETTE ===
    Route "/cards" → show()
    → Tab 1: _build_debit_cards_section() → card_controller
    → Tab 2: _build_credit_cards_section() → card_controller + account_controller

Route: `/cards`
"""

from src.ui.controllers.auth_controller import auth_controller
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

		ui.label("Karten").classes("text-h4 font-bold")

		# Tab-Layout
		with ui.tabs() as tabs:
			tab_debit = ui.tab("Debitkarten")
			tab_credit = ui.tab("Kreditkarten")

		with ui.tab_panels(tabs, value=tab_debit).classes("w-full"):

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
		with ui.expansion("Neue Debitkarte bestellen", value=True).classes("w-full"):

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
				if not account_select.value:
					error_label.set_text("Bitte wählen Sie ein Konto aus.")
					ui.notify("Bitte wählen Sie ein Konto aus.", type="warning")
					return

				with ui.dialog() as dlg, ui.card().classes("w-96"):
					ui.label("Debitkarte bestellen").classes("text-subtitle1 font-semibold mb-3")
					with ui.card().classes("w-full mb-3").props("flat bordered"):
						ui.label(f"Konto: {account_options.get(account_select.value, '')}").classes("text-sm text-gray-700")
					ui.label("Ihre Karte erhalten Sie in den nächsten 5 Arbeitstagen per Post.").classes("text-sm text-gray-600")
					with ui.row().classes("gap-4 mt-4 justify-end"):
						ui.button("Abbrechen", on_click=dlg.close).props("flat")
						def do_order(acc=account_select.value):
							# Der Service prueft u.a. "max. 1 aktive Debitkarte" und ob das Konto
							# wirklich geeignet ist. Die UI zeigt hier nur den Fehlertext an.
							error = card_controller.order_debit_card(acc)
							dlg.close()
							if error:
								error_label.set_text(error)
								ui.notify(error, type="negative")
							else:
								ui.notify("Debitkarte erfolgreich bestellt. Sie erhalten Ihre Karte in den nächsten 5 Arbeitstagen per Post.", type="positive", timeout=6000)
								account_select.value = None
						ui.button("Jetzt bestellen", on_click=do_order).props("color=primary unelevated")
				dlg.open()

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
					"expire_date": ((__import__("datetime").date.fromisoformat(card.expire_date if hasattr(card, "expire_date") else card.get("expire_date")) if isinstance((card.expire_date if hasattr(card, "expire_date") else card.get("expire_date")), str) else (card.expire_date if hasattr(card, "expire_date") else card.get("expire_date"))).strftime("%d.%m.%Y")),
					"account": account_iban,
					"status": card.status if hasattr(card, "status") else card.get("status"),
				}

			ui.add_css('''
				.debit-table .q-table { table-layout: fixed; width: 100%; }
				.debit-table .q-table th:nth-child(1), .debit-table .q-table td:nth-child(1) { width: 18%; }
				.debit-table .q-table th:nth-child(2), .debit-table .q-table td:nth-child(2) { width: 15%; }
				.debit-table .q-table th:nth-child(3), .debit-table .q-table td:nth-child(3) { width: 30%; }
				.debit-table .q-table th:nth-child(4), .debit-table .q-table td:nth-child(4) { width: 12%; }
				.debit-table .q-table th:nth-child(5), .debit-table .q-table td:nth-child(5) { width: 25%; }
			''')

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
				{"name": "spacer", "label": "", "field": "spacer", "align": "left"},
			]

			active_cards = [c for c in debit_cards if (c.status if hasattr(c, "status") else c.get("status")) == "aktiv"]
			inactive_cards = [c for c in debit_cards if (c.status if hasattr(c, "status") else c.get("status")) != "aktiv"]

			# === KASTEN 1: AKTIVE DEBITKARTE ===
			with ui.card().classes("w-full"):
				ui.label("Aktive Debitkarte").classes("text-subtitle2 font-semibold mb-2")
				if not active_cards:
					ui.label("Keine aktive Debitkarte.").classes("text-gray-500 italic")
				else:
					active_table = ui.table(columns=COLUMNS, rows=[make_row(c) for c in active_cards]).props("dense").classes("w-full debit-table")
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
						card_number = e.args.get("card_number", "")
						with ui.dialog() as dlg, ui.card().classes("w-96"):
							ui.label("Karte sperren & ersetzen?").classes("text-subtitle1 font-semibold mb-3")
							with ui.card().classes("w-full mb-3").props("flat bordered"):
								ui.label(f"Kartennummer: {card_number}").classes("text-sm text-gray-700")
							ui.label(
								"Die Karte wird sofort gesperrt. Eine Ersatzkarte wird zugestellt."
							).classes("text-sm text-orange-600 mt-2")
							with ui.row().classes("gap-4 mt-4 justify-end"):
								ui.button("Abbrechen", on_click=dlg.close).props("flat")
								def do_block_replace(cid=card_id):
									# Zwei Schritte: erst sperren (Sicherheitsmassnahme), dann ersetzen
									# (neue Kartennummer/Gueltigkeit).
									error = card_controller.block_debit_card(cid)
									if error:
										dlg.close()
										ui.notify(f"Sperren fehlgeschlagen: {error}", type="negative")
										return
									error = card_controller.replace_debit_card(cid)
									dlg.close()
									if error:
										ui.notify(f"Ersetzen fehlgeschlagen: {error}", type="negative")
									else:
										ui.notify("Karte gesperrt. Ihre Ersatzkarte erhalten Sie in den nächsten 5 Arbeitstagen per Post.", type="positive", timeout=6000)
								ui.button("Sperren & Ersetzen", on_click=do_block_replace).props("color=negative unelevated")
						dlg.open()
					def handle_order_pin_debit(e) -> None:
						"""UI-Demoaktion: PIN bestellen (hier nur Notification).

						Args:
							e: NiceGUI-Event; wird hier nicht ausgewertet.
						"""
						ui.notify("Sie erhalten in den nächsten 5 Arbeitstagen einen neuen PIN.", type="positive", timeout=5000)
					active_table.on("block_and_replace_debit", handle_block_and_replace_debit)
					active_table.on("order_pin_debit", handle_order_pin_debit)

			# === KASTEN 2: GESPERRTE / ERSETZTE DEBITKARTEN ===
			with ui.card().classes("w-full mt-4"):
				ui.label("Gesperrte / Ersetzte Debitkarten").classes("text-subtitle2 font-semibold mb-2")
				if not inactive_cards:
					ui.label("Keine gesperrten oder ersetzten Karten.").classes("text-gray-500 italic")
				else:
					inactive_table = ui.table(columns=INACTIVE_COLUMNS, rows=[{**make_row(c), "status": "inaktiv"} for c in inactive_cards]).props("dense").classes("w-full debit-table")

		except Exception as e:
			ui.notify(f"Fehler beim Laden der Debitkarten: {str(e)}", type="negative")

def _build_credit_cards_section(user_id: int) -> None:
	"""Rendert den Bereich fuer Kreditkarten (US9).

	Reihenfolge:
	1. "Karten" (aufklappbar, offen) – aktive + ersetzte/gesperrte Karten
	2. "Abrechnungskonto festlegen" (aufklappbar, geschlossen)
	3. "Neue Kreditkarte beantragen" (aufklappbar, geschlossen)

	Args:
		user_id: ID des eingeloggten Users.
	"""
	from nicegui import ui
	from src.ui.controllers.account_controller import account_controller

	with ui.column().classes("w-full gap-6"):

		try:
			credit_cards = card_controller.list_credit_cards_display(user_id)

			if isinstance(credit_cards, str):
				ui.notify(credit_cards, type="negative")
				return

			active_cards = [d for d in credit_cards if d["status"] in ["aktiv", "gesperrt"]]
			replaced_cards = [d for d in credit_cards if d["status"] == "ersetzt"]
			pending_cards = [d for d in credit_cards if d["status"] == "beantragt"]

			ui.add_css('''
				.credit-active-table .q-table { table-layout: fixed; width: 100%; }
				.credit-active-table .q-table th:nth-child(1), .credit-active-table .q-table td:nth-child(1) { width: 13%; }
				.credit-active-table .q-table th:nth-child(2), .credit-active-table .q-table td:nth-child(2) { width: 9%; }
				.credit-active-table .q-table th:nth-child(3), .credit-active-table .q-table td:nth-child(3) { width: 9%; }
				.credit-active-table .q-table th:nth-child(4), .credit-active-table .q-table td:nth-child(4) { width: 10%; }
				.credit-active-table .q-table th:nth-child(5), .credit-active-table .q-table td:nth-child(5) { width: 18%; }
				.credit-active-table .q-table th:nth-child(6), .credit-active-table .q-table td:nth-child(6) { width: 13%; }
				.credit-active-table .q-table th:nth-child(7), .credit-active-table .q-table td:nth-child(7) { width: 8%; }
				.credit-active-table .q-table th:nth-child(8), .credit-active-table .q-table td:nth-child(8) { width: 20%; }
				.credit-secondary-table .q-table { table-layout: fixed; width: 100%; }
				.credit-secondary-table .q-table th:nth-child(1), .credit-secondary-table .q-table td:nth-child(1) { width: 25%; }
				.credit-secondary-table .q-table th:nth-child(2), .credit-secondary-table .q-table td:nth-child(2) { width: 35%; }
				.credit-secondary-table .q-table th:nth-child(3), .credit-secondary-table .q-table td:nth-child(3) { width: 40%; }
			''')

			# === 1. KARTEN (offen) ===
			with ui.expansion("Karten", value=True).classes("w-full"):

				# Aktive Kreditkarten
				with ui.card().classes("w-full mb-4"):
					ui.label("Meine aktiven Kreditkarten").classes("text-subtitle2 font-semibold mb-2")

					if not active_cards:
						ui.label("Keine aktiven Kreditkarten.").classes("text-gray-500 italic")
					else:
						credit_table = ui.table(columns=[
							{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
							{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
							{"name": "balance", "label": "Genutzt (CHF)", "field": "balance", "align": "right"},
							{"name": "available", "label": "Verfügbar (CHF)", "field": "available", "align": "right"},
							{"name": "billing_account", "label": "Abrechnungskonto", "field": "billing_account", "align": "left"},
							{"name": "last_billed", "label": "Letzte Abrechnung", "field": "last_billed", "align": "left"},
							{"name": "status", "label": "Status", "field": "status", "align": "left"},
							{"name": "actions", "label": "Aktionen", "field": "actions", "align": "center"},
						], rows=[]).props("dense").classes("w-full credit-active-table")

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
							card_number = e.args.get("card_number", "")
							with ui.dialog() as dlg, ui.card().classes("w-96"):
								ui.label("Kreditkarte sperren & ersetzen?").classes("text-subtitle1 font-semibold mb-3")
								with ui.card().classes("w-full mb-3").props("flat bordered"):
									ui.label(f"Kartennummer: {card_number}").classes("text-sm text-gray-700")
								ui.label("Die Karte wird sofort gesperrt.").classes("text-sm text-orange-600 mt-2")
								with ui.row().classes("gap-4 mt-4 justify-end"):
									ui.button("Abbrechen", on_click=dlg.close).props("flat")
									def do_block_replace_credit(cid=creditcard_id):
										# Sperren + Ersetzen ist ein bewusstes Sicherheitsmuster.
										error = card_controller.block_credit_card(cid)
										if error:
											dlg.close()
											ui.notify(f"Sperren fehlgeschlagen: {error}", type="negative")
											return
										error = card_controller.replace_credit_card(cid)
										dlg.close()
										if error:
											ui.notify(f"Ersetzen fehlgeschlagen: {error}", type="negative")
										else:
											ui.notify("Kreditkarte gesperrt. Ihre Ersatzkarte erhalten Sie in den nächsten 5 Arbeitstagen per Post.", type="positive", timeout=6000)
									ui.button("Sperren & Ersetzen", on_click=do_block_replace_credit).props("color=negative unelevated")
							dlg.open()

						def handle_order_pin_credit(e) -> None:
							"""UI-Demoaktion: PIN bestellen (hier nur Notification).

							Args:
								e: NiceGUI-Event; wird hier nicht ausgewertet.
							"""
							ui.notify("Sie erhalten in den nächsten 5 Arbeitstagen einen neuen PIN.", type="positive", timeout=5000)

						credit_table.on("block_and_replace_credit", handle_block_and_replace_credit)
						credit_table.on("order_pin_credit", handle_order_pin_credit)

						credit_table.rows = [
							{
								"card_id": d["card_id"],
								"card_number": d["card_number"],
								"limit": f"{d['limit']:,.2f}",
								"balance": f"{d['balance']:,.2f}",
								"available": f"{d['available']:,.2f}",
								"billing_account": d["billing_account"],
								"last_billed": d["last_billed"],
								"status": d["status"],
							}
							for d in active_cards
						]

				# Gesperrte / Ersetzte Kreditkarten
				REPLACED_COLUMNS = [
					{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
					{"name": "limit", "label": "Limit (CHF)", "field": "limit", "align": "right"},
					{"name": "status", "label": "Status", "field": "status", "align": "left"},
				]

				with ui.card().classes("w-full"):
					ui.label("Gesperrte / Ersetzte Kreditkarten").classes("text-subtitle2 font-semibold mb-2")

					if not replaced_cards:
						ui.label("Keine gesperrten oder ersetzten Karten.").classes("text-gray-500 italic")
					else:
						replaced_table = ui.table(columns=REPLACED_COLUMNS, rows=[]).props("dense").classes("w-full credit-secondary-table")
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

			# === 2. ABRECHNUNGSKONTO FESTLEGEN (geschlossen) ===
			with ui.expansion("Abrechnungskonto festlegen", value=False).classes("w-full"):

				if not active_cards:
					ui.label("Keine aktiven Kreditkarten.").classes("text-gray-500 italic")
				else:
					card_options = {d["card_id"]: d["card_number"] for d in active_cards}

					result = account_controller.list_accounts(user_id)
					if isinstance(result, str):
						ui.notify(result, type="negative")
						account_options = {}
					else:
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

					billing_error_label = ui.label("").classes("text-red-600 mb-4 w-full")

					async def handle_set_billing_account() -> None:
						"""Setzt das Abrechnungskonto fuer eine Kreditkarte."""
						if not card_select.value or not account_select.value:
							billing_error_label.set_text("Bitte Kreditkarte und Konto auswählen.")
							ui.notify("Bitte Kreditkarte und Konto auswählen", type="warning")
							return

						with ui.dialog() as dlg, ui.card().classes("w-96"):
							ui.label("Abrechnungskonto festlegen").classes("text-subtitle1 font-semibold mb-3")
							with ui.card().classes("w-full mb-3").props("flat bordered"):
								ui.label(f"Kreditkarte: {card_options.get(card_select.value, '')}").classes("text-sm text-gray-700")
								ui.label(f"Konto: {account_options.get(account_select.value, '')}").classes("text-sm text-gray-600")
							with ui.row().classes("gap-4 mt-4 justify-end"):
								ui.button("Abbrechen", on_click=dlg.close).props("flat")
								def do_set_billing(cid=card_select.value, aid=account_select.value):
									error = card_controller.handle_set_billing_account(cid, aid)
									dlg.close()
									if error:
										billing_error_label.set_text(error)
										ui.notify(error, type="negative")
									else:
										billing_error_label.set_text("")
										ui.navigate.to("/cards")
								ui.button("Speichern", on_click=do_set_billing).props("color=primary unelevated")
						dlg.open()

					ui.button("Speichern", on_click=handle_set_billing_account).classes("w-full")

				# === WARNUNG: KEIN ABRECHNUNGSKONTO ===
				# Ohne Billing-Account kann `CreditCardBillingService` keine Monatsabrechnung ausfuehren.
				cards_without_billing = [
					c for c in active_cards
					if c.get("billing_account") in (None, "Nicht gesetzt")
				]

				if cards_without_billing:
					ui.separator().classes("my-4")
					with ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-400"):
						ui.label("⚠️ Kein Abrechnungskonto gesetzt").classes("text-subtitle2 font-semibold text-yellow-800 mb-2")
						ui.label(
							f"{len(cards_without_billing)} Kreditkarte(n) haben kein Abrechnungskonto. "
							"Der Monatsabschluss ist für diese Karten inaktiv."
						).classes("text-sm text-yellow-700")

			# === 3. NEUE KREDITKARTE BEANTRAGEN (geschlossen) ===
			with ui.expansion("Neue Kreditkarte beantragen", value=False).classes("w-full"):

				limit_input = ui.number(label="Gewünschtes Limit (CHF)", min=100, step=100).props("outlined")
				limit_input.classes("w-full mb-4")

				credit_card_error_label = ui.label("").classes("text-red-600 mb-4")

				async def handle_create_credit_card() -> None:
					"""Event-Handler: beantragt eine Kreditkarte."""
					if not limit_input.value:
						credit_card_error_label.set_text("Bitte geben Sie ein gewünschtes Limit an.")
						ui.notify("Bitte geben Sie ein gewünschtes Limit an.", type="warning")
						return

					payload = {
						"user_id": user_id,
						"desired_limit": limit_input.value or 1000,
					}

					with ui.dialog() as dlg, ui.card().classes("w-96"):
						ui.label("Kreditkarte beantragen").classes("text-subtitle1 font-semibold mb-3")
						with ui.card().classes("w-full mb-3").props("flat bordered"):
							ui.label(f"Gewünschtes Limit: {limit_input.value:,.2f} CHF").classes("text-sm text-gray-700")
						ui.label("Bei Genehmigung erhalten Sie Ihre Karte in den nächsten 5 Arbeitstagen per Post.").classes("text-sm text-gray-600")
						with ui.row().classes("gap-4 mt-4 justify-end"):
							ui.button("Abbrechen", on_click=dlg.close).props("flat")
							def do_apply(p=payload):
								error = card_controller.create_credit_card(p)
								dlg.close()
								if error:
									credit_card_error_label.set_text(error)
									ui.notify(error, type="negative")
								else:
									ui.notify("Kreditkartenantrag eingereicht. Bei Genehmigung erhalten Sie Ihre Karte in den nächsten 5 Arbeitstagen per Post.", type="positive", timeout=6000)
							ui.button("Antrag einreichen", on_click=do_apply).props("color=primary unelevated")
					dlg.open()

				ui.button("Beantragen", on_click=handle_create_credit_card).classes("w-full")

				# Offene Anträge
				if pending_cards:
					PENDING_COLUMNS = [
						{"name": "card_number", "label": "Kartennummer", "field": "card_number", "align": "left"},
						{"name": "limit", "label": "Gewünschtes Limit (CHF)", "field": "limit", "align": "right"},
						{"name": "status", "label": "Status", "field": "status", "align": "left"},
					]
					ui.separator().classes("my-4")
					ui.label("Meine Kreditkartenanträge").classes("text-subtitle2 font-semibold mb-2")
					pending_table = ui.table(columns=PENDING_COLUMNS, rows=[]).props("dense").classes("w-full credit-secondary-table")
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
		ui.button("Konten", icon="account_balance", on_click=lambda: ui.navigate.to("/accounts")).props("flat unelevated align=left").classes("w-full justify-start")
		ui.button("Karten", icon="credit_card", on_click=lambda: ui.navigate.to("/cards")).props("flat unelevated align=left").classes("w-full justify-start sidebar-active")


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
