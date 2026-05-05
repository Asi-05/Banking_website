"""Datenbank-Anbindung (Data-Access-Schicht).

Dieses Modul baut die SQLite-Verbindung (SQLAlchemy/SQLModel `engine`) auf,
erstellt bei Bedarf alle Tabellen und stellt eine `Session`-Factory bereit.
Repositories und Services nutzen `get_session()`, um sauber und einheitlich auf
die Datenbank zuzugreifen, ohne überall Engine-/Session-Code zu duplizieren.
"""

from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

from src.domain import models  # noqa: F401


# SQLite engine for the Betterbank application
DATABASE_URL = "sqlite:///betterbank.db"
# `check_same_thread=False` ist bei SQLite in Web-Apps oft nötig, weil Requests/
# UI-Events in unterschiedlichen Threads laufen können. Ohne diese Option würde
# SQLite Zugriffe aus einem anderen Thread als dem Erzeuger-Thread blockieren.
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


# Create all tables that are registered in SQLModel metadata
def create_db_and_tables() -> None:
	"""Erstellt die Datenbanktabellen und führt einfache „Einmal-Migrationen“ aus.

	SQLModel sammelt beim Import der Models alle Tabellen in `SQLModel.metadata`.
	`create_all()` legt diese Tabellen an, falls sie noch nicht existieren.

	Zusätzlich enthält diese Funktion bewusst ein paar pragmatische SQL-Schritte:
	- neue Spalten per `ALTER TABLE` nachziehen
	- alte, nicht mehr benötigte Tabellen löschen

	Das ersetzt **keine** echte Migration (wie Alembic), ist für ein Studienprojekt
	aber oft die einfachste Art, die lokale DB nach Code-Änderungen anzupassen.
	"""
	SQLModel.metadata.create_all(engine)
	# Mini-Migration: Neue Spalten `phone` und `address` zur `users`-Tabelle hinzufügen.
	# Falls die Spalten schon existieren, ignorieren wir den Fehler.
	with engine.connect() as conn:
		for col, typ in [("phone", "TEXT"), ("address", "TEXT")]:
			try:
				conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
				conn.commit()
			except Exception:
				pass  # Spalte existiert bereits

		# Design-Entscheid: Das Dashboard wird dynamisch berechnet und nicht persistiert.
		# Daher entfernen wir eine alte `dashboard`-Tabelle, falls sie aus älteren
		# Versionen noch existiert.
		try:
			conn.execute(text("DROP TABLE IF EXISTS dashboard"))
			conn.commit()
		except Exception:
			pass


# Session provider used by repositories and services
def get_session() -> Generator[Session, None, None]:
	"""Gibt eine Datenbank-Session als Generator zurück (Dependency-Pattern).

	Dieses Pattern ist praktisch, weil Aufrufer (z. B. Repositories) mit
	`with Session(engine) as session:` arbeiten können, ohne den Boilerplate jedes
	Mal neu zu schreiben. Die Session wird am Ende des `with`-Blocks automatisch
	geschlossen.

	Yields:
		Eine offene SQLModel/SQLAlchemy-Session.
	"""
	with Session(engine) as session:
		yield session


if __name__ == "__main__":
	create_db_and_tables()
