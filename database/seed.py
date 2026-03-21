# select erlaubt uns einfache SELECT-Abfragen mit SQLAlchemy.
from sqlalchemy import select
# Session ist der aktive Arbeitskontext fuer DB-Befehle.
from sqlalchemy.orm import Session

# Category ist das ORM-Modell fuer die Kategorien-Tabelle.
from .models import Category


# Feste Kategorien laut Anforderungen.
# Diese IDs bleiben stabil, damit sie im ganzen Projekt einheitlich sind.
FIXED_CATEGORIES = [
    (1, "Transport"),
    (2, "Einkaeufe"),
    (3, "Versicherungen"),
    (4, "Miete"),
    (5, "Steuern"),
    (6, "Freizeit"),
    (7, "Sparen"),
    (8, "Well being"),
    (9, "Kontouebertrag"),
    (10, "Sonstiges"),
]


# Seed-Funktion: Traegt Startdaten ein, falls sie noch fehlen.
def seed_categories(session: Session) -> None:
    # Wir lesen alle bereits vorhandenen Kategorie-IDs aus der Datenbank.
    # Ergebnis ist am Ende ein Python-Set wie {1, 2, 3, ...}.
    existing = {row[0] for row in session.execute(select(Category.id)).all()}

    # Wir gehen jede feste Kategorie durch.
    for category_id, name in FIXED_CATEGORIES:
        # Wenn die ID schon existiert, nichts tun (verhindert Duplikate).
        if category_id in existing:
            continue
        # Fehlende Kategorie wird neu angelegt.
        session.add(Category(id=category_id, name=name))

    # Speichert alle neuen Kategorien dauerhaft in der Datenbank.
    session.commit()
