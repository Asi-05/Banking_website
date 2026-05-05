"""src.__main__

Diese Datei ist der **Programmeinstieg** der BetterBank-App.

Sie orchestriert den Start in groben Schritten:

1) Datenbank initialisieren (Engine/Tabellen/kleine Migrationen)
2) Demo-/Seed-Daten einspielen (idempotent: nur wenn noch nichts existiert)
3) NiceGUI initialisieren und Routen registrieren
4) Webserver starten

Architektur in einem Satz:

- Views (NiceGUI) -> Controller -> Services -> Repositories -> Datenbank.

Wichtig fuer Anfaenger:

- Imports der Views liegen *innerhalb* der Route-Funktionen. Das ist ein
	bewusstes Pattern, um beim Start keine UI-Module zu laden, bevor NiceGUI
	initialisiert ist, und um zirkulaere Abhaengigkeiten zu vermeiden.
"""

from src.data_access.db import create_db_and_tables
from src.data_access.seed import seed_database


# ===== HAUPTPROGRAMM =====


def main() -> None:
	"""Startet die BetterBank-Anwendung.

	Die Funktion ist bewusst "top level" und laeuft in einer festen Reihenfolge:
	- Zuerst wird die DB vorbereitet.
	- Danach werden Seed-Daten erzeugt (falls die DB noch leer ist).
	- Danach werden UI-Routen registriert.
	- Zuletzt startet der Webserver.
	"""

	# 1) Datenbank und Tabellen erstellen
	print("📦 Initialisiere Datenbank...")
	create_db_and_tables()

	# 2) Testdaten seeden (Kategorien, User, Konten)
	#    Hinweis: `seed_database()` ist so gebaut, dass es mehrfach ausgefuehrt
	#    werden kann, ohne jedes Mal Duplikate zu erzeugen.
	print("🌱 Seede Testdaten...")
	seed_database()

	# 3) NiceGUI initialisieren
	from nicegui import ui

	# 4) Routen definieren
	@ui.page("/")
	def index() -> None:
		"""
		Startseite: Login-Form (US13)
		Zeigt Anmelde-Interface mit Vertragsnummer und Passwort-Eingabe.
		"""
		# Styling (einmalig beim ersten Page Load)
		ui.colors(primary="#1976d2", secondary="#26a69a")
		
		from src.ui.views import login_view
		login_view.show()

	@ui.page("/dashboard")
	def dashboard() -> None:
		"""
		Dashboard (US4)
		Zeigt Gesamtbilanz, Summen und Diagramme für wählbaren Zeitraum.
		Geschützt: Leitet zu Login weiter falls nicht angemeldet.
		"""
		from src.ui.views import dashboard_view
		dashboard_view.show()

	@ui.page("/transactions")
	def transactions() -> None:
		"""
		Transaktionsverwaltung (US1, US2, US3)
		Erfassungsformular mit exactly-one-Regel für Belastungsquelle,
		Transaktionsliste mit Filtern (Datum, Kategorie),
		Edit/Delete-Funktionen pro Zeile.
		"""
		from src.ui.views import transaction_view
		transaction_view.show()

	@ui.page("/budget")
	def budget() -> None:
		"""
		Budget-Verwaltung (US5)
		Setzen von monatlichen Limits, optional pro Kategorie,
		Budget-Übersicht mit Status (OK / ÜBERSCHRITTEN).
		"""
		from src.ui.views import budget_view
		budget_view.show()

	@ui.page("/accounts")
	def accounts() -> None:
		"""
		Konten-Verwaltung (US7, US11)
		Konten eröffnen/schließen, Umbuchungen zwischen eigenen Konten,
		Konten-Übersicht mit IBAN, Typ, Saldo, Status.
		"""
		from src.ui.views import account_view
		account_view.show()

	@ui.page("/cards")
	def cards() -> None:
		"""
		Karten-Verwaltung (US8, US9)
		Debitkarten: Bestellen, Sperren, Ersetzen (max. 1 aktiv pro Konto),
		Kreditkarten: Beantragen (mit Limit), Sperren, Ersetzen,
		Zeige verfügbares Limit und genutzter Betrag.
		"""
		from src.ui.views import card_view
		card_view.show()

	# 5) App-Start
	print("🚀 Starte Betterbank Banking App...")
	print("   Öffne: http://localhost:8080/")
	# UI-Lokalisierung: Quasar (Frontend-Komponente unter NiceGUI) wird hier auf
	# Deutsch gesetzt. Das beeinflusst z.B. Wochentage/Monatsnamen in Datepickern.
	ui.add_head_html("""
	<script>
	document.addEventListener('DOMContentLoaded', function() {
	    setTimeout(function() {
	        if (window.Quasar && Quasar.lang) {
	            Quasar.lang.set({
	                isoName: 'de',
	                nativeName: 'Deutsch',
	                date: {
	                    days: ['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag'],
	                    daysShort: ['So','Mo','Di','Mi','Do','Fr','Sa'],
	                    months: ['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'],
	                    monthsShort: ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'],
	                    firstDayOfWeek: 1
	                }
	            });
	        }
	    }, 200);
	});
	</script>
	""", shared=True)
	ui.run(
		title="💰 BetterBank - E-Banking Finanzverwaltung",
		port=8080,
	)


if __name__ in {"__main__", "__mp_main__"}:
	main()
