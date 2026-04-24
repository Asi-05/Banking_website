from __future__ import annotations

import secrets
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.user_repository import UserRepository
from src.services.recurring_service import recurring_service

# 1. HIER HAST DU DEN IMPORT ERGÄNZT:
from src.utils.validators import verify_password, hash_password


class AuthService:
    def login(self, contract_number: str, password: str) -> dict:
        with Session(engine) as session:
            user_repository = UserRepository(session)
            user = user_repository.get_by_contract_number(contract_number)
            if user is None:
                raise ValueError("Ungueltige Anmeldedaten")

            stored_hash = user.password_hash
            password_ok = (
                verify_password(password, stored_hash)
                if "$" in stored_hash
                else stored_hash == password
            )
            if not password_ok:
                raise ValueError("Ungueltige Anmeldedaten")

            # 2. HIER MUSST DU DIESE LOGIK EINBAUEN:
            # Das ist der Moment, in dem das bereitgelegte Werkzeug benutzt wird!
            if "$" not in stored_hash:
                user.password_hash = hash_password(password)
                session.add(user)
                session.commit()

        executed_recurring = recurring_service.process_due_recurring_on_login(
            user.user_id,
            date.today(),
        )
        return {
            "success": True,
            "auth_token": secrets.token_urlsafe(24),
            "user_id": user.user_id,
            "executed_recurring": executed_recurring,
        }

auth_service = AuthService()