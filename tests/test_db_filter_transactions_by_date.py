from datetime import date

from sqlmodel import SQLModel, Session, create_engine

from src.data_access.repositories.transaction_repository import TransactionRepository
from src.domain.models import Category, Transaction


# TC_008: Datumsfilter muss Grenzwerte inklusiv behandeln.
def test_db_filter_transactions_by_date() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Category(category_id=2, name="Einkaeufe"))
        session.commit()

        transactions = [
            Transaction(amount=10.0, date=date(2026, 2, 15), type="expense", category_id=2, note="TX1"),
            Transaction(amount=20.0, date=date(2026, 3, 1), type="expense", category_id=2, note="TX2"),
            Transaction(amount=30.0, date=date(2026, 3, 15), type="expense", category_id=2, note="TX3"),
            Transaction(amount=40.0, date=date(2026, 3, 31), type="expense", category_id=2, note="TX4"),
            Transaction(amount=50.0, date=date(2026, 4, 1), type="expense", category_id=2, note="TX5"),
        ]
        session.add_all(transactions)
        session.commit()

        transaction_repository = TransactionRepository(session)
        filtered = transaction_repository.filter_transactions(
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )

        assert len(filtered) == 3
        assert {tx.note for tx in filtered} == {"TX2", "TX3", "TX4"}

    SQLModel.metadata.drop_all(engine)
