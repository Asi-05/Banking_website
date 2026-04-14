from datetime import date
import importlib

from sqlmodel import SQLModel, Session, create_engine

from src.domain.models import User

dashboard_service_module = importlib.import_module("src.services.dashboard_service")


# TC_009: Leeres Dashboard darf keine Exception werfen und muss 0.0 liefern.
def test_db_empty_dashboard_behavior(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr(dashboard_service_module, "engine", engine)

    with Session(engine) as session:
        user = User(
            first_name="Neu",
            last_name="Benutzer",
            password_hash="hash",
            contract_number="BB-500001",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = int(user.user_id)

    summary = dashboard_service_module.dashboard_service.dashboard(
        user_id=user_id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
    )

    assert summary.total_balance == 0.0
    assert summary.total_income == 0.0
    assert summary.total_expenses == 0.0
    assert summary.chart_data == []

    SQLModel.metadata.drop_all(engine)
