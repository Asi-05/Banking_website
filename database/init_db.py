# SessionLocal liefert Sessions (Arbeitskontext fuer DB-Zugriffe),
# engine ist die Verbindung zur SQLite-Datenbank.
from .engine import SessionLocal, engine
# Base kennt alle ORM-Tabellen, die in models.py definiert wurden.
from .models import Base
# Diese Funktion fuellt die festen Kategorien in die Tabelle ein.
from .seed import seed_categories


# Diese Funktion richtet die Datenbank fuer das Projekt ein.
def init_database() -> None:
    # Erstellt alle Tabellen, die es noch nicht gibt.
    # Bereits vorhandene Tabellen bleiben unveraendert.
    Base.metadata.create_all(bind=engine)
    # Session oeffnen, damit wir Daten schreiben koennen.
    with SessionLocal() as session:
        # Fuegt feste Startdaten ein (z. B. Kategorien 1-10).
        seed_categories(session)


# Dieser Block wird nur ausgefuehrt,
# wenn man diese Datei direkt startet (z. B. python -m database.init_db).
if __name__ == "__main__":
    init_database()
    # Kurze Rueckmeldung in der Konsole.
    print("Database initialized successfully.")
