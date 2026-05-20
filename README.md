# 💰 E-Banking-Budget-Tracker-Anwendung

## 🎯 Projektziel
Das Ziel dieses Projekts ist die Entwicklung einer umfassenden Personal Finance & Banking Application. Die Anwendung dient als zentrales Hub für die Verwaltung privater Finanzen, die Überwachung von Budgets und die Abwicklung täglicher Bankgeschäfte in einer intuitiven, digitalen Umgebung.

## 📝 Application Requirements

---

### Problem

Die Verwaltung privater Finanzen ist heutzutage stark fragmentiert. Nutzer müssen im Alltag oft zwischen traditionellen Banking-Apps für Transaktionen und separaten Tools oder Excel-Listen für die Budgetierung wechseln. Diese mangelnde Integration macht die finanzielle Übersicht mühsam, fehleranfällig und zeitaufwendig. Klassische Bank-Anwendungen zeigen primär historische Kontobewegungen, bieten aber nicht die nötige Flexibilität für proaktives Budget-Management oder die Automatisierung wiederkehrender Kosten. In der Folge entsteht ein reaktives Finanzverhalten, das häufig zu unbemerkten Budgetüberschreitungen und verfehlten Sparzielen führt.

---

### Scenario

Unsere BetterBank löst dieses Problem, indem sie dem User eine zentrale Plattform bietet. Der User loggt sich ein und kann auf einem übersichtlichen Dashboard seine aktuelle finanzielle Lage prüfen. Er kann im Alltag neue Transaktionen mit wenigen Klicks erfassen und kategorisieren. Am Ende des Monats sieht er dank automatischer Warnungen, ob er seine gesetzten Budgets eingehalten hat, und kann sich bei Bedarf Kontoauszüge als PDF generieren.

---

## User Stories

### 1. Transaktion manuell erfassen inkl. Kategorie
**Als User möchte ich meine Transaktionen manuell erfassen und ihnen eine Kategorie zuweisen, damit ich meine Finanzen sauber nachverfolgen kann.**

**Description:** Die Anwendung speichert eine Einnahme oder Ausgabe mit Betrag, Datum, der zugewiesenen Kategorie und dem belasteten Konto/der belasteten Karte.

**Inputs:** * `amount` as `float`
* `type` as `str` (e.g. "income" | "expense")
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

**Description:** Der User ändert die Werte einer bestehenden Transaktion oder entfernt sie vollständig aus der Datenbank. Im Code sind Bearbeiten und Löschen als separate Aktionen umgesetzt.

**Inputs:** * `transaction_id` as `int`
* `new_values` as `dict` (optional, bei edit)
* `confirm` as `bool` (bei delete)

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

**Description:** Das System berechnet das aktuelle Gesamtvermögen aus allen Konten des Users sowie die Einnahmen/Ausgaben für den gewählten Zeitraum und bereitet die Daten für das Charting auf. Die Diagrammdaten werden monatlich aggregiert.

**Inputs:** * `start_date` as `date`
* `end_date` as `date`

**Outputs:** * `total_balance` as `float`
* `total_income` as `float`
* `total_expenses` as `float`
* `chart_data` (internally: `list[ChartData]`)

---

### 5. Monatliche Limits setzen
**Als User möchte ich monatliche Budget-Limits für einen bestimmten Monat und ein Jahr festlegen, damit ich automatisch gewarnt werde, wenn ich mein Budget überschreite.**

**Description:** Der User definiert ein Budget für einen bestimmten Monat und ein Jahr. Das System prüft aktuelle Ausgaben gegen dieses Budget und gibt bei Überschreitung ein Flag aus.

**Inputs:** * `limit_amount` as `float`
* `category_id` as `int` (optional für kategoriebasiertes Budget)
* `month` as `int`
* `year` as `int`

**Outputs:** * `budget_status` (internally: `Budget`)
* `is_exceeded` as `bool`

---

### 6. Wiederkehrende Zahlungen erfassen
**Als User möchte ich wiederkehrende Zahlungen für bestimmte Kategorien erstellen, um meine Fixkosten zu automatisieren.**

**Description:** Das System plant eine Transaktion, die sich basierend auf dem gewählten Intervall automatisch wiederholt, das angegebene Konto belastet und den hinterlegten Zielempfänger per IBAN verwendet. Ein optionales Enddatum kann gesetzt werden.

**Inputs:** * `amount` as `float`
* `category_id` as `int`
* `account_id` as `int`
* `target_iban` as `str`
* `interval` as `str` ("monthly" | "yearly")
* `start_date` as `date`
* `end_date` as `date` (optional)

**Outputs:** * aktiver Dauerauftrag (internally: `RecurringTransaction`)

---

### 7. Konten eröffnen und schliessen
**Als User möchte ich Privat- und Sparkonten selbstständig eröffnen oder schliessen.**

**Description:** Der User legt ein neues Konto an oder schliesst ein bestehendes Konto. Geschlossene Konten erhalten den Status `geschlossen`. Das schliessen von einem Konto geht nur bei einem Saldo von 0 CHF.

**Inputs:** * `account_type` as `str` ("privat" | "spar")
* `account_id` as `int` (nur relevant bei 'close')
* `iban` as `str` (optional, bei Neueröffnung)
* `balance` as `float` (optional, bei Neueröffnung)

**Outputs:** * `success` as `bool`
* neues oder aktualisiertes Konto (internally: `Account`)

---

### 8. Debitkarten verwalten
**Als User möchte ich neue Debitkarten bestellen sowie meine Debitkarten im Verlustfall sperren und ersetzen lassen.**

**Description:** Der User kann eine neue Debitkarte für sein Privatkonto bestellen und ersetzen. 

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
* `category_id` as `int`
* `purpose` as `str`

**Outputs:** * `payment_status` as `str` ("success")
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

**Description:** Das System gleicht die Anmeldedaten ab und erstellt bei Erfolg eine sichere Session für den User. Beim Login werden zusätzlich fällige Daueraufträge und Kreditkarten-Monatsabrechnungen verarbeitet.

**Inputs:** * `contract_number` as `str`
* `password` as `str`

**Outputs:** * `auth_token` as `str`
* `success` as `bool`
* `user_id` as `int`
* `executed_recurring` as `int`
* `billed_cards` as `int`

---

### 14. Kreditkarte monatlich abrechnen
**Als User möchte ich meine Kreditkarte am Ende des Monats automatisch abrechnen lassen, damit mein Kreditrahmen wieder auf 0 zurückgesetzt wird und die Abbuchung als Ausgabe-Transaktion auf meinem Abrechnungskonto verbucht wird.**

**Description:** Das System verarbeitet fällige Kreditkarten-Abrechnungen. Für jede aktive Kreditkarte mit Saldo > 0 und verknüpftem Abrechnungskonto wird automatisch eine Expense-Transaktion erstellt, die den Saldo als Betrag vom Abrechnungskonto abbucht und den Kreditkarten-Saldo wird auf 0 zurückgesetzt.

**Inputs:** * `user_id` as `int`
* `reference_date` as `date` (optional, default: heute)

**Outputs:** * `billed_cards` as `int` (Anzahl abgerechneter Karten)
* erstellte Transaktionen (internally: `list[Transaction]`)
* aktualisierte Kreditkarten (internally: `list[CreditCard]` mit Saldo = 0)

---

## Use cases

### Actors

* **User:** Eine Privatperson, die ihre Finanzen verwalten, Zahlungen tätigen und ihr Budget überwachen möchte.

### Main Use Cases

* **Konto & Sicherheit:** Login mit vordefinierten Usern
* **Transaktionen verwalten:** Transaktionen manuell erfassen, bearbeiten, löschen und filtern
* **Finanzen analysieren:** Dashboard mit Gesamtvermögen und Zeitraum-Summen ansehen
* **Budgetierung & Planung:** Monatliche Budget-Limits setzen und wiederkehrende Zahlungen erfassen
* **Zahlungsverkehr:** Inlandzahlungen per IBAN tätigen, Geld zwischen eigenen Konten umbuchen und Kontoauszüge generieren
* **Konten- & Kartenmanagement:** Privat- und Sparkonten eröffnen oder schliessen sowie Karten bestellen, sperren und ersetzen

### Use Case Diagramm

<img width="818" height="936" alt="Bildschirmfoto 2026-04-09 um 23 54 29" src="https://github.com/user-attachments/assets/0afa94cf-0bd9-4aad-a06b-31e196b26aaf" />


## Data Input & Output

### Dateneingabe

Die Anwendung erhält Benutzereingaben über die Weboberfläche. Alle Eingaben werden validiert, bevor sie über das ORM in der Datenbank gespeichert werden.

### Eingabefelder (Beispiel für Transaktion)

| Felder       | Code-Variable | Typ    | Pflicht | Beispiel       |
|--------------|---------------|--------|---------|----------------|
| Betrag       | `amount`      | float  | ja      | 45.50          |
| Typ          | `type`        | string | ja      | expense        |
| Kategorie ID | `category_id` | int    | ja      | 6 (Freizeit)   |
| Konto ID     | `account_id`  | int    | nein    | 12             |
| Debitkarte ID | `card_id`    | int    | nein    | 7              |
| Kreditkarte ID | `creditcard_id` | int | nein    | 3              |
| Datum        | `date`        | date   | nein    | 2026-03-10     |
| Notiz        | `note`        | string | nein    | Ausgang        |

### Beispiel Eingabe (JSON)

```json
{
  "amount": 45.50,
  "type": "expense",
  "category_id": 6,
  "account_id": 12,
  "date": "2026-03-10",
  "note": "Ausgang"
}
```

Hinweis: Genau eine Belastungsquelle muss gesetzt sein (`account_id`, `card_id` oder `creditcard_id`). Wenn kein Datum übergeben wird, verwendet das System automatisch das aktuelle Datum.

### Datenausgabe

Nach der Verarbeitung der gespeicherten Transaktionen generiert das System zusammengefasste Finanzinformationen, die im Dashboard angezeigt werden.
 
### Output Struktur
 
| Feld          | Typ    |
|---------------|--------|
| total_balance | float  |
| total_income  | float  |
| total_expenses| float  |
| chart_data    | list[ChartData] |

### Example Output (JSON)
 
```json
{
  "total_balance": 1400,
  "total_income": 3500,
  "total_expenses": 2100,
  "chart_data": [
    {
      "label": "2026-03",
      "income": 3500,
      "expenses": 2100
    }
  ]
}
```

Die Ausgabedaten werden verwendet, um Diagramme und finanzielle Zusammenfassungen im Dashboard zu erstellen. `total_balance` entspricht dem aktuellen Kontostand aller Konten des Users, `total_income` und `total_expenses` beziehen sich auf den gewählten Zeitraum.


### Wireframes/ Mockups

<img src="https://github.com/user-attachments/assets/72d3350d-d529-4a51-9c6d-41ba9c5af20a" width="300" />
<img src="https://github.com/user-attachments/assets/b14845a7-8c76-4f98-a227-ef7491b62e23" width="300" />


<img src="https://github.com/user-attachments/assets/9595726a-eb0b-4fbf-8096-1cb519962654" width="300" />
<img src="https://github.com/user-attachments/assets/329364dc-9c8f-4004-a8a7-319b1e3d00d7" width="300" />


## 🏛️ Architecture

## Programm Struktur

```text
BetterBank/
├── .github/                 # GitHub-Workflows
├── .venv/                   # lokale virtuelle Umgebung (optional)
├── .vscode/                 # Editor-Einstellungen (optional)
├── .pytest_cache/           # pytest cache
├── main.py                  # optionaler Top-Level-Runner
├── pyproject.toml           # Projekt-Konfiguration
├── requirements/            # ergänzende requirement-notes
├── requirements.txt         # Verwendete Bibliotheken
├── technical_design.md      # Design-/Architekturnotizen
├── README.md                # Zentrale Projektdokumentation
├── betterbank.db            # lokale SQLite DB (Entwicklung)
├── statements/              # generierte Kontoauszüge (PDF)
├── tests/                   # Pytest-Dateien zur Qualitätssicherung
└── src/                     # Der gesamte Quellcode der Anwendung
  ├── __init__.py
  ├── __main__.py         # STARTPUNKT: Initialisiert NiceGUI (ui.run())
  ├── utils/              # HILFSFUNKTIONEN
  │   ├── __init__.py
  │   ├── validators.py   # IBAN-, Passwort-, Datums- und Feldvalidierung
  │   └── formatters.py   # Hilfsfunktionen für Anzeigeformate (CHF, Datum, Typ)
  ├── domain/             # DOMÄNENSCHICHT: Business-Objekte (Models)
  │   ├── __init__.py
  │   └── models.py       # SQLModel-Entitäten (User, Account, Transaction, ...)
  ├── data_access/        # PERSISTENZSCHICHT: Datenbank & Repositories
  │   ├── __init__.py
  │   ├── db.py           # Engine, create_all und Session-Provider
  │   ├── seed.py         # Skript für Test-/Demo-Daten
  │   └── repositories/   # CRUD/Query-Operationen pro Domäne
  │       ├── __init__.py
  │       ├── account_repository.py
  │       ├── budget_repository.py
  │       ├── card_repository.py
  │       ├── category_repository.py
  │       ├── payment_repository.py
  │       ├── recurring_repository.py
  │       ├── transaction_repository.py
  │       └── user_repository.py
  ├── services/           # ANWENDUNGSLOGIK: Service-Schicht (Business-Regeln)
  │   ├── __init__.py
  │   ├── account_service.py
  │   ├── auth_service.py
  │   ├── budget_service.py
  │   ├── card_service.py
  │   ├── category_service.py
  │   ├── creditcard_billing_service.py
  │   ├── dashboard_service.py
  │   ├── payment_service.py
  │   ├── recurring_service.py
  │   ├── transaction_service.py
  │   └── user_service.py
  └── ui/                 # PRÄSENTATIONSSCHICHT: NiceGUI-Frontend
    ├── __init__.py
    ├── app_state.py
    ├── controllers/    # Orchestrierung / Controller-Adapter
    │   ├── __init__.py
    │   ├── account_controller.py
    │   ├── auth_controller.py
    │   ├── budget_controller.py
    │   ├── card_controller.py
    │   ├── category_controller.py
    │   ├── dashboard_controller.py
    │   ├── payment_controller.py
    │   ├── recurring_controller.py
    │   ├── transaction_controller.py
    │   └── user_controller.py
    └── views/          # NiceGUI-Seiten (UI-Komponenten)
      ├── __init__.py
      ├── login_view.py
      ├── dashboard_view.py
      ├── transaction_view.py
      ├── budget_view.py
      ├── account_view.py
      └── card_view.py
```

### Software Architecture
## UML Klassendiagramm / ER Diagramm

<img width="5600" height="1875" alt="Klassendiagramm (6)" src="https://github.com/user-attachments/assets/e7f266f4-ba1b-4600-9c12-231c3b93affd" />



#### Layers / Components

 * UI (NiceGUI pages/components, browser as thin client)
 * Application logic (controllers + domain/services)
 * Persistence (SQLite + SQLModel entities + repositories)

#### Design Decisions

 * Organize code using MVC:
   * Model: domain + ORM entities (e.g. `src/domain/models.py`)
   * View: NiceGUI UI components/pages
   * Controller: event handlers and coordination logic between UI, services, and persistence
 
 * Separate entrypoint/UI routing (`main.py`, `src/__main__.py`) from domain logic (`src/services`) and persistence (`src/data_access`)
 * Use modules with clear responsibilities to reduce coupling and keep business logic testable
 * Keep business rules testable without starting the UI

* Hinweis: Das ER-Diagramm wird separat gepflegt und hier bewusst nicht angepasst.

#### Design Patterns

 * MVC (Model–View–Controller)
 * Repository/DAO for database access (see `src/data_access/repositories`)
 * Service layer for business rules (see `src/services`)


## 🗄️ Database and ORM
Unsere Applikation nutzt eine **SQLite**-Datenbank in Kombination mit **SQLModel** als Object-Relational Mapper (ORM). SQLModel vereint SQLAlchemy (für die Datenbankinteraktion) und Pydantic (für die Datenvalidierung) und ermöglicht uns eine saubere, typensichere Python-Entwicklung.

### ORM und Entitäten

Unsere Datenbankarchitektur folgt einer strikten Trennung der Zuständigkeiten und nutzt relationale Muster, um Redundanzen zu vermeiden und die Datenintegrität sicherzustellen:

* **User ↔ Account / Cards:** Kunden werden in der `users`-Tabelle gespeichert und auf die `User`-Entität gemappt. `Account` ist eine 1:n-Beziehung zu `User`. `DebitCard` ist einem `Account` zugeordnet (`account_id` → `accounts.account_id`) und damit indirekt einem `User` über das Konto zugeordnet. `CreditCard` ist direkt einem `User` zugeordnet (`user_id`) und kann optional ein `billing_account_id` (→ `Account`) besitzen, das für monatliche Kreditkartenabbuchungen verwendet wird.

* **Bidirektionales Mapping:** In der Python-Logik nutzen wir das `back_populates`-Feature von SQLModel. Dadurch können wir bidirektional navigieren (z. B. von einem Konto direkt auf das `User`-Objekt zugreifen), während die Datenbankebene strikt bei einer Einbahnstrasse über Foreign Keys (`user_id`) bleibt.

* **Budget ↔ Category:** Budgets werden auf die `Budget`-Entität gemappt. Ein harter `UniqueConstraint` in der Datenbank auf die Kombination `(user_id, month, year, category_id)` stellt sicher, dass ein User für einen bestimmten Monat und eine bestimmte Kategorie nicht versehentlich doppelte Budgets anlegen kann.

* **Die "is_a" Transaktions-Strategie:** Alle Geldbewegungen basieren auf der `Transaction`-Entität, welche die gemeinsamen Basisdaten (Betrag, Datum, Typ) speichert. Spezifische Zahlungsarten (wie `Transfer`, `Payment`, `RecurringTransaction`) erben *nicht* im Python-Code, sondern werden relational über Komposition abgebildet. Die `Transfer` ↔ `Transaction` Beziehung (1:1 über den Foreign Key `transaction_id`) stellt sicher, dass zielspezifische Daten (wie `target_iban`) sauber getrennt bleiben und die Haupttabelle keine leeren `NULL`-Spalten für nicht benötigte Felder ansammelt.

* **Persistente Dashboard-Tabelle:** Die Implementierung enthält keine persistente `dashboard`-Tabelle; Dashboards werden dynamisch berechnet und über das `DashboardSummary`-DTO geliefert.

## 👥 Arbeitsaufteilung

| Mitglied | Schwerpunkt |
|---|---|
| Asithan Supendran | Projektsetup & Infrastruktur, Business-Logik (Account, Auth, Budget, Dashboard, Payment, Transaction), Passwort-Sicherheit, Tests, README |
| Filmon Samy | Softwarearchitektur, Business-Logik (Recurring, Category, CreditcardBilling), MVC-Refactoring (Controller-Schicht), Code-Dokumentation & Kommentare |
| Janath Balasubramaniam | UI/Views (NiceGUI), Business-Logik (Card-Service), Kontoeinstellungen, Kartenmanagement, Dauerauftrags-UI |

## ✅ Project Requirements
Dieses Projekt erfüllt die Kernanforderungen wie folgt:

1. Using NiceGUI for building an interactive web app
2. Data validation in the app
3. Using an ORM for database management

### 1. Browser-based App (NiceGUI)
Die Anwendung ist eine serverseitige NiceGUI-Webapp mit Browser als Thin Client. Routen und Seiten sind zentral im App-Entrypoint definiert.

### 2. Data Validation
Die Anwendung validiert Eingaben u. a. für:
* Beträge (`validate_positive_amount`)
* IBAN-Format (`validate_iban`)
* Datumsbereiche (`validate_date_range`)
* Exactly-one-Regel für Transaktionsquellen (`validate_exactly_one_source`)

### 3. Database Management
Alle fachlichen Daten werden über SQLModel/SQLAlchemy verwaltet (u. a. User, Konten, Karten, Transaktionen, Budgets, Zahlungen, Umbuchungen).

## ⚙️ Implementation
### Technology
 * Python 3.x
 * NiceGUI
 * SQLModel / SQLAlchemy
 * SQLite
 * fpdf2
 * pytest

### How to run

> Voraussetzung: **Python 3.11 oder neuer**

1. (Optional, empfohlen) Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
2. Abhängigkeiten installieren:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Anwendung starten:
   ```bash
   python3 main.py
   ```
4. Im Browser öffnen: `http://localhost:8080/`

> Die Demo-Daten (User, Konten, Karten) werden beim ersten Start **automatisch** angelegt.

### Demo-Zugangsdaten

| Vertragsnummer | Passwort      | Name           |
|----------------|---------------|----------------|
| BB-100001      | Dummy_hash_1  | Hermann Grieder |
| BB-100002      | Dummy_hash_2  | Felix Haerer   |

### Tests ausführen

```bash
python3 -m pytest -q
```





















