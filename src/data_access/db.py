from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

from src.domain import models  # noqa: F401


# SQLite engine for the Betterbank application
DATABASE_URL = "sqlite:///betterbank.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


# Create all tables that are registered in SQLModel metadata
def create_db_and_tables() -> None:
	SQLModel.metadata.create_all(engine)
	# Migration: Neue Spalten phone und address zu Users-Tabelle hinzufügen (einmalig)
	with engine.connect() as conn:
		for col, typ in [("phone", "TEXT"), ("address", "TEXT")]:
			try:
				conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
				conn.commit()
			except Exception:
				pass  # Spalte existiert bereits

		# Entferne alte persistente Dashboard-Tabelle falls vorhanden (Option 1: kein Persistieren)
		try:
			conn.execute(text("DROP TABLE IF EXISTS dashboard"))
			conn.commit()
		except Exception:
			pass


# Session provider used by repositories and services
def get_session() -> Generator[Session, None, None]:
	with Session(engine) as session:
		yield session 


if __name__ == "__main__":
	create_db_and_tables()
