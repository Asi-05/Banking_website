# 💰 E-Banking-Budget-Tracker-Anwendung

## 🎯 Projektziel 

Das Ziel dieses Projekts ist die Entwicklung einer umfassenden Personal Finance & Banking Application. Die Anwendung dient als zentrales Hub für die Verwaltung privater Finanzen, die Überwachung von budgets und die Abwicklung täglicher Bankgeschäfte in einer intuitiven, digitalen Umgebung. 

## 📝 Application Requirements
### Problem
🚧 Describe the real-world problem your application solves. (Not HOW, but WHAT)

Im Alltag verlieren viele Menschen schnell den Überblick über ihre Finanzen, da tägliche Ausgaben, Sparkonten und die Altersvorsorge (Säule 3a) oft auf verschiedene Bank Apps oder manuellen Excellisten veteilt sind. Das fürhrt unbemerkten Budgetüberschreitungen, verfehlten Sparzielen und hohem Zeitaufwand bei alltäglichen Aufgaben, wie dem Abtippen von Rechnungen oder dem Verwalten von Bankkarten.

### Scenario
🚧 Describe when and how a user will use your application

Unsere App (Mazebank :D?) löst das Problem der unübersichtlichen Finanzen, indem der Nutzer eine einzige, zentrale Plattform für den Alltag bietet.

Ein Benutzer loggt sich in die App ein, um Rechnungen bequem per PDF Upload zu bezahlen oder alltägliche Ausgaben manuell zu erfassen und zu kategorisieren. Die Anwendung speichert die Transaktionen sicher, berechnet sofort die aktuellen Bilanzen und gleicht sie mit vordefinierten Monatsbudgets ab (inklusive autoamtischer Warnungen bei Überschreitung). Darüber hinaus ermöglicht das System dem Nutzer, mit wenigen Klicks komplette Bankgeschäfte zu erledigen, wie das Sperren einer Kreditkarte im Notfall, das Herunterladen von Kontoauszügen oder die direkte Vereinbarung eines Termins für die Eröffnung eines 3a Vorsorgekontos.

### 👤 User Stories
📝 Finanzverwaltung (Core Features)
* US1: Als User möchte ich meine Einnahmen und Ausgaben manuell erfassen können, um meine Finanzen lückenlos zu überwachen.
* US2: Als User möchte ich jeder Transaktion eine Kategorie zuweisen können, um die Struktur meiner Ausgaben zu verstehen.
* US3: Als User möchte ich bestehende Einträge nachträglich bearbeiten oder löschen können, um Fehler zu korrigieren.
* US4: Als User möchte ich meine Einnahmen und Ausgaben nach Datum und Kategorien filten können, um gezielt nach alten Zahlungen zu suchen.

📊 Dashboard & Analyse
* US5: Als User möchte ich ein Dashboard mit Charts sehen, damit ich meine Einnahmen und Ausgaben auf einem Blick sehen kann.
* US6: Als User möchte ich jederzeit meine aktuelle Gesamtbilanz einsehen können, um zu wissen, wie viel Budget mir noch Verfügbar steht.
* US7: Als User möchte ich Summen für bestimmte Zeiträume (z.B. aktueller Monat) abrufen können, um meine finanzielle Entwicklung zu sehen.
* (US8: Als User möchte ich die vier grössten Aktienticker direkt auf der Startseite sehen, um über Marktbewegungen informiert zu bleiben. )

💰 Budgetierung & Planung
* US9: Als User möchte ich monatliche Limits setzen können, damit ich automatisch gewarnt werde, wenn ich mein Budget überschreite.
* US10: Als User möchte ich wiederkehrende Zahlungen für definierte Kategorien erfassen können, um Fixkosten zu automatisieren.

🏦 Konten- & Kartenmanagement
* US11: Als User möchte ich Privat und Sparkonten selbständig eröffnen oder schliessen können.
* US12: Als User möchte ich neue Karten bestellen, sowie bei Karten Verlust sperren oder ersetzen können.
* US13: Als User möchte ich ein 3a Konto eröffnen können und direkt einen Beratungstermin vereinbaren können.

💸 Zahlungsverkehr & Dokumente
* US14: Als User möchte ich Inlandzahlungen per IBAN Eingabe oder durch PDF Upload erfassen.
* US15: Als User möchte ich Geld schnell zwischen meinen eigenen Konten umbuchen können.
* US16: Als User möchte ich für spezifische Zeiträume Kontoauszüge generieren und einsehen können.

🔐 Sicherheit & Onboarding
* US17: Als User möchte ich mich mit Vertragsnummer und Passwort anmelden können.
* US18: Als User möchte ich mich auf Wunsch ein neues Benutzerkonto erstellen können.


### Use cases
🚧 Name actors and briefly describe each use case. Ideally, a UML use case diagram specifies use cases and relationships.

### UC1: Transaktion manuell erfassen & kategorisieren
**Basiert auf:** US1, US2, US3 | **Akteur:** Registrierter User

**Hauptszenario (Happy Path):**
  1. Der User klickt auf den Button "Neue Transaktion erfassen".
  2. Das System öffnet ein Eingabeformular.
  3. Der User wählt den Transaktionstyp (Einnahme oder Ausgabe).
  4. Der User gibt Betrag, Datum und einen Beschreibungstext ein.
  5. Der User wählt aus einem Dropdown-Menü eine passende Kategorie (z.B. "Lebensmittel", "Miete").
  6. Der User klickt auf "Speichern".
  7. Das System speichert die Transaktion, schliesst das Formular und aktualisiert die Gesamtbilanz (US6) auf dem Dashboard.
**Alternative Szenarien / Ausnahmen:**
  * *Pflichtfelder fehlen:* Das System speichert den Eintrag nicht, markiert die fehlenden Felder rot und zeigt eine Fehlermeldung an.
  * *Nachträgliche Bearbeitung (US3):* Der User wählt eine bestehende Transaktion aus, ändert den Betrag und klickt auf "Aktualisieren". Das System überschreibt den alten Datensatz.

### UC2: Budget-Limit setzen und Warnung auslösen
**Basiert auf:** US9 | **Akteur:** Registrierter User, System

**Hauptszenario (Happy Path):**
  1. Der User navigiert zum Bereich "Budgetierung".
  2. Der User klickt bei einer bestimmten Kategorie auf "Limit setzen".
  3. Der User gibt einen maximalen monatlichen Betrag ein und speichert.
  4. Das System erfasst im Hintergrund eine neue Ausgabe in dieser Kategorie, die das gesetzte Limit überschreitet.
  5. Das System generiert sofort eine Push-Benachrichtigung und einen visuellen Warnhinweis im Dashboard.
**Alternative Szenarien / Ausnahmen:**
  * *Limit herabsetzen:* Der User setzt ein Limit, das bereits durch bestehende Ausgaben im aktuellen Monat überschritten ist. Das System warnt den User direkt bei der Eingabe darüber.

### UC3: Bankkarte bei Verlust sperren und ersetzen
**Basiert auf:** US12 | **Akteur:** Registrierter User

**Hauptszenario (Happy Path):**
  1. Der User navigiert zum Bereich "Kartenmanagement".
  2. Der User wählt die betroffene Karte aus und klickt auf "Karte sperren".
  3. Das System fragt nach dem Sperrgrund.
  4. Der User wählt "Verlust" und bestätigt die Sperrung mit einer Zwei-Faktor-Authentifizierung.
  5. Das System ändert den Status der Karte auf "Gesperrt" und blockiert alle weiteren Zahlungen.
  6. Das System bietet im Anschluss direkt die Option: "Neue Ersatzkarte bestellen".
  7. Der User bestätigt die Lieferadresse und bestellt den Ersatz.
**Alternative Szenarien / Ausnahmen:**
  * *Temporäre Sperrung:* Der User wählt "Karte temporär einfrieren" anstatt "Verlust". Die Karte wird deaktiviert, kann aber vom User jederzeit per Knopfdruck wieder entsperrt werden.

### UC4: Inlandzahlung per PDF-Upload erfassen
**Basiert auf:** US14 | **Akteur:** Registrierter User

**Hauptszenario (Happy Path):**
  1. Der User wählt im Zahlungsverkehr "Neue Zahlung" und klickt auf "PDF / Rechnung hochladen".
  2. Der User wählt eine PDF-Datei aus.
  3. Das System analysiert das Dokument (OCR) und extrahiert automatisch: IBAN, Empfängername, Betrag und Referenznummer.
  4. Das System präsentiert dem User ein vorausgefülltes Zahlungsformular zur Kontrolle.
  5. Der User prüft die Daten und klickt auf "Zahlung freigeben".
  6. Das System führt die Zahlung aus und zeigt eine Erfolgsmeldung.
**Alternative Szenarien / Ausnahmen:**
  * *Scan fehlgeschlagen:* Das System kann die IBAN nicht eindeutig lesen und fordert den User auf: "Bitte Daten manuell nachtragen."
  * *Fehlende Kontodeckung:* Das Saldo ist zu niedrig. Das System lehnt die Ausführung ab und schlägt eine Umbuchung von einem anderen Konto vor.

### UC5: Login mit Vertragsnummer und Passwort
**Basiert auf:** US17 | **Akteur:** Registrierter User

**Hauptszenario (Happy Path):**
  1. Der User öffnet die App/Webseite und sieht den Login-Screen.
  2. Der User gibt seine Vertragsnummer und sein Passwort ein.
  3. Der User klickt auf "Anmelden".
  4. Das System validiert die Zugangsdaten gegen die Datenbank.
  5. Die Daten sind korrekt. Das System leitet den User auf das gesicherte Dashboard weiter.
**Alternative Szenarien / Ausnahmen:**
  * *Falsches Passwort:* Das System verweigert den Zugriff und zeigt die verbleibenden Versuche an.
  * *Konto gesperrt:* Nach 3 Fehlversuchen sperrt das System den Zugang temporär und bietet den Prozess "Passwort vergessen" an.

### Wireframes/ Mockups
🚧 Add screenshots of the wireframe mockups you chose to implement.

## 🏛️ Architecture
🚧 Document the architecture components, relationships, and key design decisions.

### Software Architecture
🚧 Insert your UML class diagram(s). Split into multiple diagrams if needed.

#### Layers / components:

 * UI (NiceGUI pages/components, browser as thin client)
 * Application logic (controllers + domain/services)
 * Persistence (SQLite + ORM entities + repositories/queries)

#### Design decisions (examples):

 * Organize code using MVC:
   * Model: domain + ORM entities (e.g. models.py)
   * View: NiceGUI UI components/pages
   * Controller: event handlers and coordination logic between UI, services, and       persistence
 
 * Separate UI (app/main.py) from domain logic (e.g. pricing.py) and persistence     (e.g. models.py, db.py)
 * Use and interaction of modules to minimize dependencies, by minimizing            cohesion and maximizing coupling
 * Keep business rules testable without starting the UI

#### Design patterns used (examples):

 * MVC (Model–View–Controller)
 * Repository/DAO for database access (e.g. queries.py)
 * Strategy for business rules (e.g. discount calculation)
 * Adapter for external services (e.g. invoice generation backend)


## 🗄️ Database and ORM
🚧 Describe the database and your ORM entities. Ideally, a diagram documents the database and it is described together with the ORM entities.

ORM and Entities (example): In the database, order are stored in ... that are mapped an Order entity. The Order ↔ OrderItem relationship ... ensures that an Order has at least one OrderItem and an OrderItem always relates to an Order.

## ✅ Project Requirements
🚧 Requirements act as a contract: implement and demonstrate each point below.

Each app must meet the following criteria in order to be accepted (see also the official project guidelines PDF on Moodle):

1. Using NiceGUI for building an interactive web app
2. Data validation in the app
3. Using an ORM for database management

### 1. Browser-based App (NiceGUI)
🚧 In this section, document how your project fulfills each criterion.

Architecture note (per SS26 guidelines): the browser is a thin client; UI state + business logic live on the server-side NiceGUI app.

### 2. Data Validation
The application validates all user input to ensure data integrity and a smooth user experience. These checks prevent crashes and guide the user to provide correct input, matching the validation requirements described in the project guidelines.

### 3. Database Management
All relevant data is managed via an ORM (e.g. SQLModel or SQLAlchemy). For the pizza example this includes users, pizzas, and orders.

## ⚙️ Implementation
### Technology
 * Python 3.x
 * Environment: GitHub Codespaces
 * External libraries (e.g. NiceGUI, SQLAlchemy, Pydantic)

### 📂 Repository Structure

### How to run





















