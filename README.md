# 💰 E-Banking-Budget-Tracker-Anwendung

## 🎯 Projektziel
Das Ziel dieses Projekts ist die Entwicklung einer umfassenden Personal Finance & Banking Application. Die Anwendung dient als zentrales Hub für die Verwaltung privater Finanzen, die Überwachung von Budgets und die Abwicklung täglicher Bankgeschäfte in einer intuitiven, digitalen Umgebung.

## 📝 Application Requirements

---

### Problem

Viele Menschen verlieren im Alltag leicht den Überblick über ihre Einnahmen und Ausgaben. Die manuelle Erfassung ist mühsam, und bestehende Banking-Apps bieten oft nicht die nötige Flexibilität, um Budgets individuell zu verwalten, wiederkehrende Kosten zu automatisieren und gleichzeitig Konten oder Karten direkt zu managen. Das führt zu unbemerkten Budgetüberschreitungen und fehlender finanzieller Kontrolle.

---

### Scenario

Unsere Finanzverwaltungs-App Betterbank löst dieses Problem, indem sie dem User eine zentrale Plattform bietet. Der User loggt sich ein und kann auf einem übersichtlichen Dashboard seine aktuelle finanzielle Lage prüfen. Er kann im Alltag neue Transaktionen mit wenigen Klicks erfassen und kategorisieren. Am Ende des Monats sieht er dank automatischer Warnungen sofort, ob er seine gesetzten Budgets eingehalten hat, und kann sich bei Bedarf Kontoauszüge als PDF generieren.

---

## User Stories

### 1. Transaktion manuell erfassen inkl. Kategorie
**Als User möchte ich meine Einnahmen und Ausgaben manuell hinzufügen und ihnen eine Kategorie zuweisen, damit ich meine Finanzstruktur überwachen und verstehen kann.**

**Description:** Die Anwendung speichert eine neue Einnahme oder Ausgabe mit Betrag, Datum, der zugewiesenen Kategorie und dem belasteten Konto/der belasteten Karte.

**Inputs:** * `amount` as `float`
* `type` as `str` (e.g., "income" | "expense")
* `date` as `date`
* `category_id` as `int`
* `account_id` as `int` (optional, falls über Konto bezahlt)
* `card_id` as `int` (optional, falls über kontogebundene Debitkarte bezahlt)
* `creditcard_id` as `int` (optional, falls über unabhängige Kreditkarte bezahlt)
* `note` as `str` (optional)

**Validierungsregel:** Es muss genau eines der drei Belastungsfelder gesetzt sein (`account_id`, `card_id`, `creditcard_id`).

**Outputs:** * gespeicherte Transaktion (internally: `Transaction`)

---

### 2. Transaktion bearbeiten oder löschen
**Als User möchte ich bestehende Einträge bearbeiten oder löschen, um Fehler zu korrigieren.**

**Description:** Der User ändert die Werte einer bestehenden Transaktion oder entfernt sie vollständig aus der Datenbank.

**Inputs:** * `transaction_id` as `int`
* `action` as `str` ("edit" | "delete")
* `new_values` as `dict` (optional, bei edit)

**Outputs:** * `success` as `bool`
* aktualisierte Transaktionsliste

---

### 3. Transaktionen filtern
**Als User möchte ich meine Einnahmen und Ausgaben nach Datum und Kategorie filtern, um gezielt nach älteren Zahlungen zu suchen.**

**Description:** Das System wendet Suchkriterien auf die Transaktionshistorie an und gibt eine gefilterte Liste zurück.

**Inputs:** * `start_date` as `date` (optional)
* `end_date` as `date` (optional)
* `category_id` as `int` (optional)

**Outputs:** * gefilterte Transaktionsliste (internally: `list[Transaction]`)

---

### 4. Dashboard und Bilanz anzeigen
**Als User möchte ich ein Dashboard mit Diagrammen, meinem Gesamtsaldo und Summen für bestimmte Zeiträume sehen, um meine finanzielle Situation auf einen Blick erfassen zu können.**

**Description:** Das System berechnet die aktuelle Bilanz sowie die Einnahmen/Ausgaben für den gewählten Zeitraum und bereitet die Daten für das Charting auf.

**Inputs:** * `start_date` as `date`
* `end_date` as `date`

**Outputs:** * `total_balance` as `float`
* `total_income` as `float`
* `total_expenses` as `float`
* `chart_data` (internally: `list[ChartData]`)

---

### 5. Monatliche Limits setzen
**Als User möchte ich monatliche Limits festlegen, damit ich automatisch gewarnt werde, wenn ich mein Budget überschreite.**

**Description:** Der User definiert ein Budget. Das System prüft aktuelle Ausgaben gegen dieses Budget und gibt bei Überschreitung ein Flag aus.

**Inputs:** * `limit_amount` as `float`
* `category_id` as `int` (optional für kategoriebasiertes Budget)
* `month` as `int`
* `year` as `int`

**Outputs:** * `budget_status` (internally: `Budget`)
* `is_exceeded` as `bool`

---

### 6. Wiederkehrende Zahlungen erfassen
**Als User möchte ich wiederkehrende Zahlungen für bestimmte Kategorien erstellen, um meine Fixkosten zu automatisieren.**

**Description:** Das System plant eine Transaktion, die sich basierend auf dem gewählten Intervall automatisch wiederholt, das angegebene Konto belastet und den hinterlegten Zielempfänger per IBAN verwendet.

**Inputs:** * `amount` as `float`
* `category_id` as `int`
* `account_id` as `int`
* `target_iban` as `str`
* `interval` as `str` ("monthly" | "yearly")
* `start_date` as `date`

**Outputs:** * aktiver Dauerauftrag (internally: `RecurringTransaction`)

---

### 7. Konten eröffnen und schliessen
**Als User möchte ich Privat- und Sparkonten selbstständig eröffnen oder schliessen.**

**Description:** Der User ändert den Status (aktiv/inaktiv) eines bestehenden Kontos oder legt ein neues Konto an.

**Inputs:** * `account_type` as `str` ("private" | "savings")
* `status` as `str` ("open" | "close")
* `account_id` as `int` (nur relevant bei 'close')

**Outputs:** * `success` as `bool`
* neues oder aktualisiertes Konto (internally: `Account`)

---

### 8. Debitkarten verwalten
**Als User möchte ich neue Debitkarten bestellen sowie meine Debitkarten im Verlustfall sperren oder ersetzen lassen.**

**Description:** Der User kann eine neue Debitkarte für sein Privatkonto bestellen oder den Status einer bestehenden Debitkarte auf "gesperrt" setzen. 

**Inputs:** * `account_id` as `int`
* `card_id` as `int` (bei Sperrung/Ersatz)
* `action` as `str` ("order" | "block" | "replace")

**Outputs:** * `card_status` as `str`
* aktualisierte Kartenliste (internally: `list[Card]`)

---

### 9. Unabhängige Kreditkarten verwalten
**Als User möchte ich eine eigenständige Kreditkarte mit eigenem Kreditrahmen bestellen sowie verwalten (sperren/ersetzen), um Zahlungen unabhängig von meinem Kontostand abzuwickeln.**

**Description:** Der User beantragt eine Kreditkarte. Das System erstellt ein neues, unabhängiges Kreditkarten-Objekt mit einem festgelegten Limit. Der User kann Transaktionen direkt über diese Karte abwickeln, wodurch sich der genutzte Kreditrahmen (Saldo) verändert. Bei Verlust kann die Karte gesperrt werden.

**Inputs:** * `user_id` as `int`
* `desired_limit` as `float` (bei Neubestellung)
* `creditcard_id` as `int` (bei Sperrung/Ersatz)
* `action` as `str` ("order" | "block" | "replace")

**Outputs:** * `card_status` as `str`
* aktualisiertes Kreditkarten-Objekt (internally: `CreditCard`)

---

### 10. Inlandzahlungen erfassen
**Als User möchte ich Inlandszahlungen mit einer IBAN eingeben.**

**Description:** Der User gibt Empfängerdaten ein, und das System initiiert eine Überweisung vom gewählten Belastungskonto.

**Inputs:** * `target_iban` as `str`
* `amount` as `float`
* `source_account_id` as `int`
* `purpose` as `str`

**Outputs:** * `payment_status` as `str` ("pending" | "success")
* Zahlungsbeleg (internally: `Payment`)

---

### 11. Kontenumbuchung
**Als User möchte ich schnell Geld zwischen meinen Konten überweisen können.**

**Description:** Das System bucht einen Betrag von einem eigenen Konto sofort auf ein anderes eigenes Konto um.

**Inputs:** * `from_account_id` as `int`
* `to_account_id` as `int`
* `amount` as `float`

**Outputs:** * `success` as `bool`
* aktualisierte Kontostände (internally: `list[Account]`)

---

### 12. Kontoauszüge generieren
**Als User möchte ich Kontoauszüge für bestimmte Zeiträume erstellen und einsehen.**

**Description:** Die Anwendung sammelt alle Transaktionen eines Kontos im gewählten Zeitraum und generiert daraus ein PDF.

**Inputs:** * `account_id` as `int`
* `start_date` as `date`
* `end_date` as `date`

**Outputs:** * Kontoauszug als Datei (PDF)
* `file_path` as `str`

---

### 13. Login
**Als User möchte ich mich mit meiner Vertragsnummer und meinem Passwort anmelden.**

**Description:** Das System gleicht die Anmeldedaten ab und erstellt bei Erfolg eine sichere Session für den User.

**Inputs:** * `contract_number` as `str`
* `password` as `str`

**Outputs:** * `auth_token` as `str`
* `success` as `bool`

---

## Use cases

### Actors

* **User:** Eine Privatperson, die ihre Finanzen verwalten, Zahlungen tätigen und ihr Budget überwachen möchte.

### Main Use Cases

* **Konto & Sicherheit:** Login mit vordefinierten Usern
* **Transaktionen verwalten:** Einnahmen und Ausgaben manuell erfassen, bearbeiten, löschen und filtern
* **Finanzen analysieren:** Dashboard mit Gesamtbilanz ansehen
* **Budgetierung & Planung:** Monatliche Budget-Limits setzen, wiederkehrende Zahlungen erfassen
* **Zahlungsverkehr:** Inlandzahlungen per IBAN tätigen, Geld zwischen eigenen Konten umbuchen, Kontoauszüge generieren
* **Konten- & Kartenmanagement:** Privat und Sparkonten eröffnen/schliessen, Karten bestellen/sperren/ersetzen

### Use Case Diagramm

<img width="822" height="1007" alt="Use Case Diagram" src="https://github.com/user-attachments/assets/0c5d868f-a5eb-4cfb-ab1a-3a215e579f63" />


## Data Input & Output

### Dateneingabe

Die Anwendung erhält Benutzereingaben über die Weboberfläche. Alle Eingaben werden validiert, bevor sie über das ORM in der Datenbank gespeichert werden.

### Eingabefelder (Beispiel für Transaktion)

| Felder       | Code-Variable | Typ    | Pflicht | Beispiel       |
|--------------|---------------|--------|---------|----------------|
| Betrag       | `amount`      | float  | ja      | 45.50          |
| Kategorie ID | `category_id` | int    | ja      | 4 (Food)       |
| Konto ID     | `account_id`  | int    | ja      | 12             |
| Datum        | `date`        | date   | ja      | 2026-03-10     |
| Notiz        | `note`        | string | nein    | Mittagessen    |

### Beispiel Eingabe (JSON)

```json
{
  "amount": 45.50,
  "category_id": 4,
  "account_id": 12,
  "date": "2026-03-10",
  "note": "Lunch"
}
```

### Datenausgabe

Nach der Verarbeitung der gespeicherten Transaktionen generiert das System zusammengefasste Finanzinformationen, die im Dashboard angezeigt werden.
 
### Output Struktur
 
| Feld          | Typ    |
|---------------|--------|
| total_income  | float  |   
| total_expenses| float  |
| balance       | float  |

### Example Output (JSON)
 
```json
{
  "total_income": 3500,
  "total_expenses": 2100,
  "balance": 1400
}
```

Die Ausgabedaten werden verwendet, um Diagramme und finanzielle Zusammenfassungen im Dashboard zu erstellen.


### Wireframes/ Mockups
🚧 Add screenshots of the wireframe mockups you chose to implement.

## 🏛️ Architecture
🚧 Document the architecture components, relationships, and key design decisions.

### Software Architecture
🚧 Insert your UML class diagram(s). Split into multiple diagrams if needed.

![Klassendiagramm](https://github.com/user-attachments/assets/4e192496-3f35-4784-9189-8f6d4bd9072b)


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





















