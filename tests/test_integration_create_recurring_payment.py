from datetime import date, timedelta
import importlib

from sqlmodel import SQLModel, Session, create_engine

from src.data_access.repositories.recurring_repository import RecurringRepository
from src.domain.models import Account, Category, User

recurring_service_module = importlib.import_module("src.services.recurring_service")


# TC_012: Dauerauftrag muss mit User (via Konto), Konto und Ziel-IBAN verknuepft sein.
def test_integration_create_recurring_payment(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr(recurring_service_module, "engine", engine)

    with Session(engine) as session:
        user = User(
            first_name="Max",
            last_name="Dauer",
            password_hash="hash",
            contract_number="BB-400001",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        category = Category(category_id=1, name="Sonstiges")
        session.add(category)

        account = Account(
            account_type="privat",
            balance=1000.0,
            iban="CH5604835012345678009",
            user_id=int(user.user_id),
        )
        session.add(account)
        session.commit()
        session.refresh(account)

        user_id = int(user.user_id)
        account_id = int(account.account_id)

    recurring = recurring_service_module.recurring_service.create_recurring(
        {
            "amount": 150.0,
            "category_id": 1,
            "account_id": account_id,
            "target_iban": "CH56 0483 5012 3456 7800 9",
            "interval": "monthly",
            "start_date": date.today() + timedelta(days=1),
        }
    )

    with Session(engine) as session:
        recurring_repository = RecurringRepository(session)
        reloaded = recurring_repository.get_by_id(int(recurring.recurring_id))
        by_user = recurring_repository.list_by_user(user_id)

        assert reloaded is not None
        assert reloaded.account_id == account_id
        assert reloaded.target_iban == "CH56 0483 5012 3456 7800 9"
        assert any(item.recurring_id == reloaded.recurring_id for item in by_user)

    SQLModel.metadata.drop_all(engine)
