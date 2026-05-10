"""Initialdaten (Seeding) für die lokale Entwicklungsdatenbank.

Dieses Modul legt beim ersten Start Demo-Daten an: fixe Kategorien sowie
vordefinierte Test-User mit je zwei Konten und je einer Debit-/Kreditkarte.
Es gehört zur Data-Access-Schicht, weil es direkt mit der Datenbank arbeitet.
Die Funktionen sind so geschrieben, dass man sie mehrfach ausführen kann,
ohne doppelte Einträge zu erzeugen ("idempotent").
"""

from datetime import date

from sqlmodel import Session, select

from src.data_access.db import create_db_and_tables, engine
from src.domain.models import Account, Category, CreditCard, DebitCard, Transaction, User
from src.utils.validators import generate_ch_iban


# Fixed categories from the technical design (must be seeded on first start)
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
	"Gehalt",
]


INITIAL_USER_BALANCE = 5000.0
INITIAL_SAVINGS_BALANCE = 10000.0


# Exactly two predefined test users
TEST_USERS = [
	{
		"first_name": "Hermann",
		"last_name": "Grieder",
		"contract_number": "BB-100001",
		"password_hash": "Dummy_hash_1",
	},
	{
		"first_name": "Felix",
		"last_name": "Haerer",
		"contract_number": "BB-100002",
		"password_hash": "Dummy_hash_2",
	},
]


# Add categories only when they do not exist yet
def seed_categories(session: Session) -> None:
	"""Legt die vordefinierten Kategorien an, falls sie noch fehlen.

	Args:
		session: Offene Datenbank-Session.
	"""
	for category_name in CATEGORY_NAMES:
		# Prüfe, ob es die Kategorie schon gibt (sonst würden wir Duplikate erzeugen).
		existing_category = session.exec(
			select(Category).where(Category.name == category_name)
		).first()
		if existing_category is None:
			session.add(Category(name=category_name))
	session.commit()


# Add exactly two test users if they are missing
def seed_users(session: Session) -> list[User]:
	"""Legt genau die zwei vordefinierten Test-User an (falls sie fehlen).

	Hinweis: In `TEST_USERS` steht `password_hash` als Dummy-Text.
	Echte Passwort-Hashes werden normalerweise über `hash_password()` erzeugt
	(siehe `src/utils/validators.py` und `auth_service`). Für Demo-Daten ist das
	hier absichtlich vereinfacht.

	Args:
		session: Offene Datenbank-Session.

	Returns:
		Liste der (existierenden oder neu angelegten) User-Objekte.
	"""
	users: list[User] = []

	for user_data in TEST_USERS:
		# Existiert der User mit dieser Vertragsnummer schon?
		existing_user = session.exec(
			select(User).where(User.contract_number == user_data["contract_number"])
		).first()

		if existing_user is None:
			# Neu anlegen und sofort committen, damit `user_id` erzeugt wird.
			existing_user = User(
				first_name=user_data["first_name"],
				last_name=user_data["last_name"],
				contract_number=user_data["contract_number"],
				password_hash=user_data["password_hash"],
			)
			session.add(existing_user)
			session.commit()
			session.refresh(existing_user)

		users.append(existing_user)

	return users


# For each user, create exactly one private and one savings account if missing
def seed_accounts_for_users(session: Session, users: list[User]) -> None:
	"""Legt pro User ein Privat- und ein Sparkonto an, falls sie fehlen.

	Args:
		session: Offene Datenbank-Session.
		users: Die User, für die Konten sichergestellt werden sollen.
	"""
	for user in users:
		# Prüfe, ob bereits ein Privatkonto existiert.
		privat_account = session.exec(
			select(Account).where(
				Account.user_id == user.user_id,
				Account.account_type == "privat",
			)
		).first()
		if privat_account is None:
			# IBAN wird deterministisch aus user_id + Suffix gebaut (gut für Tests/Demos).
			session.add(
				Account(
					account_type="privat",
					balance=INITIAL_USER_BALANCE,
					status="aktiv",
					iban=generate_ch_iban("09000", f"{user.user_id:010d}01"),
					user_id=user.user_id,
				)
			)

		# Prüfe, ob bereits ein Sparkonto existiert.
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
					balance=INITIAL_SAVINGS_BALANCE,
					status="aktiv",
					iban=generate_ch_iban("09000", f"{user.user_id:010d}02"),
					user_id=user.user_id,
				)
			)

	session.commit()


# For each predefined user, ensure exactly one active debit card exists
def seed_debit_cards_for_users(session: Session, users: list[User]) -> None:
	"""Stellt sicher, dass jeder Test-User eine aktive Debitkarte hat.

	Args:
		session: Offene Datenbank-Session.
		users: Die User, für die Karten sichergestellt werden sollen.
	"""
	today = date.today()
	for user in users:
		# Suche eine aktive Debitkarte, die über ein Konto diesem User gehört.
		has_active_debit = session.exec(
			select(DebitCard)
			.join(Account, Account.account_id == DebitCard.account_id)
			.where(
				Account.user_id == user.user_id,
				DebitCard.status == "aktiv",
			)
		).first()

		if has_active_debit is not None:
			continue

		# Debitkarten sollen im Demo-Setup immer ans Privatkonto gekoppelt sein.
		private_account = session.exec(
			select(Account).where(
				Account.user_id == user.user_id,
				Account.account_type == "privat",
			)
		).first()

		if private_account is None:
			continue

		session.add(
			DebitCard(
				card_number=f"420000{user.user_id:010d}",
				expire_date=date(today.year + 4, today.month, 1),
				status="aktiv",
				account_id=private_account.account_id,
			)
		)

	session.commit()


# For each predefined user, ensure exactly one active credit card exists
def seed_credit_cards_for_users(session: Session, users: list[User]) -> None:
	"""Stellt sicher, dass jeder Test-User eine aktive Kreditkarte hat.

	Args:
		session: Offene Datenbank-Session.
		users: Die User, für die Karten sichergestellt werden sollen.
	"""
	today = date.today()
	for user in users:
		# Suche eine aktive Kreditkarte des Users.
		has_active_credit = session.exec(
			select(CreditCard).where(
				CreditCard.user_id == user.user_id,
				CreditCard.status == "aktiv",
			)
		).first()

		if has_active_credit is not None:
			continue

		# Kreditkarte ist "unabhängig" (direkt am User), nicht an ein Konto gebunden.
		session.add(
			CreditCard(
				card_number=f"510000{user.user_id:010d}",
				expire_date=date(today.year + 4, today.month, 1),
				limit=5000.0,
				balance=0.0,
				status="aktiv",
				user_id=user.user_id,
			)
		)

	session.commit()


# For each predefined user, create monthly salary income transactions
def seed_monthly_income_for_users(session: Session, users: list[User]) -> None:
	"""Legt pro User eine monatliche Gehaltsbuchung von CHF 8'500 an.

	Buchungen werden für jeden Monat von Januar bis zum aktuellen Monat
	des laufenden Jahres erstellt. Die Funktion ist idempotent.

	Args:
		session: Offene Datenbank-Session.
		users: Die User, für die Gehaltsbuchungen erstellt werden sollen.
	"""
	gehalt_category = session.exec(
		select(Category).where(Category.name == "Gehalt")
	).first()
	if gehalt_category is None:
		return

	today = date.today()

	for user in users:
		privat_account = session.exec(
			select(Account).where(
				Account.user_id == user.user_id,
				Account.account_type == "privat",
			)
		).first()
		if privat_account is None:
			continue

		for month in range(1, today.month + 1):
			salary_date = date(today.year, month, 1)

			existing = session.exec(
				select(Transaction).where(
					Transaction.account_id == privat_account.account_id,
					Transaction.date == salary_date,
					Transaction.type == "income",
					Transaction.note == "Monatsgehalt",
				)
			).first()
			if existing is not None:
				continue

			session.add(Transaction(
				amount=8500.0,
				date=salary_date,
				type="income",
				note="Monatsgehalt",
				category_id=gehalt_category.category_id,
				account_id=privat_account.account_id,
			))
			privat_account.balance += 8500.0

	session.commit()


# Public function to run complete database seeding process
def seed_database() -> None:
	"""Führt den kompletten Seeding-Prozess aus (Tabellen + Demo-Daten)."""
	# Erst Tabellen sicherstellen, danach erst Daten einfügen.
	create_db_and_tables()
	with Session(engine) as session:
		seed_categories(session)
		users = seed_users(session)
		seed_accounts_for_users(session, users)
		seed_debit_cards_for_users(session, users)
		seed_credit_cards_for_users(session, users)
		seed_monthly_income_for_users(session, users)


if __name__ == "__main__":
	seed_database()
