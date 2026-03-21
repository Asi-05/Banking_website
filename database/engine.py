# Path hilft uns, sichere Dateipfade auf jedem Betriebssystem zu bauen.
from pathlib import Path

# Diese Funktion erstellt spaeter die Verbindung zur Datenbank.
from sqlalchemy import create_engine
# sessionmaker baut eine Vorlage fuer Datenbank-Sitzungen (Sessions).
from sqlalchemy.orm import sessionmaker


# __file__ ist der Pfad zu dieser Datei.
# resolve() macht daraus einen absoluten Pfad.
# parent.parent springt zwei Ebenen hoch:
# von database/engine.py nach database/ und dann ins Projekt-Hauptverzeichnis.
BASE_DIR = Path(__file__).resolve().parent.parent
# In diesem Ordner speichern wir die SQLite-Datei.
DB_DIR = BASE_DIR / "data"
# Ordner wird erstellt, falls er noch nicht existiert.
# parents=True: auch fehlende Elternordner erzeugen.
# exist_ok=True: kein Fehler, wenn der Ordner schon da ist.
DB_DIR.mkdir(parents=True, exist_ok=True)
# Voller Pfad zur eigentlichen Datenbankdatei.
DB_PATH = DB_DIR / "betterbank.db"

# SQLAlchemy erwartet eine URL zur Datenbank.
# Bei SQLite beginnt sie mit sqlite:/// und danach kommt der Dateipfad.
DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLite needs this flag for multi-threaded access in app servers.
# engine ist die zentrale Verbindung zur Datenbank.
# Darueber laufen spaeter alle SQL-Befehle.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal ist unsere "Session-Fabrik":
# Jede neue Session ist ein Arbeitskontext fuer Lese-/Schreibzugriffe.
# autocommit=False: nichts wird automatisch gespeichert.
# autoflush=False: SQLAlchemy sendet Aenderungen nicht ungefragt sofort an die DB.
# bind=engine: Session nutzt genau die oben definierte Datenbankverbindung.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
