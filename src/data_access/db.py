from collections.abc import Generator

from sqlmodel import SQLModel, Session, create_engine


# SQLite engine for the Betterbank application
DATABASE_URL = "sqlite:///betterbank.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


# Create all tables that are registered in SQLModel metadata
def create_db_and_tables() -> None:
	SQLModel.metadata.create_all(engine)


# Session provider used by repositories and services
def get_session() -> Generator[Session, None, None]:
	with Session(engine) as session:
		yield session
