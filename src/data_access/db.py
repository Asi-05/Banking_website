"""Datenbankinitialisierung und Session-Verwaltung fuer Betterbank.

Dieses Modul kapselt die SQLite-Engine sowie Hilfsfunktionen fuer
Tabellenerstellung und Session-Bereitstellung.
"""

from collections.abc import Generator

from sqlmodel import SQLModel, Session, create_engine


DATABASE_URL = "sqlite:///betterbank.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
	"""Erzeugt alle in SQLModel registrierten Tabellen.

	Die Funktion ist idempotent und kann beim App-Start mehrfach
	aufgerufen werden, ohne bestehende Tabellen zu ueberschreiben.
	"""

	SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
	"""Liefert eine SQLModel-Session als Generator.

	Yields:
		Session: Offene Datenbank-Session innerhalb eines Context Managers.
	"""

	with Session(engine) as session:
		yield session
