from datetime import date

from sqlmodel import Session, select

from src.data_access.db import create_db_and_tables, engine
from src.domain.models import Account, Category, CreditCard, DebitCard, User
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
	for category_name in CATEGORY_NAMES:
		existing_category = session.exec(
			select(Category).where(Category.name == category_name)
		).first()
		if existing_category is None:
			session.add(Category(name=category_name))
	session.commit()


# Add exactly two test users if they are missing
def seed_users(session: Session) -> list[User]:
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
			session.add(existing_user)
			session.commit()
			session.refresh(existing_user)

		users.append(existing_user)

	return users


# For each user, create exactly one private and one savings account if missing
def seed_accounts_for_users(session: Session, users: list[User]) -> None:
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
					balance=INITIAL_USER_BALANCE,
					status="aktiv",
					iban=generate_ch_iban("09000", f"{user.user_id:010d}01"),
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
					balance=INITIAL_SAVINGS_BALANCE,
					status="aktiv",
					iban=generate_ch_iban("09000", f"{user.user_id:010d}02"),
					user_id=user.user_id,
				)
			)

	session.commit()


# For each predefined user, ensure exactly one active debit card exists
def seed_debit_cards_for_users(session: Session, users: list[User]) -> None:
	today = date.today()
	for user in users:
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
	today = date.today()
	for user in users:
		has_active_credit = session.exec(
			select(CreditCard).where(
				CreditCard.user_id == user.user_id,
				CreditCard.status == "aktiv",
			)
		).first()

		if has_active_credit is not None:
			continue

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


# Public function to run complete database seeding process
def seed_database() -> None:
	create_db_and_tables()
	with Session(engine) as session:
		seed_categories(session)
		users = seed_users(session)
		seed_accounts_for_users(session, users)
		seed_debit_cards_for_users(session, users)
		seed_credit_cards_for_users(session, users)


if __name__ == "__main__":
	seed_database()
