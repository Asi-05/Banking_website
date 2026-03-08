# 💰 E-Banking-Budget-Tracker-Anwendung

## 🎯 Projektziel 

Wir migrieren unseren ursprünglichen CLI Budget Tracker zu einer vollwertigen, browserbasierten E-Banking Anwendung. Die App ermöglicht es Nutzern , Finanzen in einer moderner Weboberfläche zu verwalten, konten zu eröffnen und automatisierte Zahlungen zu tätigen. (Wird noch ergänzt!)

## 📝 Application Requirements
### Problem
🚧 Describe the real-world problem your application solves. (Not HOW, but WHAT)

💡 Example: In a small local pizzeria, the staff writes orders and calculates totals by hand. This causes mistakes and inconsistent orders or discounts.

### Scenario
🚧 Describe when and how a user will use your application

💡 Example: PizzaRP solves the part of the problem where orders and totals are created by letting a user select items from a menu, validating the inputs, storing orders in a database, and automatically generating a correct invoice.

### 👤 User Stories

### Use cases
🚧 Name actors and briefly describe each use case. Ideally, a UML use case diagram specifies use cases and relationships.

### Wireframes/ Mockups
🚧 Add screenshots of the wireframe mockups you chose to implement.

## 🏛️ Architecture
🚧 Document the architecture components, relationships, and key design decisions.

### Software Architecture
🚧 Insert your UML class diagram(s). Split into multiple diagrams if needed.

Layers / components:

UI (NiceGUI pages/components, browser as thin client)
Application logic (controllers + domain/services)
Persistence (SQLite + ORM entities + repositories/queries)
Design decisions (examples):

Organize code using MVC:
Model: domain + ORM entities (e.g. models.py)
View: NiceGUI UI components/pages
Controller: event handlers and coordination logic between UI, services, and persistence
Separate UI (app/main.py) from domain logic (e.g. pricing.py) and persistence (e.g. models.py, db.py)
Use and interaction of modules to minimize dependencies, by minimizing cohesion and maximizing coupling
Keep business rules testable without starting the UI
Design patterns used (examples):

MVC (Model–View–Controller)
Repository/DAO for database access (e.g. queries.py)
Strategy for business rules (e.g. discount calculation)
Adapter for external services (e.g. invoice generation backend)














