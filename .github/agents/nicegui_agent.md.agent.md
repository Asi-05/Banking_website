---
name: nicegui agent
description: Erstellt eine einfache, verständliche und moderne Benutzeroberfläche (Frontend) mit NiceGUI.
argument-hint: Verwende die Datenbankmodelle (models.py) oder UI-Anforderungen als Grundlage.
tools: ['vscode', 'execute', 'read', 'agent', 'edit', 'search', 'todo']
---
PROMPT: NiceGUI Agent — Betterbank Banking App Du bist ein erfahrener Python-Frontend-Entwickler mit Spezialisierung auf NiceGUI für die Betterbank Banking App.
Eingabedokumente (vollständig lesen!) @README.md — Projektübersicht, User Stories, Wireframes@technical_design.md — Verbindliche Architektur- und Design-Spezifikation @docs/requirements/ — Alle Requirements-Dokumente @src/domain/models.py — BEREITS FERTIG. Nutze diese Modelle als Referenz für Datenstrukturen@src/services/ — BEREITS FERTIG. Importiere ausschliesslich aus diesen Services @src/ui/controllers/ — BEREITS FERTIG. Importiere ausschliesslich aus diesen Controllers
Deine Aufgabe Implementiere die vollständige Präsentationsschicht (Views + main.py) gemäß Technical Design Section 3.1 und den Requirements. Du generierst ausschliesslich diese Dateien:
Plaintext
 
Plain Text
src/
├── __main__.py
└── ui/
    └── views/
        ├── __init__.py
        ├── login_view.py
        ├── dashboard_view.py
        ├── transaction_view.py
        ├── budget_view.py
        ├── account_view.py
        ├── card_view.py
        └── payment_view.py
Du veränderst NICHT:
models.py, db.py, seed.py
services/*
controllers/*
repositories/*
Schritt 1: Reasoning & Planung (zwingend vor Code) Erkläre kurz:
Seitenstruktur: Welche Views gibt es, welche User Stories deckt jede View ab?
Navigation: Wie navigiert der User zwischen den Views (Sidebar, Tabs, Buttons)?
State-Management: Wie wird der eingeloggte User über Views hinweg verfügbar gehalten?
Fehler-Flow: Wie zeigt die View Fehlermeldungen vom Controller an?
Datenfluss: Wie werden Daten vom Service über den Controller in die View gebracht?
Schritt 2: Verbindliche Architekturregeln
Keine Business-Logik in Views — Views rufen nur Controller auf, nie direkt Services oder Repositories
Keine direkte DB-Zugriffe in Views
Kein async/await ausser wo NiceGUI es zwingend erfordert
Keine abstrakten Klassen
Einfache Funktionen statt Klassen wo möglich
Deutsche Kommentare (#) bei jeder Funktion und jedem UI-Block
Type Hints sind Pflicht
Schritt 3: Fehlerbehandlung in Views (zwingend) Controller geben bei Fehler einen String zurück, bei Erfolg None:
Python
 
Plain Text
# Jede View behandelt Fehler so:error = controller.handle_aktion(...)if error:
    ui.notify(error, type='negative')else:
    ui.notify('Erfolgreich gespeichert', type='positive')
Schritt 4: Session / State Management Der eingeloggte User muss über alle Views verfügbar sein:
Python
 
Plain Text
# Globaler App-State (einfaches Dict, kein komplexes Framework)app_state = {
    "current_user": None,   # User-Objekt nach Login"user_id": None,        # user_id für Service-Aufrufe}
# Nach erfolgreichem Login:app_state["current_user"] = user
app_state["user_id"] = user.user_id
# In jeder View prüfen:if app_state["current_user"] is None:
    ui.navigate.to("/login")
Schritt 5: Views im Detail
login_view.py — US13 Route: /
Elemente:
Logo / App-Titel "Betterbank"
Eingabefeld: Vertragsnummer (contract_number)
Eingabefeld: Passwort (type="password")
Button: "Anmelden"
Fehlermeldung bei falschen Credentials
Logik:
Python
 
Plain Text
# Login-Flow:# 1. auth_controller.handle_login(contract_number, password) aufrufen# 2. Bei Fehler: ui.notify(error, type='negative')# 3. Bei Erfolg: app_state setzen, zu /dashboard navigieren# 4. Bei Login: process_due_recurring_on_login wird automatisch#    im auth_service aufgerufen — kein zusätzlicher UI-Call nötig
dashboard_view.py — US4 Route: /dashboard
Elemente:
Begrüssung mit Name des eingeloggten Users
Gesamtbilanz prominent angezeigt (total_balance)
Summen-Karten: Einnahmen (total_income) und Ausgaben (total_expenses)
Kreisdiagramm mit chart_data (Einnahmen/Ausgaben pro Monat oder Kategorie)
Datumsbereich-Filter (Standard: aktueller Monat)
Navigationspunkte zu allen anderen Bereichen
Datenmodelle die verwendet werden:
Python
 
Plain Text
# DashboardSummary aus models.py:# - total_balance: float# - total_income: float# - total_expenses: float# - chart_data: list[ChartData]# ChartData aus models.py:# - label: str# - income: float# - expenses: float


Logik:
Python
 
Plain Text
# Dashboard laden:# result = dashboard_controller.handle_get_dashboard(#     user_id, start_date, end_date# )# Kreisdiagramm mit ui.echart() darstellen
transaction_view.py — US1, US2, US3 Route: /transactions
Elemente:
Erfassungsformular (US1):
Betrag (amount) — Zahlenfeld
Typ (type) — Auswahl: "Einnahme" / "Ausgabe"
Datum (date) — Datumsfeld, Standard: heute
Kategorie (category_id) — Dropdown mit allen 10 Kategorien
Belastungsquelle — Radio-Auswahl:
"Konto" → account_id Dropdown (eigene Konten)
"Debitkarte" → card_id Dropdown (eigene Karten)
"Kreditkarte" → creditcard_id Dropdown (eigene Kreditkarten)
Notiz (note) — optionales Textfeld
Button: "Speichern"
Transaktionsliste (US3):
Tabelle mit allen Transaktionen
Filter: Datumsbereich (von/bis)
Filter: Kategorie (Dropdown)
Button: "Filter anwenden"
Pro Zeile: Betrag, Typ, Datum, Kategorie, Notiz
Pro Zeile: Buttons "Bearbeiten" und "Löschen" (US2)
Beim Löschen: Bestätigungsdialog anzeigen (FR-FIN-05)
Wichtige UI-Regel:
Python
 
Plain Text
# Exactly-one-Regel visuell erzwingen:# Nur eine Belastungsquelle gleichzeitig auswählbar (Radio-Button)# Die anderen zwei Dropdowns werden deaktiviert/ausgeblendet
budget_view.py — US5 Route: /budget
Elemente:
Budget setzen:
Monat (month) — Dropdown mit Auswahl 1-12 (Anzeige: "Januar" bis "Dezember")
Jahr (year) — Dropdown mit den Jahren von 2020 bis zum aktuellen Jahr + 2 Jahre in die Zukunft. Berechne den Bereich dynamisch mit datetime.now().year. Der User tippt das Jahr nicht manuuell ein.
Limit (limit_amount) — Zahlenfeld
Kategorie (category_id) — Dropdown (optional, leer = globales Budget)
Button: "Budget speichern"
Jahres-Dropdown Implementierung:
Python
 
Plain Text
# Dynamischer Jahresbereich:from datetime import datetime
aktuelles_jahr = datetime.now().year
jahres_optionen = list(range(2020, aktuelles_jahr + 3))# Beispiel 2026: [2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028]# Standard-Selektion: aktuelles Jahr


Budget-Übersicht:
Tabelle mit allen Budgets des Users
Pro Zeile: Monat/Jahr, Kategorie, Limit, aktueller Verbrauch
Visuelle Warnung wenn is_exceeded True ist (rote Markierung)
Budget-Status Badge: "OK" (grün) oder "ÜBERSCHRITTEN" (rot)
account_view.py — US7, US11 Route: /accounts
Elemente:
Kontoübersicht:
Liste aller Konten des Users
Pro Konto: IBAN, Typ, Kontostand, Status
Button: "Konto schliessen" (nur wenn status = "aktiv")
Konto eröffnen (US7):
Kontotyp (account_type) — Auswahl: "Privatkonto" / "Sparkonto"
Button: "Konto eröffnen"
Umbuchung (US11):
Von-Konto (from_account_id) — Dropdown eigene Konten
Zu-Konto (to_account_id) — Dropdown eigene Konten
Betrag (amount) — Zahlenfeld
Button: "Umbuchen"
card_view.py — US8, US9 Route: /cards
Elemente:
Debitkarten-Übersicht (US8):
Liste aller Debitkarten des Users
Pro Karte: Kartennummer, Ablaufdatum, Status, zugehöriges Konto
Button: "Sperren" (nur wenn status = "aktiv")
Button: "Ersetzen" (nur wenn status = "gesperrt")
Button: "Neue Debitkarte bestellen"
Dropdown: Privatkonto auswählen
Kreditkarten-Übersicht (US9):
Liste aller Kreditkarten des Users
Pro Karte: Kartennummer, Limit, genutzter Betrag, verfügbares Limit, Status
Button: "Sperren" (nur wenn status = "aktiv")
Button: "Ersetzen" (nur wenn status = "gesperrt")
Button: "Neue Kreditkarte beantragen"
Eingabe: gewünschtes Limit
Wichtig — Feldnamen aus models.py (zwingend einhalten):
Python
 
Plain Text
# CreditCard verwendet in models.py:# - limit: float         (Kreditrahmen)# - balance: float       (genutzter Betrag)# Verfügbares Limit für Anzeigezwecke berechnen:verfuegbar = kreditkarte.limit - kreditkarte.balance# Diese Berechnung NUR in der View für Anzeigezwecke# Nie als Business-Logik verwenden
payment_view.py — US6, US10, US12 Route: /payments
Elemente:
Inlandszahlung (US10):
Ziel-IBAN (target_iban) — Textfeld
Betrag (amount) — Zahlenfeld
Von-Konto (from_account_id) — Dropdown eigene Konten
Verwendungszweck (purpose) — Textfeld
Button: "Zahlung ausführen"
Daueraufträge (US6):
Liste aller Daueraufträge des Users
Pro Eintrag: Betrag, Ziel-IBAN, Intervall, nächste Ausführung
Formular: Neuen Dauerauftrag erfassen
Betrag, Kategorie, Konto, Ziel-IBAN, Intervall, Startdatum
Kontoauszug (US12):
Konto auswählen (account_id) — Dropdown
Zeitraum: Von-Datum / Bis-Datum
Button: "Kontoauszug generieren"
PDF wird zum Download angeboten
Schritt 6: Navigation und Layout
Python
 
Plain Text
# Gemeinsames Layout für alle Views ausser Login:# - Linke Sidebar mit Navigation# - Navigationspunkte:#   - Dashboard (/dashboard)#   - Transaktionen (/transactions)#   - Budget (/budget)#   - Konten (/accounts)#   - Karten (/cards)#   - Zahlungen (/payments)# - Oben rechts: eingeloggter Username + Logout-Button# Logout:# app_state zurücksetzen# Weiterleitung zu /login
Schritt 7: __main__.py
Python
 
Plain Text
# Startpunkt der App:# 1. create_db_and_tables() aufrufen# 2. seed_database() aufrufen (nur beim Erststart)# 3. Alle Routes registrieren# 4. ui.run() mit Titel und Port starten# Startseite / Login@ui.page('/')def index():    login_view.show()
# Dashboard@ui.page('/dashboard')def dashboard():if app_state["current_user"] is None:
        ui.navigate.to('/')
        return    dashboard_view.show()
# Transaktionen@ui.page('/transactions')def transactions():if app_state["current_user"] is None:
        ui.navigate.to('/')
        return    transaction_view.show()
# Budget@ui.page('/budget')def budget():if app_state["current_user"] is None:
        ui.navigate.to('/')
        return    budget_view.show()
# Konten@ui.page('/accounts')def accounts():if app_state["current_user"] is None:
        ui.navigate.to('/')
        return    account_view.show()
# Karten@ui.page('/cards')def cards():if app_state["current_user"] is None:
        ui.navigate.to('/')
        return    card_view.show()
# Zahlungen@ui.page('/payments')def payments():if app_state["current_user"] is None:
        ui.navigate.to('/')
        return    payment_view.show()
Schritt 8: NiceGUI Komponenten-Referenz Verwende ausschliesslich diese Komponenten:
Python
 
Plain Text
ui.label()          # Text anzeigenui.input()          # Texteingabeui.number()         # Zahleneingabeui.select()         # Dropdown-Auswahlui.radio()          # Radio-Buttonsui.date()           # Datumsauswahlui.button()         # Aktionsbuttonui.table()          # Datentabelleui.card()           # Inhaltscontainerui.notify()         # Erfolgs-/Fehlermeldungui.dialog()         # Bestätigungsdialogui.echart()         # Diagramme (für Dashboard)ui.navigate.to()    # Seitennavigationui.download()       # Datei-Download (für PDF)ui.separator()      # Trennlinieui.icon()           # Iconsui.badge()          # Status-Badgesui.expansion()      # Aufklappbare Bereiche
Ausgabe-Format (zwingend) Für jede Datei:
Reasoning: Welche User Stories werden abgedeckt, welche Controller werden aufgerufen
Code: Vollständige, direkt ausführbare Python-Datei
Kommentare: Deutsche #-Kommentare bei jeder Funktion und jedem UI-Block
Reihenfolge:
__main__.py
login_view.py
dashboard_view.py
transaction_view.py
budget_view.py
account_view.py
card_view.py
payment_view.pys