# 💰 E-Banking-Budget-Tracker-Anwendung

## 🎯 Projektziel 

Das Ziel dieses Projekts ist die Entwicklung einer umfassenden Personal Finance & Banking Application. Die Anwendung dient als zentrales Hub für die Verwaltung privater Finanzen, die Überwachung von budgets und die Abwicklung täglicher Bankgeschäfte in einer intuitiven, digitalen Umgebung. 

## 📝 Application Requirements
### Problem
🚧 Describe the real-world problem your application solves. (Not HOW, but WHAT)

💡 Example: In a small local pizzeria, the staff writes orders and calculates totals by hand. This causes mistakes and inconsistent orders or discounts.

### Scenario
🚧 Describe when and how a user will use your application

💡 Example: PizzaRP solves the part of the problem where orders and totals are created by letting a user select items from a menu, validating the inputs, storing orders in a database, and automatically generating a correct invoice.

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





















