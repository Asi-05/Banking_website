"""src.__main__

Diese Datei ist der **Programmeinstieg** der BetterBank-App.

=== WAS PASSIERT BEIM APP-START? ===
Wenn die App gestartet wird (z.B. mit `python -m src`), wird diese Datei
ausgefuehrt. Sie orchestriert den Start in genau dieser Reihenfolge:

    1) Datenbank initialisieren (Tabellen erstellen, Migrationen)
    2) Demo-Daten einspielen (nur beim ersten Start, danach idempotent)
    3) NiceGUI-Routen registrieren (/,  /dashboard, /transactions, usw.)
    4) Webserver starten (Port 8080)

=== WARUM IST DIESE REIHENFOLGE WICHTIG? ===
    - DB muss ZUERST existieren, bevor Seeds eingespielt werden.
    - NiceGUI muss ZUERST importiert sein, bevor Routen registriert werden.
    - Der Webserver startet ZULETZT (blockiert bis zum Beenden der App).

=== WAS IST EINE "ROUTE"? ===
Eine Route ist eine URL, die NiceGUI verwaltet.
Wenn der Browser `http://localhost:8080/dashboard` aufruft, fuehrt NiceGUI
die Funktion `dashboard()` aus, die die Seite aufbaut.

    Route "/" → login_view.show()
    Route "/dashboard" → dashboard_view.show()
    Route "/transactions" → transaction_view.show()
    Route "/budget" → budget_view.show()
    Route "/accounts" → account_view.show()
    Route "/cards" → card_view.show()

=== WARUM SIND IMPORTS IN DEN ROUTE-FUNKTIONEN (INNEN)? ===
    # FALSCH (wuerde beim Modulstart importieren, bevor NiceGUI bereit ist):
    from src.ui.views import login_view   # ganz oben in der Datei

    # RICHTIG (importiert erst wenn die Route aufgerufen wird):
    @ui.page("/")
    def index():
        from src.ui.views import login_view   # HIER DRIN
        login_view.show()

    Grund: NiceGUI-Views duerften beim Modul-Import keine UI-Elemente
    erstellen (NiceGUI waere noch nicht fertig initialisiert).
    Lokale Imports loesen zirkulaere Abhaengigkeiten und Initialisierungsfehler.

=== WAS IST IDEMPOTENT? ===
    `seed_database()` ist "idempotent" = kann mehrfach aufgerufen werden,
    ohne doppelte Daten zu erzeugen. Es prueft immer: "Existiert das schon?"
    Wenn ja → nichts tun. Wenn nein → anlegen.

=== WAS IST `if __name__ in {"__main__", "__mp_main__"}:` ===
    `if __name__ == "__main__":` ist Standard-Python: Wird nur ausgefuehrt,
    wenn die Datei direkt gestartet wird (nicht importiert).
    `"__mp_main__"` ist NiceGUI-spezifisch: NiceGUI kann Subprozesse
    starten (fuer Live-Reload), die sich als `__mp_main__` identifizieren.
    Beide muessen `main()` aufrufen.

=== ARCHITEKTUR IN EINEM SATZ ===
    Views (NiceGUI) → Controller → Services → Repositories → Datenbank
"""

from src.data_access.db import create_db_and_tables
from src.data_access.seed import seed_database


def main() -> None:
    """Startet die BetterBank-Anwendung.

    Laeuft in fester Reihenfolge:
    1. DB vorbereiten (Tabellen erstellen)
    2. Seed-Daten sicherstellen (Demo-User, Kategorien, Konten)
    3. UI-Routen registrieren
    4. Webserver starten (blockiert)
    """

    # Schritt 1: Datenbanktabellen erstellen (falls noch nicht vorhanden).
    # Auch Migrations-Schritte (neue Spalten etc.) werden hier ausgefuehrt.
    print("📦 Initialisiere Datenbank...")
    create_db_and_tables()

    # Schritt 2: Demo-Daten einspielen.
    # `seed_database()` ist idempotent: Bei jedem Start wird geprueft, ob
    # Daten schon existieren. Nur fehlende Daten werden hinzugefuegt.
    print("🌱 Seede Testdaten...")
    seed_database()

    # Schritt 3: NiceGUI importieren und Routen registrieren.
    from nicegui import ui

    # Globales CSS: wird einmalig in allen Seiten geladen (shared=True).
    # Definiert: Sidebar-Farben, Header-Stil, Seitenhintergrund, Datepicker-Farben.
    ui.add_head_html("""
    <style>
    /* ===== BetterBank Design Theme ===== */

    /* Drawer: dunkelblau, volle Höhe */
    .q-drawer {
        background: #1a3c7e !important;
        border-right: none !important;
        top: 0 !important;
        z-index: 3000 !important;
    }
    /* ALLE Elemente im Drawer weiss */
    .q-drawer * { color: rgba(255,255,255,0.95) !important; }

    /* Hover-Effekt Sidebar-Buttons */
    .q-drawer .q-btn:hover {
        background: rgba(255,255,255,0.12) !important;
        border-radius: 8px !important;
    }
    /* Aktiver Sidebar-Eintrag */
    .sidebar-active {
        background: rgba(255,255,255,0.18) !important;
        border-radius: 8px !important;
    }
    /* Trennlinie in Sidebar */
    .q-drawer .q-separator {
        background: rgba(255,255,255,0.2) !important;
        opacity: 1 !important;
        border: none !important;
    }

    /* Header: weiss mit feinem Schatten, nur rechts vom Drawer */
    .q-header {
        background: white !important;
        box-shadow: 0 1px 4px rgba(26,60,126,0.10) !important;
        border-bottom: 1px solid #dde3ea !important;
        left: 300px !important;
    }
    /* BetterBank-Label im Header ausblenden (steht schon in der Sidebar) */
    .q-header .text-h5 { display: none !important; }
    /* Settings- und Logout-Buttons: kräftiges Dunkelblau */
    .q-header .q-btn { color: #1a3c7e !important; }
    .q-header .q-btn:hover {
        background: rgba(26,60,126,0.08) !important;
        border-radius: 8px !important;
    }

    /* Seitenhintergrund hellgrau */
    .q-page-container, .q-page { background: #f0f4f8; }

    /* Datepicker: Header und aktiver Tag im neuen Blau */
    .q-date__header { background: #1a3c7e !important; }
    .q-date__today .q-btn { color: #1a3c7e !important; }
    .q-date__calendar-item--active .q-btn {
        background: #1a3c7e !important;
        color: white !important;
    }

    /* ===== Einheitliche Tabellen-Abstände für alle Seiten ===== */
    .q-table th {
        padding: 10px 16px !important;
        font-weight: 600 !important;
        background: #f8fafc !important;
        color: #374151 !important;
        border-bottom: 2px solid #e5e7eb !important;
    }
    .q-table td {
        padding: 10px 16px !important;
        border-bottom: 1px solid #f0f4f8 !important;
    }
    .q-table tbody tr:last-child td {
        border-bottom: none !important;
    }
    .q-table tbody tr:hover td {
        background: rgba(26, 60, 126, 0.04) !important;
    }
    </style>
    """, shared=True)

    # Route "/": Login-Seite (Startseite der App).
    # `ui.colors(...)` setzt das Farbschema fuer Quasar-Komponenten (NiceGUI-Backend).
    @ui.page("/")
    def index() -> None:
        """Startseite: Login-Formular (US13).

        Zeigt Anmelde-Interface mit Vertragsnummer und Passwort-Eingabe.
        Kein Login-Guard hier (diese Seite MUSS ohne Login erreichbar sein).
        """
        ui.colors(primary="#1a3c7e", secondary="#26a69a")
        # Import HIER (nicht oben): NiceGUI ist jetzt bereit, und zirkulaere Imports werden vermieden.
        from src.ui.views import login_view
        login_view.show()

    # Route "/dashboard": Hauptseite nach dem Login.
    @ui.page("/dashboard")
    def dashboard() -> None:
        """Dashboard (US4).

        Zeigt Gesamtbilanz, Einnahmen/Ausgaben und Diagramme.
        Geschuetzt: Leitet zu Login weiter falls nicht angemeldet (Login-Guard in der View).
        """
        ui.colors(primary="#1a3c7e", secondary="#26a69a")
        from src.ui.views import dashboard_view
        dashboard_view.show()

    # Route "/transactions": Zahlungen, Dauerauftraege, Kontoauszug.
    @ui.page("/transactions")
    def transactions() -> None:
        """Transaktionsverwaltung (US1, US2, US3).

        Erfassungsformular fuer Zahlungen, Dauerauftraege und Kontoauszuege.
        Geschuetzt durch Login-Guard.
        """
        ui.colors(primary="#1a3c7e", secondary="#26a69a")
        from src.ui.views import transaction_view
        transaction_view.show()

    # Route "/budget": Monatsbudgets verwalten.
    @ui.page("/budget")
    def budget() -> None:
        """Budget-Verwaltung (US5).

        Monatliche Ausgabenlimits setzen (optional pro Kategorie).
        Geschuetzt durch Login-Guard.
        """
        ui.colors(primary="#1a3c7e", secondary="#26a69a")
        from src.ui.views import budget_view
        budget_view.show()

    # Route "/accounts": Konten eröffnen, schliessen, anzeigen.
    @ui.page("/accounts")
    def accounts() -> None:
        """Konten-Verwaltung (US7, US11).

        Konten eroeffnen/schliessen, Kontenstand anzeigen.
        Geschuetzt durch Login-Guard.
        """
        ui.colors(primary="#1a3c7e", secondary="#26a69a")
        from src.ui.views import account_view
        account_view.show()

    # Route "/cards": Debit- und Kreditkarten verwalten.
    @ui.page("/cards")
    def cards() -> None:
        """Karten-Verwaltung (US8, US9).

        Debitkarten bestellen/sperren/ersetzen, Kreditkarten beantragen/verwalten.
        Geschuetzt durch Login-Guard.
        """
        ui.colors(primary="#1a3c7e", secondary="#26a69a")
        from src.ui.views import card_view
        card_view.show()

    # Schritt 4: Quasar-Lokalisierung auf Deutsch (fuer Datepicker-Beschriftungen).
    # Dieses Script wird im Browser ausgefuehrt, NACHDEM alle Komponenten geladen sind.
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

    print("🚀 Starte Betterbank Banking App...")
    print("   Öffne: http://localhost:8080/")

    # Schritt 4: Webserver starten.
    # `ui.run()` blockiert bis die App beendet wird (Ctrl+C).
    ui.run(
        title="💰 BetterBank - E-Banking Finanzverwaltung",
        port=8080,
    )


# Einstiegspunkt: wird ausgefuehrt wenn man `python -m src` oder `python src/__main__.py` aufruft.
# `__mp_main__` ist NiceGUI-spezifisch (fuer den Reload-Mechanismus).
if __name__ in {"__main__", "__mp_main__"}:
    main()
