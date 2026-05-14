# BetterBank – Architektur & Lerndokumentation

> **Ziel dieses Dokuments:** Vollständige, prüfungsreife Erklärung der Programmstruktur der BetterBank-Anwendung für die Abschlusspräsentation. Alle Schichten, Entscheidungen und Zusammenhänge werden anhand konkreter Dateien belegt.

---

## Inhaltsverzeichnis

1. [Technologie-Stack](#1-technologie-stack)
2. [Programmstruktur & Architektur-Übersicht](#2-programmstruktur--architektur-übersicht)
3. [Das MVC-Pattern in BetterBank](#3-das-mvc-pattern-in-betterbank)
   - [Model – Daten & Datenbanklogik](#31-model--daten--datenbanklogik)
   - [View – NiceGUI-Frontend](#32-view--nicegui-frontend)
   - [Controller – Business-Logik](#33-controller--business-logik)
4. [Schichtentrennung und Kommunikation](#4-schichtentrennung-und-kommunikation)
5. [Exemplarischer Datenfluss: Login](#5-exemplarischer-datenfluss-login)
6. [Begründung der Architekturentscheidungen](#6-begründung-der-architekturentscheidungen)
7. [Sicherheitskonzepte](#7-sicherheitskonzepte)
8. [Teststrategie](#8-teststrategie)
9. [Zukünftige Entwicklungsoptionen (Ausblick)](#9-zukünftige-entwicklungsoptionen-ausblick)
10. [FAQ – Vorbereitung auf die Dozenten-Fragerunde](#10-faq--vorbereitung-auf-die-dozenten-fragerunde)

---

## 1. Technologie-Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| Programmiersprache | Python 3.13 | Typsicherheit, grosse Ökosystem, schnelles Prototyping |
| Web-UI | **NiceGUI** (Quasar/Vue.js) | Python-native UI ohne JavaScript-Kenntnisse, reactive Components |
| ORM & Datenbankmodelle | **SQLModel** (SQLAlchemy + Pydantic) | Einheitliche Klassen für DB-Tabellen und Typenvalidierung |
| Datenbank | **SQLite** | Keine Server-Infrastruktur nötig, Datei `betterbank.db` |
| Passwort-Hashing | **PBKDF2-HMAC-SHA256** (200'000 Iterationen) | Industriestandard, Brute-Force-resistent |
| PDF-Generierung | **fpdf2** | Kontoauszüge als PDF exportieren |
| Tests | **pytest** | Unit- und Integrationstests |

---

## 2. Programmstruktur & Architektur-Übersicht

### Verzeichnisstruktur

```
Banking Website/
├── main.py                        # Einstiegspunkt (delegiert an src/__main__.py)
├── betterbank.db                  # SQLite-Datenbankdatei
├── requirements.txt               # Python-Abhängigkeiten
├── statements/                    # Generierte PDF-Kontoauszüge
├── tests/                         # Automatisierte Pytest-Tests (22 Dateien)
└── src/
    ├── __main__.py                # App-Orchestrierung: DB → Seed → Routen → Server
    ├── domain/
    │   └── models.py              # MODEL: Alle Datenstrukturen (10 SQLModel-Klassen)
    ├── data_access/
    │   ├── db.py                  # Datenbankverbindung (Engine, Session)
    │   ├── seed.py                # Demo-Daten (idempotent)
    │   └── repositories/          # MODEL: Datenbankzugriffe (8 Repositories)
    ├── services/                  # CONTROLLER: Fachlogik (11 Services)
    ├── ui/
    │   ├── app_state.py           # Globaler Session-Zustand (eingeloggter User)
    │   ├── views/                 # VIEW: NiceGUI-Seiten (6 Views)
    │   └── controllers/           # VIEW-CONTROLLER: Brücke View ↔ Service (10 Controller)
    └── utils/
        ├── validators.py          # Validierungsregeln & Passwort-Hashing
        └── formatters.py          # Hilfsfunktionen für Anzeigeformate
```

### Wie das Programm als Ganzes funktioniert

Beim Start (`python main.py`) läuft folgende Sequenz ab:

```
main.py
  └── src/__main__.py → main()
        ├── 1. create_db_and_tables()   → SQLite-Tabellen anlegen / migrieren
        ├── 2. seed_database()          → Demo-User, Konten, Kategorien einfügen
        ├── 3. Routen registrieren      → NiceGUI-URLs auf View-Funktionen mappen
        └── 4. ui.run(port=8080)        → Webserver starten (blockiert)
```

Danach ist die App unter `http://localhost:8080` erreichbar. Jede URL-Route ruft eine Python-Funktion auf, die eine NiceGUI-Seite rendert.

**Routing-Übersicht:**

| URL-Route | View-Funktion | Geschützt? |
|---|---|---|
| `/` | `login_view.show()` | Nein (Login-Seite) |
| `/dashboard` | `dashboard_view.show()` | Ja (Login-Guard) |
| `/transactions` | `transaction_view.show()` | Ja |
| `/budget` | `budget_view.show()` | Ja |
| `/accounts` | `account_view.show()` | Ja |
| `/cards` | `card_view.show()` | Ja |

---

## 3. Das MVC-Pattern in BetterBank

BetterBank implementiert eine **erweiterte MVC-Architektur** mit fünf klar getrennten Schichten:

```
┌────────────────────────────────────────────────────────┐
│  VIEW          ui/views/*.py        (NiceGUI-Seiten)   │
├────────────────────────────────────────────────────────┤
│  UI-CONTROLLER ui/controllers/*.py  (View-Brücke)      │
├────────────────────────────────────────────────────────┤
│  SERVICE       services/*.py        (Fachlogik)        │
├────────────────────────────────────────────────────────┤
│  REPOSITORY    data_access/repositories/*.py (DB-CRUD) │
├────────────────────────────────────────────────────────┤
│  MODEL         domain/models.py     (Datenstrukturen)  │
│                data_access/db.py    (DB-Verbindung)    │
└────────────────────────────────────────────────────────┘
```

---

### 3.1 Model – Daten & Datenbanklogik

Das Model besteht aus zwei Teilen: **Datenstrukturen** (`domain/models.py`) und **Datenbankzugriff** (`data_access/`).

#### Datenstrukturen (`src/domain/models.py`)

Alle 10 Klassen sind mit **SQLModel** definiert, das automatisch Python-Klassen in Datenbanktabellen umwandelt:

**Persistierte Tabellen (`table=True`):**

| Klasse | Tabelle | Beschreibung |
|---|---|---|
| `User` | `users` | Bankkundendaten, Vertragsnummer, Passwort-Hash |
| `Account` | `accounts` | Bankkonten (Privat, Spar) mit IBAN und Saldo |
| `DebitCard` | `debit_cards` | Debitkarte, einem Konto zugeordnet |
| `CreditCard` | `credit_cards` | Kreditkarte mit Limit und Monatsabrechnung |
| `Category` | `categories` | Kategorien für Transaktionen (Miete, Lohn, ...) |
| `Transaction` | `transactions` | Basis-Tabelle für alle Geldbewegungen |
| `Transfer` | `transfers` | Umbuchung zwischen zwei eigenen Konten |
| `Payment` | `payments` | Inlandszahlung mit Ziel-IBAN |
| `Budget` | `budgets` | Monatliche Ausgabenlimits pro Kategorie |
| `RecurringTransaction` | `recurring_transactions` | Daueraufträge (monatlich/jährlich) |

**Nicht-persistierte DTOs (`table=False`):**

| Klasse | Verwendung |
|---|---|
| `ChartData` | Einnahmen/Ausgaben pro Monat für Dashboard-Diagramme |
| `DashboardSummary` | Gesamtergebnis: Kontostand, Summen, Chartdaten |

**Entity-Relationship-Übersicht:**

```
User (1) ──────────── Account (n)
                          │
                          ├── DebitCard (n)
                          ├── Transaction (n)         ── Transfer (0..1)
                          ├── RecurringTransaction (n) ── Payment (0..1)
                          └── CreditCard (billing_account)

User (1) ──────────── CreditCard (n)
User (1) ──────────── Budget (n)
Category (1) ─────── Transaction (n)
Category (1) ─────── Budget (n)
```

**Beispiel: User-Klasse mit Relationship**

```python
class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    password_hash: str          # NIEMALS Klartext gespeichert
    contract_number: str        # Login-Identifikator

    accounts: list["Account"] = Relationship(back_populates="user")
    credit_cards: list["CreditCard"] = Relationship(back_populates="user")
    budgets: list["Budget"] = Relationship(back_populates="user")
```

Die `primary_key`-IDs sind `Optional[int]` mit `default=None`, weil die Datenbank die ID erst nach `session.commit()` vergibt – vorher ist das Python-Objekt noch ohne ID.

#### Datenbankverbindung (`src/data_access/db.py`)

```python
# Einmalige Engine-Instanz für die gesamte App
engine = create_engine(
    "sqlite:///betterbank.db",
    connect_args={"check_same_thread": False}  # NiceGUI nutzt mehrere Threads
)
```

`check_same_thread=False` ist notwendig, weil NiceGUI verschiedene Browseranfragen in unterschiedlichen Threads verarbeitet. SQLAlchemy verwaltet die Thread-Sicherheit intern.

#### Repositories (`src/data_access/repositories/`)

Jedes Repository kapselt **alle Datenbankzugriffe** für genau ein Domänenobjekt:

| Repository | Zuständig für |
|---|---|
| `UserRepository` | `User` – Login, Profilverwaltung |
| `AccountRepository` | `Account` – Konten laden, Saldo aktualisieren |
| `TransactionRepository` | `Transaction` – Filtern, Erstellen, Löschen |
| `BudgetRepository` | `Budget` – Limits setzen und prüfen |
| `CardRepository` | `DebitCard` – Karte bestellen, sperren, ersetzen |
| `CategoryRepository` | `Category` – Kategorien laden |
| `PaymentRepository` | `Payment` – Zahlungsdetails speichern |
| `RecurringRepository` | `RecurringTransaction` – Daueraufträge verwalten |

**Typisches Repository-Muster:**

```python
class UserRepository:
    def __init__(self, session: Session):
        self.session = session  # Session wird vom Service übergeben

    def get_by_contract_number(self, contract_number: str) -> User | None:
        statement = select(User).where(User.contract_number == contract_number)
        return self.session.exec(statement).first()  # None wenn nicht gefunden

    def save(self, user: User) -> User:
        self.session.add(user)    # Hat user_id? → UPDATE, sonst → INSERT
        self.session.commit()     # Wirklich in SQLite-Datei schreiben
        self.session.refresh(user)  # Neue Werte aus DB laden (z.B. auto-generierte ID)
        return user
```

---

### 3.2 View – NiceGUI-Frontend

Das Frontend befindet sich in `src/ui/views/`. Jede Datei ist eine Python-Funktion, die eine vollständige Webseite mit NiceGUI-Komponenten (Quasar/Vue.js-basiert) aufbaut.

**Die 6 Views:**

| View-Datei | Seite | User Stories |
|---|---|---|
| `login_view.py` | Login-Formular | US13 |
| `dashboard_view.py` | Gesamtbilanz, Diagramme | US4 |
| `transaction_view.py` | Zahlungen, Daueraufträge, Kontoauszug | US1, US2, US3 |
| `budget_view.py` | Monatsbudgets verwalten | US5 |
| `account_view.py` | Konten eröffnen/schliessen | US7, US11 |
| `card_view.py` | Debit- und Kreditkarten | US8, US9 |

**Was eine View tut – und was nicht:**

```python
# src/ui/views/login_view.py – Ausschnitt

def show() -> None:
    from nicegui import ui

    # NUR: UI-Elemente aufbauen
    contract_number_input = ui.input(label="Vertragsnummer").props("outlined")
    password_input = ui.input(label="Passwort", password=True)
    error_label = ui.label("").classes("text-red-600")

    async def handle_login() -> None:
        # NUR: Controller aufrufen, Ergebnis in UI anzeigen
        result = auth_controller.login(
            contract_number_input.value,
            password_input.value
        )
        if isinstance(result, str):           # Fehlerfall
            error_label.set_text(result)
        elif result.get("success"):           # Erfolgsfall
            app_state["user_id"] = result["user_id"]
            ui.navigate.to("/dashboard")

    ui.button("Anmelden", on_click=handle_login)
```

Die View enthält **keine Passwort-Prüflogik, keine Datenbankabfragen und keine Geschäftsregeln**. Sie delegiert alles an den Controller.

**Login-Guard:** Jede geschützte View prüft am Anfang:

```python
def show() -> None:
    from nicegui import ui
    if app_state.get("current_user") is None:
        ui.navigate.to("/")   # Uneingeloggte Benutzer → Zurück zum Login
        return
    # ... Rest der View
```

---

### 3.3 Controller – Business-Logik

Die Business-Logik ist auf zwei Ebenen verteilt:

#### UI-Controller (`src/ui/controllers/`)

Die UI-Controller bilden die **direkte Brücke zwischen View und Service**. Ihre einzige Aufgabe: Service aufrufen und Exceptions in benutzerlesbare Strings umwandeln.

```python
# src/ui/controllers/auth_controller.py

class AuthController:
    def login(self, contract_number: str, password: str) -> dict | str:
        try:
            return auth_service.login(contract_number, password)  # Service aufrufen
        except Exception as error:
            return str(error)   # Exception → lesbarer Fehlertext für die View

    def logout(self) -> None:
        app_state["current_user"] = None   # State leeren
        app_state["user_id"] = None
        app_state["show_logout_message"] = True

# Singleton: wird von allen Views importiert
auth_controller = AuthController()
```

**Alle 10 UI-Controller:**

| Controller | Zuständig für |
|---|---|
| `auth_controller` | Login, Logout, Benutzername anzeigen |
| `account_controller` | Konto eröffnen/schliessen, Saldo abrufen |
| `transaction_controller` | Transaktionen erstellen, bearbeiten, löschen |
| `payment_controller` | Zahlungsauftrag mit IBAN ausführen |
| `recurring_controller` | Dauerauftrag anlegen, bearbeiten, löschen |
| `budget_controller` | Budget setzen, Verbrauch prüfen |
| `card_controller` | Debitkarte bestellen, sperren, ersetzen |
| `category_controller` | Kategorien laden |
| `dashboard_controller` | Dashboard-Kennzahlen berechnen |
| `user_controller` | Profil (Telefon, Adresse) aktualisieren |

#### Services (`src/services/`)

Die Services enthalten die **eigentliche Fachlogik**. Sie sind unabhängig von NiceGUI und könnten in einem anderen Frontend wiederverwendet werden.

**Alle 11 Services:**

| Service | Kernaufgabe |
|---|---|
| `auth_service` | Login, PBKDF2-Passwortprüfung, Migration auf sicheres Hash-Format |
| `account_service` | Konto eröffnen/schliessen, IBAN-Generierung (Modulo-97) |
| `transaction_service` | Transaktionen buchen + Saldo aktualisieren (Multiplier-Trick) |
| `payment_service` | Inlandszahlung mit IBAN-Validierung |
| `recurring_service` | Daueraufträge anlegen, Fälligkeitsprüfung beim Login |
| `budget_service` | Budget prüfen, Warnung bei Überschreitung |
| `card_service` | Debitkarte bestellen/sperren/ersetzen |
| `dashboard_service` | Bilanzkennzahlen + monatliche Chartdaten aggregieren |
| `creditcard_billing_service` | Monatliche Kreditkartenabrechnung beim Login |
| `category_service` | Kategorien laden |
| `user_service` | Profildaten (Telefon, Adresse) aktualisieren |

**Singleton-Muster:** Jeder Service wird als Modul-Instanz bereitgestellt:

```python
# Am Ende jeder Service-Datei:
auth_service = AuthService()

# Import in anderen Dateien:
from src.services.auth_service import auth_service
```

---

## 4. Schichtentrennung und Kommunikation

### Die goldene Regel der Schichtentrennung

> **Jede Schicht darf nur die direkt darunter liegende Schicht aufrufen – nie überspringen.**

| Schicht | Darf aufrufen | Darf NICHT aufrufen |
|---|---|---|
| View | UI-Controller | Services, Repositories, DB direkt |
| UI-Controller | Services | Repositories, DB direkt |
| Service | Repositories, andere Services, Utils | Views, Controller |
| Repository | DB (SQLModel/Session) | Services, Views |

### Kommunikationskanal: `app_state`

Die Views kommunizieren ihren Zustand über `src/ui/app_state.py`:

```python
app_state: dict = {
    "current_user": None,       # None = nicht eingeloggt; dict = Login-Ergebnis
    "user_id": None,            # DB-ID des eingeloggten Users (für DB-Abfragen)
    "show_logout_message": False,  # Flag für einmalige Logout-Bestätigung
}
```

Dieses Muster ist für eine Single-User-Demo-App akzeptabel. Es wird im Abschnitt [FAQ](#10-faq--vorbereitung-auf-die-dozenten-fragerunde) kritisch diskutiert.

### Session-Management

Services öffnen für jede Operation eine eigene, kurzlebige Datenbanksession:

```python
# Typisches Service-Muster
def some_method(self, user_id: int) -> list[Account]:
    with Session(engine) as session:          # Session öffnen
        repo = AccountRepository(session)     # Repository mit Session erstellen
        result = repo.list_by_user(user_id)  # DB-Abfrage
        return result
    # Session automatisch geschlossen am Ende des with-Blocks
```

---

## 5. Exemplarischer Datenfluss: Login

Der Login-Vorgang zeigt alle fünf Schichten in Aktion:

```
[Browser]  User gibt Vertragsnummer + Passwort ein, klickt "Anmelden"
    │
    ▼
[VIEW]  login_view.py → handle_login()
    │   Liest Eingabefelder, ruft Controller auf
    │
    ▼
[UI-CONTROLLER]  auth_controller.login(contract_number, password)
    │   Delegiert an Service, fängt Exceptions als String ab
    │
    ▼
[SERVICE]  auth_service.login(contract_number, password)
    │   1. Session öffnen
    │   2. UserRepository.get_by_contract_number()  → DB-Query
    │   3. verify_password(password, user.password_hash)  → PBKDF2
    │   4. Falls altes Hash-Format: Passwort-Migration (password_hash upgraden)
    │   5. Session schliessen
    │   6. recurring_service.process_due_recurring_on_login()
    │   7. creditcard_billing_service.process_monthly_billing()
    │   8. dict zurückgeben: {success, auth_token, user_id, ...}
    │
    ▼
[REPOSITORY]  user_repository.get_by_contract_number(contract_number)
    │   SELECT * FROM users WHERE contract_number = :contract_number
    │
    ▼
[MODEL / DB]  SQLite betterbank.db  →  User-Objekt oder None
    │
    └── Rückgabe durch alle Schichten nach oben ↑

[VIEW]  Setzt app_state["user_id"] und navigiert zu /dashboard
```

**Fehlerfall:** Wenn Vertragsnummer oder Passwort falsch sind, wirft der Service eine `ValueError("Ungueltige Anmeldedaten")`. Der Controller fängt sie als `str(error)` ab. Die View zeigt diesen String als rote Fehlermeldung an – ohne dass Details über den Fehlergrund durchsickern (Security Best Practice).

---

## 6. Begründung der Architekturentscheidungen

### Warum diese Aufteilung für eine Banking-App?

**1. Strikte Schichtentrennung schützt vor Fehlern**

In einer Banking-App ist Datenkonsistenz kritisch. Wenn Views direkt die Datenbank ansprechen könnten, entstünden schnell Saldofehler. Die Transaktionslogik (Saldo erhöhen/senken, Exactly-one-Source-Regel) liegt ausschliesslich im `transaction_service` – ein einziger, testierbarer Ort.

**2. Testbarkeit ohne UI**

Services und Repositories können ohne NiceGUI getestet werden. Die 22 Testdateien in `tests/` testen die Fachlogik isoliert:

```python
# tests/test_calculate_total_balance.py
def test_total_balance_sums_all_accounts():
    # Kein NiceGUI, keine View – nur Service + In-Memory-DB
    result = dashboard_service.dashboard(user_id=1, start_date=..., end_date=...)
    assert result.total_balance == expected_balance
```

**3. Singleton-Services reduzieren Overhead**

Da Services keine Instanzvariablen verwenden (alle Daten kommen aus der DB), ist eine einzige Instanz pro Service ausreichend. Dies vereinfacht den Import und spart Speicher.

**4. Repository-Pattern entkoppelt ORM vom Fachcode**

Falls SQLite durch PostgreSQL ersetzt würde, müsste nur `db.py` und minimal die Repositories angepasst werden. Services und Views bleiben unverändert.

**5. Idempotentes Seeding**

`seed_database()` prüft vor jedem Einfügen, ob die Daten schon existieren. Das ermöglicht wiederholte App-Starts ohne Datenverdopplung – wichtig für Entwicklung und Demos.

### Technologieentscheidungen

**SQLModel statt reinem SQLAlchemy:**
SQLModel kombiniert SQLAlchemy (SQL-Kommunikation) mit Pydantic (Typvalidierung) in einer einzigen Klasse. Dies reduziert Boilerplate: eine Klasse ist gleichzeitig Datenbankmodell und Python-Datenstruktur.

**NiceGUI statt Flask/FastAPI + React:**
NiceGUI erlaubt vollständige Web-UIs in reinem Python. Für ein Lernprojekt mit Banking-Fokus vermeidet dies den JavaScript-Overhead und lässt das Team bei Python bleiben.

**SQLite statt PostgreSQL:**
Für eine Demo-App ohne echte Multi-User-Last ist SQLite ideal: keine Serverinstallation, die Datenbankdatei liegt direkt im Projektverzeichnis und ist leicht versionierbar.

---

## 7. Sicherheitskonzepte

### Passwort-Hashing (PBKDF2)

Passwörter werden **niemals im Klartext** gespeichert. Das Format in der Datenbank ist:

```
<random_salt_32chars>$<pbkdf2_hash_hex>
```

```python
# src/utils/validators.py

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)   # Zufälliger Salt verhindert Rainbow-Tables
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,                   # 200'000 Iterationen = Brute-Force kostet Tage
    )
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    salt, expected_hex = stored_hash.split("$", 1)
    calculated_hex = hashlib.pbkdf2_hmac("sha256", ..., 200_000).hex()
    return hmac.compare_digest(calculated_hex, expected_hex)  # Timing-sicher
```

`hmac.compare_digest` verhindert Timing-Angriffe, bei denen ein Angreifer aus der Antwortzeit auf den Hash schliessen könnte.

### Passwort-Migration beim Login

Frühere Demo-Daten enthielten Klartext-Passwörter. Beim ersten Login mit einem alten Passwort wird es automatisch auf PBKDF2 upgegraded – ohne dass der User etwas merkt ("Migration on Login").

### Generische Fehlermeldungen

```python
# Beide Fälle geben dieselbe Nachricht – man erfährt nicht, ob die
# Vertragsnummer oder das Passwort falsch war
raise ValueError("Ungueltige Anmeldedaten")
```

### IBAN-Validierung (Schweizer Format)

```python
# Nur CH-IBANs mit genau 21 Zeichen werden akzeptiert
if re.fullmatch(r"CH\d{19}", normalized) is None:
    raise ValueError("Ungültige IBAN")
```

### Exactly-one-Source-Regel

Jede Transaktion muss genau **eine** Belastungsquelle haben (Konto, Debitkarte oder Kreditkarte – nie zwei gleichzeitig):

```python
set_sources = sum(v is not None for v in (account_id, card_id, creditcard_id))
if set_sources != 1:
    raise ValueError("Genau eine Belastungsquelle muss gesetzt sein")
```

---

## 8. Teststrategie

Die 22 Testdateien decken drei Ebenen ab:

| Testtyp | Beispieldateien | Was wird getestet |
|---|---|---|
| **Unit Tests** | `test_validate_iban_format.py`, `test_calculate_total_balance.py` | Einzelne Funktionen isoliert |
| **Service-Tests** | `test_budget_service.py`, `test_creditcard_billing_service.py` | Services mit In-Memory-SQLite-DB |
| **Integrationstests** | `test_integration_account_transfer.py`, `test_integration_create_recurring_payment.py` | Mehrere Schichten zusammen (Controller → Service → DB) |
| **Controller-Tests** | `test_ui_auth_controller.py`, `test_ui_transaction_controller.py` | UI-Controller-Verhalten und Fehlerbehandlung |

**Wichtig:** Die Tests verwenden echte SQLite-In-Memory-Datenbanken (`sqlite:///:memory:`), keine Mocks. Dies stellt sicher, dass SQL-Queries tatsächlich korrekt funktionieren.

---

## 9. Zukünftige Entwicklungsoptionen (Ausblick)

### Kurzfristig (nächste Iteration)

**1. Multi-User-Session-Management**
Aktuell ist `app_state` ein globales Dictionary – alle Browser-Tabs teilen denselben Zustand. In einer Mehrbenutzer-Umgebung müsste NiceGUIs `ui.context` oder `app.storage.user` (user-spezifischer Storage) verwendet werden:

```python
# Statt:  app_state["user_id"] = user_id
# Besser: app.storage.user["user_id"] = user_id  (pro Browser-Session isoliert)
```

**2. Alembic für Datenbankmigrationen**
Die aktuellen Mini-Migrationen in `db.py` (manuelles `ALTER TABLE`) sollten durch **Alembic** ersetzt werden, das Datenbankschema-Änderungen versioniert und rückgängig machbar macht.

**3. Echte Datenbankproduktion (PostgreSQL)**
SQLite ist für eine Single-User-Demo ausreichend, für parallele Benutzer würde PostgreSQL benötigt. Der Wechsel erfordert nur eine neue Connection-URL in `db.py`.

### Mittelfristig (erweiterte Architektur)

**4. REST API Layer (FastAPI)**
Würde man ein Mobile-App-Frontend hinzufügen, könnte man die bestehenden Services direkt als FastAPI-Endpoints exponieren – die Service-Schicht bleibt unverändert:

```python
@app.get("/api/dashboard/{user_id}")
def get_dashboard(user_id: int, start: date, end: date):
    return dashboard_service.dashboard(user_id, start, end)
```

**5. Caching mit Redis**
Dashboard-Kennzahlen werden bei jedem Seitenaufruf neu berechnet. Mit Redis könnten aggregierte Werte für z.B. 60 Sekunden gecacht werden, was die Datenbankbelastung drastisch reduziert.

**6. Erweiterte Sicherheitskonzepte**
- JWT-Tokens statt globalem `app_state` für zustandslose Authentifizierung
- Rate-Limiting beim Login (Schutz vor Brute-Force)
- Audit-Log für sicherheitsrelevante Aktionen (Login, Kontoänderungen)
- Zwei-Faktor-Authentifizierung (TOTP)

### Langfristig (Microservices)

**7. Microservice-Aufteilung**
Die bestehende Service-Struktur bietet eine natürliche Vorlage für Microservices:
- `auth_service` → Authentication Service
- `transaction_service` → Transaction Service
- `dashboard_service` → Reporting Service

Jeder Service könnte unabhängig skaliert und deployed werden, mit einer Message Queue (z.B. RabbitMQ) für asynchrone Kommunikation.

---

## 10. FAQ – Vorbereitung auf die Dozenten-Fragerunde

---

### Frage 1: „Warum haben Sie ein globales `app_state`-Dictionary statt einer echten Session-Verwaltung? Ist das sicher?"

**Antwort:**

Das globale `app_state`-Dictionary ist eine bewusste Vereinfachung für die Demo-App. Es speichert `user_id` und das Login-Ergebnis für den aktuell eingeloggten User:

```python
app_state = {
    "current_user": None,   # None = nicht eingeloggt
    "user_id": None,
}
```

**Limitierung:** Da das Dictionary prozessglobal ist, teilen sich alle Browser-Tabs und alle Nutzer denselben Zustand auf demselben Server-Prozess. Das bedeutet: Wenn sich ein zweiter Nutzer einloggt, würde `user_id` überschrieben und der erste Nutzer hätte keinen Zugriff mehr auf seine Daten.

**Produktionslösung:** In einer echten Banking-Applikation würde man NiceGUIs `app.storage.user` verwenden (browsergebundener Storage) oder serverseitige Sessions mit JWT-Tokens:

```python
# Sichere Multi-User-Alternative:
app.storage.user["user_id"] = result["user_id"]  # Isoliert pro Browser-Session
```

Das aktuelle Design ist für die Demo-App mit einem Benutzer gleichzeitig akzeptabel und dokumentiert in `app_state.py`.

---

### Frage 2: „Warum trennen Sie Services und UI-Controller? Wäre ein Controller nicht ausreichend?"

**Antwort:**

Die Trennung zwischen **UI-Controller** (`ui/controllers/`) und **Service** (`services/`) hat zwei konkrete Vorteile:

**1. Testbarkeit:** Die Services können vollständig ohne NiceGUI getestet werden. Unsere 22 Testdateien importieren direkt die Services und testen die Fachlogik isoliert. Würden Services NiceGUI-Abhängigkeiten enthalten, wäre das unmöglich.

**2. Wiederverwendbarkeit:** Die Service-Schicht ist UI-agnostisch. Wenn wir morgen eine REST API mit FastAPI hinzufügen, importieren wir dieselben Services:

```python
# Dieser Code würde in einem FastAPI-Endpoint so aussehen:
@app.get("/api/dashboard")
def dashboard_api(user_id: int):
    return dashboard_service.dashboard(user_id, ...)  # Gleicher Service, neues UI
```

Der UI-Controller hat genau eine Aufgabe: Python-Exceptions in Strings umwandeln, die die View anzeigen kann. Diese Fehlerbehandlung gehört nicht in den Service (der weiss nichts von der UI) und nicht in die View (die sollte so schlank wie möglich sein).

---

### Frage 3: „Wie stellen Sie sicher, dass die Transaktionssalden konsistent bleiben? Was passiert bei einem Fehler mitten in einer Buchung?"

**Antwort:**

Die Konsistenz wird durch **atomare Datenbank-Transaktionen** und den **Multiplier-Trick** im `transaction_service` gewährleistet.

**Atomare Sessions:** Jede Session-Operation wird erst mit `session.commit()` dauerhaft geschrieben. Wenn vorher ein Fehler auftritt, wird die Session automatisch zurückgerollt – kein halbfertiger Zustand in der Datenbank.

**Multiplier-Trick für Edit/Delete:**

```python
# Bei EDIT einer Transaktion:
# Schritt 1: Alten Effekt rückgängig machen (multiplier = -1)
self._apply_source_effect(old_transaction, multiplier=-1)
# Schritt 2: Neuen Effekt anwenden (multiplier = +1)
self._apply_source_effect(new_transaction, multiplier=+1)
```

Wenn zwischen Schritt 1 und 2 ein Fehler auftritt, rollt die Session zurück und der Saldo bleibt im Ausgangszustand.

**Einschränkung:** SQLite unterstützt keine `SELECT ... FOR UPDATE`-Locks. Bei echter Parallelität (zwei Tabs gleichzeitig) könnten Race Conditions entstehen. In einem Produktionssystem würde man PostgreSQL mit Serializable Isolation Level verwenden.

---

### Frage 4: „Wie funktioniert die automatische Ausführung von Daueraufträgen? Gibt es einen Cron-Job?"

**Antwort:**

Es gibt **keinen Cron-Job oder Hintergrundprozess**. Die Daueraufträge werden stattdessen **beim Login des Users** ausgeführt – eine Technik, die als "Lazy Execution" oder "Triggered Processing" bekannt ist.

**Ablauf:**

```python
# in auth_service.login():
executed = recurring_service.process_due_recurring_on_login(user_id, date.today())
```

Der `RecurringService` prüft alle Daueraufträge des Users und führt fällige aus:

```python
def _is_due(self, recurring, login_date) -> bool:
    next_due = self._next_due_date(recurring.last_executed, recurring.interval)
    return next_due <= login_date
```

**Fälligkeitsberechnung:** Monatliche Daueraufträge werden nicht mit `+30 Tage` berechnet (Monate haben unterschiedlich viele Tage), sondern mit korrektem Monats-Carryover:

```python
# 31. Januar + 1 Monat = 28. Februar (nicht 3. März!)
day = min(from_date.day, calendar.monthrange(year, month)[1])
```

**Vorteil:** Einfache Implementierung ohne Infrastruktur. **Nachteil:** Daueraufträge werden nur ausgeführt, wenn der User sich einloggt. In einer Produktionsumgebung würde man einen dedizierten Scheduler (APScheduler, Celery, oder einen Cloud-Cron-Job) verwenden.

---

### Frage 5: „Warum verwenden Sie SQLModel statt direktem SQLAlchemy oder einem anderen ORM? Was sind die Tradeoffs?"

**Antwort:**

**SQLModel** ist eine Python-Bibliothek, die **SQLAlchemy** (SQL-Datenbankzugriff) mit **Pydantic** (Typenvalidierung) kombiniert. Der entscheidende Vorteil: Eine einzige Klasse ist gleichzeitig Datenbankmodell und Python-Datenstruktur:

```python
# Mit SQLModel: Eine Klasse für alles
class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    contract_number: str

# Mit reinem SQLAlchemy bräuchte man TWO Klassen:
# 1. Eine ORM-Klasse (Datenbankstruktur)
# 2. Eine separate Pydantic-Klasse (Validierung/Serialisierung)
```

**Vorteile von SQLModel:**
- Weniger Code (eine Klasse statt zwei)
- Automatische Typvalidierung durch Pydantic
- Nahtlose Integration mit FastAPI (für spätere API-Erweiterung)

**Tradeoffs:**
- SQLModel ist jünger als SQLAlchemy und hat noch einige Edge-Cases (z.B. bei komplexen Relationship-Konfigurationen mit mehreren Foreign Keys auf dieselbe Tabelle, wie bei `Transfer` mit `from_account_id` und `to_account_id`). Diese erfordern explizite `sa_relationship_kwargs`.
- Die SQLModel-Dokumentation ist weniger umfangreich als SQLAlchemy.

Für dieses Projekt überwiegen die Vorteile klar: Schnellere Entwicklung, weniger Boilerplate, und die Datenbankmodelle sind sofort als Python-Objekte nutzbar.

---

*Dokument erstellt: Mai 2026 | BetterBank E-Banking Projekt | FHNW*
