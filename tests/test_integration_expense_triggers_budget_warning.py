from datetime import date
import importlib

from sqlmodel import SQLModel, Session, create_engine

from src.domain.models import Account, Category, User

budget_service_module = importlib.import_module("src.services.budget_service")
transaction_service_module = importlib.import_module("src.services.transaction_service")


# TC_011: Neue Ausgabe soll Budgetueberschreitung nach dem Speichern ausloesen.
def test_integration_expense_triggers_budget_warning(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr(budget_service_module, "engine", engine)
    monkeypatch.setattr(transaction_service_module, "engine", engine)

    with Session(engine) as session:
        user = User(
            first_name="Max",
            last_name="Budget",
            password_hash="hash",
            contract_number="BB-300001",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(Category(category_id=2, name="Einkaeufe"))

        account = Account(
            account_type="privat",
            balance=1000.0,
            iban="CH5604835012345678009",
            user_id=user.user_id,
        )
        session.add(account)
        session.commit()
        session.refresh(account)

        user_id = int(user.user_id)
        account_id = int(account.account_id)

    budget_service_module.budget_service.set_budget(
        {
            "user_id": user_id,
            "limit_amount": 500.0,
            "month": 4,
            "year": 2026,
            "category_id": 2,
        }
    )

    transaction_service_module.transaction_service.create_transaction(
        {
            "amount": 480.0,
            "type": "expense",
            "date": date(2026, 4, 10),
            "category_id": 2,
            "account_id": account_id,
        }
    )

    transaction_service_module.transaction_service.create_transaction(
        {
            "amount": 30.0,
            "type": "expense",
            "date": date(2026, 4, 11),
            "category_id": 2,
            "account_id": account_id,
        }
    )

    status = budget_service_module.budget_service.check_budget_status(
        user_id=user_id,
        month=4,
        year=2026,
        category_id=2,
    )

    assert status["current_spending"] == 510.0
    assert status["is_exceeded"] is True

    SQLModel.metadata.drop_all(engine)
