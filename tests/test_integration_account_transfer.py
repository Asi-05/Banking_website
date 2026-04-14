from datetime import date
import importlib

from sqlmodel import SQLModel, Session, create_engine, select

from src.domain.models import Account, Category, Transfer, User

payment_service_module = importlib.import_module("src.services.payment_service")
transaction_service_module = importlib.import_module("src.services.transaction_service")


# TC_010: Vollstaendiger Umbuchungs-Flow zwischen zwei Konten.
def test_integration_account_transfer(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr(payment_service_module, "engine", engine)
    monkeypatch.setattr(transaction_service_module, "engine", engine)

    with Session(engine) as session:
        user = User(
            first_name="Max",
            last_name="Muster",
            password_hash="hash",
            contract_number="BB-200001",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(Category(category_id=1, name="Transfer"))

        account_a = Account(
            account_type="privat",
            balance=1000.0,
            iban="CH5604835012345678009",
            user_id=user.user_id,
        )
        account_b = Account(
            account_type="sparkonto",
            balance=500.0,
            iban="CH9300762011623852957",
            user_id=user.user_id,
        )
        session.add(account_a)
        session.add(account_b)
        session.commit()
        session.refresh(account_a)
        session.refresh(account_b)

        transfers_before = len(session.exec(select(Transfer)).all())

    transfer = payment_service_module.payment_service.create_transfer(
        {
            "from_account_id": account_a.account_id,
            "to_account_id": account_b.account_id,
            "amount": 100.0,
            "category_id": 1,
            "date": date(2026, 4, 11),
        }
    )

    with Session(engine) as session:
        updated_a = session.get(Account, account_a.account_id)
        updated_b = session.get(Account, account_b.account_id)
        transfers_after = len(session.exec(select(Transfer)).all())

        assert transfer.transfer_id is not None
        assert updated_a is not None
        assert updated_b is not None
        assert updated_a.balance == 900.0
        assert updated_b.balance == 600.0
        assert transfers_after == transfers_before + 1

    SQLModel.metadata.drop_all(engine)
