"""src.data_access.db

Diese Datei gehoert zur **Data-Access-Schicht**.

=== WAS MACHT DIESE DATEI? ===
Sie baut die Datenbankverbindung auf und stellt sie dem Rest der App bereit.

    1. `engine`:              Die Datenbankverbindung (einmal erstellt, ueberall genutzt)
    2. `create_db_and_tables`: Erstellt Tabellen beim App-Start (falls noch nicht vorhanden)
    3. `get_session`:         Hilfsfunktion, um eine DB-Session zu oeffnen

=== WAS IST EINE "ENGINE"? ===
Die Engine ist das Herzstueck der Datenbankverbindung. Sie enthaelt:
    - Die Datenbankadresse (hier: SQLite-Datei "betterbank.db")
    - Verbindungsoptionen (z.B. check_same_thread=False)
    - Den internen Connection-Pool

Die Engine wird EINMAL beim Import dieser Datei erstellt und von allen
Repositories und Services wiederverwendet.

=== WARUM SQLITE? ===
SQLite ist eine einfache Datenbankdatei ohne separaten Server.
    - Die Datei `betterbank.db` liegt im Projektverzeichnis.
    - Kein separater Datenbankserver noetig (ideal fuer Demo-Projekte).
    - In einem echten Bankprojekt wuerde man PostgreSQL oder MySQL verwenden.

=== WAS IST `check_same_thread=False`? ===
SQLite erlaubt normalerweise nur Zugriffe vom GLEICHEN Thread, der die
Verbindung erstellt hat. NiceGUI bearbeitet aber verschiedene Seitenanfragen
in unterschiedlichen Threads.
    `check_same_thread=False` deaktiviert diese Einschraenkung.
    (SQLModel/SQLAlchemy verwaltet die Thread-Sicherheit selbst.)

=== WAS IST EINE "SESSION"? ===
Eine Session ist eine kurzlebige Datenbankverbindung fuer eine Operation.
Jede Repository-Methode oeffnet eine eigene Session:
    with Session(engine) as session:
        result = session.get(User, user_id)
    # Session automatisch geschlossen am Ende des with-Blocks.

=== WAS MACHT `create_db_and_tables()`? ===
    1. `SQLModel.metadata.create_all(engine)`:
       Erstellt alle Tabellen, die in `domain/models.py` definiert sind.
       Falls eine Tabelle schon existiert, wird sie NICHT veraendert.

    2. Mini-Migrationen (ALTER TABLE):
       Neue Spalten koennen mit `ALTER TABLE users ADD COLUMN phone TEXT`
       nachgezogen werden. Falls die Spalte schon existiert, wird der Fehler
       ignoriert (try/except). Das ersetzt eine echte Migration (Alembic).

    3. Alte Tabellen loeschen:
       `DROP TABLE IF EXISTS dashboard` entfernt nicht mehr benoetigte Tabellen.

=== ARCHITEKTUR-KETTE ===
    src/__main__.py → create_db_and_tables() [beim Start]
    Services/Repositories → `with Session(engine) as session:` [bei jedem DB-Zugriff]
"""

from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

# Alle Models importieren, damit SQLModel.metadata sie kennt (fuer create_all).
from src.domain import models  # noqa: F401


# Datenbankadresse: SQLite-Datei im Projektverzeichnis.
DATABASE_URL = "sqlite:///betterbank.db"

# Engine: einmalige Datenbankverbindung fuer die gesamte App.
# check_same_thread=False: Erlaubt Zugriffe aus verschiedenen Threads (noetig fuer NiceGUI).
# echo=False: Kein SQL-Logging in der Konsole (echo=True waere hilfreich zum Debuggen).
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    """Erstellt alle Datenbanktabellen und fuehrt einfache Migrationen aus.

    WANN WIRD DAS AUFGERUFEN?
        Einmalig beim App-Start in `src/__main__.py`:
        create_db_and_tables()
        seed_database()

    WAS PASSIERT SCHRITT FUER SCHRITT:
        1. `SQLModel.metadata.create_all(engine)`:
           Alle Klassen in `models.py` mit `table=True` werden als Tabellen angelegt.
           Bereits vorhandene Tabellen werden NICHT veraendert (kein Datenverlust).

        2. Mini-Migrationen fuer neue Spalten:
           Wenn neue Spalten zu einem Model hinzugefuegt werden, kann man sie
           hier mit ALTER TABLE nachziehen. Der try/except ignoriert den Fall,
           dass die Spalte schon existiert.

        3. Alte Tabellen loeschen:
           `DROP TABLE IF EXISTS dashboard` entfernt eine veraltete Tabelle
           aus einer frueheren Version der App.

    HINWEIS:
        Das ist keine vollstaendige Datenbankmigration (kein Versionsmanagement).
        Fuer echte Projekte wuerde man Alembic verwenden.
    """
    # Tabellen anlegen (alle Models aus domain/models.py).
    SQLModel.metadata.create_all(engine)

    with engine.connect() as conn:
        # Mini-Migration: Neue Spalten `phone` und `address` zu `users` hinzufuegen.
        # Fehler (Spalte existiert schon) werden ignoriert.
        for col, typ in [("phone", "TEXT"), ("address", "TEXT")]:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
                conn.commit()
            except Exception:
                pass  # Spalte existiert bereits → ignorieren.

        try:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN is_settled INTEGER NOT NULL DEFAULT 1"))
            conn.commit()
        except Exception:
            pass  # Spalte existiert bereits → ignorieren.

        # Alte `dashboard`-Tabelle loeschen (Dashboard wird jetzt dynamisch berechnet).
        try:
            conn.execute(text("DROP TABLE IF EXISTS dashboard"))
            conn.commit()
        except Exception:
            pass


def get_session() -> Generator[Session, None, None]:
    """Liefert eine offene Datenbank-Session als Generator (Dependency-Pattern).

    WIE BENUTZT MAN DAS?
        Normalerweise oeffnen Repositories direkt eine Session:
            with Session(engine) as session:
                result = session.get(User, user_id)

        `get_session()` ist eine Alternative fuer Dependency-Injection-Frameworks
        (FastAPI, etc.). In diesem Projekt wird es weniger direkt genutzt.

    GENERATOR-PATTERN:
        `yield` statt `return`: Die Funktion "pausiert" nach dem yield und
        laeuft weiter, wenn der Aufrufer fertig ist. So wird die Session
        am Ende automatisch geschlossen.

    Yields:
        Eine offene SQLModel/SQLAlchemy-Session.
    """
    with Session(engine) as session:
        yield session


# Wird nur ausgefuehrt, wenn diese Datei direkt gestartet wird (nicht importiert).
# Nuetzlich zum Testen: `python -m src.data_access.db`
if __name__ == "__main__":
    create_db_and_tables()
