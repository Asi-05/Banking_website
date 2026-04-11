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
* `from_account_id` as `int`
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

<img width="818" height="936" alt="Bildschirmfoto 2026-04-09 um 23 54 29" src="https://github.com/user-attachments/assets/0afa94cf-0bd9-4aad-a06b-31e196b26aaf" />


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

<img src="https://github.com/user-attachments/assets/72d3350d-d529-4a51-9c6d-41ba9c5af20a" width="300" />
<img src="https://github.com/user-attachments/assets/9595726a-eb0b-4fbf-8096-1cb519962654" width="300" />


<img src="https://github.com/user-attachments/assets/b14845a7-8c76-4f98-a227-ef7491b62e23" width="300" />
<img src="https://github.com/user-attachments/assets/329364dc-9c8f-4004-a8a7-319b1e3d00d7" width="300" />

## 🏛️ Architecture
🚧 Document the architecture components, relationships, and key design decisions.

### Software Architecture
## UML Klassendiagramm / ER Diagramm

![Klassediagramm updated](https://github.com/user-attachments/assets/3eb8d6c4-1b7b-40f9-a7a5-df589375feb0)


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

Unsere Applikation nutzt eine **SQLite**-Datenbank in Kombination mit **SQLModel** als Object-Relational Mapper (ORM). SQLModel vereint SQLAlchemy (für die Datenbankinteraktion) und Pydantic (für die Datenvalidierung) und ermöglicht uns eine saubere, typensichere Python-Entwicklung.

![Use Case Diagramm](pfad/zu/deinem/diagramm.png) 
*(Hinweis: Füge hier den Pfad zu deinem ER-Diagramm ein)*

### ORM und Entitäten

Unsere Datenbankarchitektur folgt einer strikten Trennung der Zuständigkeiten und nutzt relationale Muster, um Redundanzen zu vermeiden und die Datenintegrität sicherzustellen:

* **User ↔ Account / Cards:** Kunden werden in der `users`-Tabelle gespeichert und auf die `User`-Entität gemappt. Die `User` ↔ `Account` Beziehung (sowie zu `CreditCard` und `DebitCard`) ist eine 1:n-Beziehung. Das stellt sicher, dass ein User mehrere Konten und Karten besitzen kann, ein Konto/eine Karte aber immer exakt einem User zugeordnet ist. 

* **Bidirektionales Mapping:** In der Python-Logik nutzen wir das `back_populates`-Feature von SQLModel. Dadurch können wir bidirektional navigieren (z. B. von einem Konto direkt auf das `User`-Objekt zugreifen), während die Datenbankebene strikt bei einer Einbahnstraße über Foreign Keys (`user_id`) bleibt.

* **Budget ↔ Category:** Budgets werden auf die `Budget`-Entität gemappt. Ein harter `UniqueConstraint` in der Datenbank auf die Kombination `(user_id, month, year, category_id)` stellt sicher, dass ein User für einen bestimmten Monat und eine bestimmte Kategorie nicht versehentlich doppelte Budgets anlegen kann.

* **Die "is_a" Transaktions-Strategie:** Alle Geldbewegungen basieren auf der `Transaction`-Entität, welche die gemeinsamen Basisdaten (Betrag, Datum, Typ) speichert. Spezifische Zahlungsarten (wie `Transfer`, `Payment`, `RecurringTransaction`) erben *nicht* im Python-Code, sondern werden relational über Komposition abgebildet. Die `Transfer` ↔ `Transaction` Beziehung (1:1 über den Foreign Key `transaction_id`) stellt sicher, dass zielspezifische Daten (wie `target_iban`) sauber getrennt bleiben und die Haupttabelle keine leeren `NULL`-Spalten für nicht benötigte Felder ansammelt.

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





















