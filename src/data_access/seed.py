"""Seed-Logik fuer initiale Stammdaten und Demo-Benutzer.

Das Modul legt beim Erststart die vordefinierten Kategorien sowie zwei
Testuser inkl. je einem Privat- und Sparkonto an.
"""

from sqlmodel import Session, select

from src.data_access.db import create_db_and_tables, engine
from src.domain.models import Account, Category, User

CATEGORY_NAMES = [
	"Transport",
	"Einkaeufe",
	"Versicherungen",
	"Miete",
	"Steuern",
	"Freizeit",
	"Sparen",
	"Well-being",
	"Kontouebertrag",
	"Sonstiges",
]

TEST_USERS = [
	{
		"first_name": "Hermann",
		"last_name": "Grieder",
		"contract_number": "BB-100001",
		"password_hash": "dummy_hash_1",
	},
	{
		"first_name": "Felix",
		"last_name": "Haerer",
		"contract_number": "BB-100002",
		"password_hash": "dummy_hash_2",
	},
]

def seed_categories(session: Session) -> None:
	"""Legt die festen Kategorien an, falls sie noch nicht existieren.

	Args:
		session: Aktive SQLModel-Session fuer Lese-/Schreibzugriffe.
	"""

	for category_name in CATEGORY_NAMES:
		existing_category = session.exec(
			select(Category).where(Category.name == category_name)
		).first()
		if existing_category is None:
			session.add(Category(name=category_name))
	session.commit()


def seed_users(session: Session) -> list[User]:
	"""Stellt sicher, dass genau die zwei vordefinierten Testuser vorhanden sind.

	Args:
		session: Aktive SQLModel-Session.

	Returns:
		list[User]: Die vorhandenen oder neu angelegten Testuser.
	"""

	users: list[User] = []

	for user_data in TEST_USERS:
		existing_user = session.exec(
			select(User).where(User.contract_number == user_data["contract_number"])
		).first()

		if existing_user is None:
			existing_user = User(
				first_name=user_data["first_name"],
				last_name=user_data["last_name"],
				contract_number=user_data["contract_number"],
				password_hash=user_data["password_hash"],
			)
			# Commit je Benutzer, damit user_id direkt fuer Konten verfuegbar ist.
			session.add(existing_user)
			session.commit()
			session.refresh(existing_user)

		users.append(existing_user)

	return users

def seed_accounts_for_users(session: Session, users: list[User]) -> None:
	"""Erzeugt pro Benutzer ein Privat- und ein Sparkonto, falls fehlend.

	Args:
		session: Aktive SQLModel-Session.
		users: Benutzerliste, fuer die Konten angelegt werden sollen.
	"""

	for user in users:
		privat_account = session.exec(
			select(Account).where(
				Account.user_id == user.user_id,
				Account.account_type == "privat",
			)
		).first()
		if privat_account is None:
			session.add(
				Account(
					account_type="privat",
					balance=0.0,
					status="aktiv",
					iban=f"DE00{user.contract_number.replace('-', '')}01",
					user_id=user.user_id,
				)
			)

		spar_account = session.exec(
			select(Account).where(
				Account.user_id == user.user_id,
				Account.account_type == "spar",
			)
		).first()
		if spar_account is None:
			session.add(
				Account(
					account_type="spar",
					balance=0.0,
					status="aktiv",
					iban=f"DE00{user.contract_number.replace('-', '')}02",
					user_id=user.user_id,
				)
			)

	session.commit()


def seed_database() -> None:
	"""Fuehrt den kompletten Seed-Prozess in korrekter Reihenfolge aus.

	Ablauf:
		1. Tabellen anlegen.
		2. Kategorien anlegen.
		3. Testuser sicherstellen.
		4. Konten je Testuser sicherstellen.
	"""

	create_db_and_tables()
	with Session(engine) as session:
		seed_categories(session)
		users = seed_users(session)
		seed_accounts_for_users(session, users)


if __name__ == "__main__":
	"""Ermoeglicht das manuelle Starten des Seedings per Skriptaufruf."""

	seed_database()
