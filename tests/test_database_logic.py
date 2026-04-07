import pytest
from datetime import date
from sqlmodel import Session, create_engine, SQLModel, select
from src.domain.models import User, Account, Budget, Transaction
from sqlalchemy.exc import IntegrityError

# Setup: Wir nutzen eine SQLite Datenbank im Arbeitsspeicher für die Tests
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

# TEST 1: Prüft die User-Erstellung und Felder
def test_create_user(session: Session):
    user = User(
        first_name="Hermann", 
        last_name="Grieder", 
        contract_number="BB-100001", 
        password_hash="hash123"
    )
    session.add(user)
    session.commit()
    
    db_user = session.exec(select(User).where(User.contract_number == "BB-100001")).one()
    assert db_user.first_name == "Hermann"
    assert db_user.password_hash == "hash123"

# TEST 2: Prüft die Unique-Constraint Regel beim Budget (Wichtig!)
def test_budget_unique_constraint(session: Session):
    # Erstes Budget anlegen
    b1 = Budget(user_id=1, month=5, year=2026, category_id=1, limit_amount=500.0)
    session.add(b1)
    session.commit()

    # Zweites Budget mit identischer Kombination (user, month, year, category)
    # Dies MUSS einen Fehler werfen gemäß Technical Design
    b2 = Budget(user_id=1, month=5, year=2026, category_id=1, limit_amount=300.0)
    session.add(b2)
    
    with pytest.raises(IntegrityError):
        session.commit()

# TEST 3: Prüft die Exactly-One-Rule (Struktur-Check)
def test_transaction_sources(session: Session):
    # Transaktion über ein Konto
    t1 = Transaction(amount=50.0, date=date(2026, 5, 20), type="expense", category_id=1, account_id=1)
    session.add(t1)
    session.commit()
    
    assert t1.account_id is not None
    assert t1.card_id is None