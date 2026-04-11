from datetime import date

from sqlmodel import SQLModel, Session, create_engine

from src.domain.models import Category, Transaction


# TC_007: Persistenztest fuer Transaktion mit korrekter Kategorie-Referenz.
def test_db_persist_transaction_with_category() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        category = Category(category_id=2, name="Einkaeufe")
        session.add(category)
        session.commit()

        transaction = Transaction(
            amount=45.90,
            date=date(2026, 4, 11),
            type="expense",
            category_id=2,
            note="Migros Einkauf",
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)

        loaded = session.get(Transaction, transaction.transaction_id)
        assert loaded is not None
        assert loaded.category_id == 2
        assert loaded.category is not None
        assert loaded.category.name == "Einkaeufe"

    SQLModel.metadata.drop_all(engine)
