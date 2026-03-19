# 💰 E-Banking-Budget-Tracker-Anwendung

## 🎯 Projektziel 

Das Ziel dieses Projekts ist die Entwicklung einer umfassenden Personal Finance & Banking Application. Die Anwendung dient als zentrales Hub für die Verwaltung privater Finanzen, die Überwachung von budgets und die Abwicklung täglicher Bankgeschäfte in einer intuitiven, digitalen Umgebung. 

## 📝 Application Requirements
### Problem
🚧 Describe the real-world problem your application solves. (Not HOW, but WHAT)

Im Alltag verlieren viele Menschen schnell den Überblick über ihre Finanzen, da tägliche Ausgaben oft auf manuellen Excellisten veteilt sind. Das fürhrt unbemerkten Budgetüberschreitungen, verfehlten Sparzielen und hohem Zeitaufwand bei alltäglichen Aufgaben, wie dem Abtippen von Rechnungen oder dem Verwalten von Bankkarten.

### Scenario
🚧 Describe when and how a user will use your application

Unsere App (Mazebank :D?) löst das Problem der unübersichtlichen Finanzen, indem der Nutzer eine einzige, zentrale Plattform für den Alltag bietet.

Ein Benutzer loggt sich in die App ein, um Rechnungen bequem alltägliche Ausgaben manuell zu erfassen und zu kategorisieren. Die Anwendung speichert die Transaktionen sicher, berechnet sofort die aktuellen Bilanzen und gleicht sie mit vordefinierten Monatsbudgets ab inklusive autoamtischer Warnungen bei Überschreitung. Darüber hinaus ermöglicht das System dem Nutzer, mit wenigen Klicks komplette Bankgeschäfte zu erledigen, wie das Sperren einer Kreditkarte im Notfall, das Herunterladen von Kontoauszügen oder die direkte Vereinbarung eines Termins für die Eröffnung eines 3a Vorsorgekontos.

## 📝 Application Requirements

---

### Problem

Viele Menschen verlieren im Alltag leicht den Überblick über ihre Einnahmen und Ausgaben. Die manuelle Erfassung ist mühsam, und bestehende Banking-Apps bieten oft nicht die nötige Flexibilität, um Budgets individuell zu verwalten, wiederkehrende Kosten zu automatisieren und gleichzeitig Konten oder Karten direkt zu managen. Das führt zu unbemerkten Budgetüberschreitungen und fehlender finanzieller Kontrolle.

---

### Scenario

Unsere Finanzverwaltungs-App löst dieses Problem, indem sie dem User eine zentrale Plattform bietet. Der User loggt sich ein und kann auf einem übersichtlichen Dashboard seine aktuelle finanzielle Lage prüfen. Er kann im Alltag neue Transaktionen mit wenigen Klicks erfassen und kategorisieren. Am Ende des Monats sieht er dank automatischer Warnungen sofort, ob er seine gesetzten Budgets eingehalten hat, und kann sich bei Bedarf Kontoauszüge als PDF generieren.

---

## User Stories

### 1. Transaktion manuell erfassen inkl. Kategorie
**Als User möchte ich meine Einnahmen und Ausgaben manuell hinzufügen und ihnen eine Kategorie zuweisen, damit ich meine Finanzstruktur überwachen und verstehen kann.**

**Description:** Die Anwendung speichert eine neue Einnahme oder Ausgabe mit Betrag, Datum und der zugewiesenen Kategorie.

**Inputs:** * `betrag` as `float`
* `typ` as `str` (e.g., "Einnahme" | "Ausgabe")
* `datum` as `date`
* `kategorie_id` as `int`
* `notiz` as `str` (optional)

**Outputs:** * gespeicherte Transaktion (internally: `Transaction`)

---

### 2. Transaktion bearbeiten oder löschen
**Als User möchte ich bestehende Einträge bearbeiten oder löschen, um Fehler zu korrigieren.**

**Description:** Der User ändert die Werte einer bestehenden Transaktion oder entfernt sie vollständig aus der Datenbank.

**Inputs:** * `transaktion_id` as `int`
* `aktion` as `edit | delete`
* `neue_werte` as `dict` (optional, bei edit)

**Outputs:** * `erfolgsstatus` as `bool`
* aktualisierte Transaktionsliste

---

### 3. Transaktionen filtern
**Als User möchte ich meine Einnahmen und Ausgaben nach Datum und Kategorie filtern, um gezielt nach älteren Zahlungen zu suchen.**

**Description:** Das System wendet Suchkriterien auf die Transaktionshistorie an und gibt eine gefilterte Liste zurück.

**Inputs:** * `start_datum` as `date` (optional)
* `end_datum` as `date` (optional)
* `kategorie_id` as `int` (optional)

**Outputs:** * gefilterte Transaktionsliste (internally: `list[Transaction]`)

---

### 4. Dashboard und Bilanz anzeigen
**Als User möchte ich ein Dashboard mit Diagrammen, meinem Gesamtsaldo und Summen für bestimmte Zeiträume sehen, um meine finanzielle Situation auf einen Blick erfassen zu können.**

**Description:** Das System berechnet die aktuelle Bilanz sowie die Einnahmen/Ausgaben für den gewählten Zeitraum und bereitet die Daten für das Charting auf.

**Inputs:** * `zeitraum_start` as `date`
* `zeitraum_ende` as `date`

**Outputs:** * `aktuelle_gesamtbilanz` as `float`
* `summe_einnahmen` as `float`
* `summe_ausgaben` as `float`
* `chart_daten` (internally: `list[ChartData]`)

---

### 5. Aktienticker anzeigen
**Als User möchte ich die vier wichtigsten Aktiensymbole auf der Startseite sehen, um über die Marktentwicklung informiert zu bleiben.**

**Description:** Die Applikation ruft Marktdaten der vier grössten Aktienwerte (z.B. über eine externe API) ab und zeigt diese an.

**Inputs:** none

**Outputs:** * `aktien_kurse` (internally: `list[StockTicker]`)

---

### 6. Monatliche Limits setzen
**Als User möchte ich monatliche Limits festlegen, damit ich automatisch gewarnt werde, wenn ich mein Budget überschreite.**

**Description:** Der User definiert ein Budget. Das System prüft aktuelle Ausgaben gegen dieses Budget und gibt bei Überschreitung ein Flag aus.

**Inputs:** * `limit_betrag` as `float`
* `kategorie_id` as `int` (optional für kategoriebasiertes Budget)
* `monat` as `int`
* `jahr` as `int`

**Outputs:** * `budget_status` (internally: `Budget`)
* `budget_ueberschritten` as `bool`

---

### 7. Wiederkehrende Zahlungen erfassen
**Als User möchte ich wiederkehrende Zahlungen für bestimmte Kategorien erstellen, um meine Fixkosten zu automatisieren.**

**Description:** Das System plant eine Transaktion, die sich basierend auf dem gewählten Intervall automatisch wiederholt.

**Inputs:** * `betrag` as `float`
* `kategorie_id` as `int`
* `intervall` as `str` ("monatlich" | "jährlich")
* `start_datum` as `date`

**Outputs:** * aktiver Dauerauftrag (internally: `RecurringTransaction`)

---

### 8. Konten eröffnen und schliessen
**Als User möchte ich Privat- und Sparkonten selbstständig eröffnen oder schliessen.**

**Description:** Der User ändert den Status (aktiv/inaktiv) eines bestehenden Kontos oder legt ein neues Konto an.

**Inputs:** * `konto_typ` as `str` ("Privatkonto" | "Sparkonto")
* `aktion` as `open | close`
* `konto_id` as `int` (nur relevant bei 'close')

**Outputs:** * `erfolgsstatus` as `bool`
* neues oder aktualisiertes Konto (internally: `Account`)

---

### 9. Karten verwalten
**Als User möchte ich neue Karten bestellen sowie meine Karten im Verlustfall sperren oder ersetzen lassen.**

**Description:** Der User kann eine neue Karte zu einem Konto bestellen oder den Status einer bestehenden Karte auf "gesperrt" setzen.

**Inputs:** * `konto_id` as `int`
* `karte_id` as `int` (optional, bei Sperrung/Ersatz)
* `aktion` as `order | block | replace`

**Outputs:** * `karten_status` as `str`
* aktualisierte Kartenliste (internally: `list[Card]`)

---

### 10. Inlandzahlungen erfassen
**Als User möchte ich Inlandszahlungen mit einer IBAN eingeben.**

**Description:** Der User gibt Empfängerdaten ein, und das System initiiert eine Überweisung vom gewählten Belastungskonto.

**Inputs:** * `ziel_iban` as `str`
* `betrag` as `float`
* `belastungs_konto_id` as `int`
* `verwendungszweck` as `str`

**Outputs:** * `zahlungs_status` as `str` ("pending" | "success")
* Zahlungsbeleg (internally: `Payment`)

---

### 11. Kontenumbuchung
**Als User möchte ich schnell Geld zwischen meinen Konten überweisen können.**

**Description:** Das System bucht einen Betrag von einem eigenen Konto sofort auf ein anderes eigenes Konto um.

**Inputs:** * `von_konto_id` as `int`
* `zu_konto_id` as `int`
* `betrag` as `float`

**Outputs:** * `umbuchung_erfolgreich` as `bool`
* aktualisierte Kontostände (internally: `list[Account]`)

---

### 12. Kontoauszüge generieren
**Als User möchte ich Kontoauszüge für bestimmte Zeiträume erstellen und einsehen.**

**Description:** Die Anwendung sammelt alle Transaktionen eines Kontos im gewählten Zeitraum und generiert daraus ein PDF.

**Inputs:** * `konto_id` as `int`
* `start_datum` as `date`
* `end_datum` as `date`

**Outputs:** * Kontoauszug als Datei (PDF)
* `datei_pfad` as `str`

---

### 13. Login
**Als User möchte ich mich mit meiner Vertragsnummer und meinem Passwort anmelden.**

**Description:** Das System gleicht die Anmeldedaten ab und erstellt bei Erfolg eine sichere Session für den User.

**Inputs:** * `vertragsnummer` as `str`
* `passwort` as `str`

**Outputs:** * `auth_token` as `str`
* `login_erfolgreich` as `bool`

---

### 14. Registrierung (Onboarding)
**Als User möchte ich bei Bedarf ein neues Benutzerkonto erstellen können.**

**Description:** Das System erfasst die Profildaten eines neuen Users, hasht das Passwort und legt den User in der Datenbank an.

**Inputs:** * `vorname` as `str`
* `nachname` as `str`
* `email` as `str`
* `passwort` as `str`

**Outputs:** * `neue_vertragsnummer` as `str`
* `registrierung_erfolgreich` as `bool`
* neues User-Profil (internally: `User`)

---

### Use cases

**Actors**
* **User:** Eine Privatperson, die ihre Finanzen verwalten, Zahlungen tätigen und ihr Budget überwachen möchte.

**Main Use Cases**
* **Konto & Sicherheit:** Registrieren (Onboarding), Login
* **Transaktionen verwalten:** Einnahmen und Ausgaben manuell erfassen, bearbeiten, löschen und filtern
* **Finanzen analysieren:** Dashboard mit Gesamtbilanz ansehen, Aktienticker verfolgen
* **Budgetierung & Planung:** Monatliche Budget-Limits setzen, wiederkehrende Zahlungen erfassen
* **Zahlungsverkehr:** Inlandzahlungen per IBAN tätigen, Geld zwischen eigenen Konten umbuchen, Kontoauszüge generieren
* **Konten- & Kartenmanagement:** Privat und Sparkonten eröffnen/schliessen, Karten bestellen/sperren/ersetzen
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





















