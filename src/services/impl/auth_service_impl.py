from __future__ import annotations

"""Authentifizierungslogik fuer vordefinierte Nutzer und Session-Verwaltung."""

from datetime import datetime, timedelta
import secrets

from ...exceptions import UnauthorizedError, ValidationError
from ...models import Session, User
from ..interface.auth_service import AuthService
from .shared import InMemoryStore, hash_password, validate_password_policy


class InMemoryAuthService(AuthService):
    """Implementiert Login/Logout auf Basis des In-Memory-Speichers."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store
        self._recurring_service = None

    def set_recurring_service(self, recurring_service) -> None:
        """Setzt den Service fuer Dauerauftraege, um faellige Jobs beim Login auszufuehren."""

        self._recurring_service = recurring_service

    def create_predefined_user(self, contract_number: str, password: str, full_name: str) -> User:
        """Erstellt ein vordefiniertes Benutzerkonto (ohne Selbstregistrierung)."""

        if contract_number in self.store.users_by_contract:
            raise ValidationError("contract_number already exists")
        validate_password_policy(password)

        user = User(
            user_id=self.store.next_user_id(),
            contract_number=contract_number,
            password_hash=hash_password(password),
            full_name=full_name,
        )
        self.store.users[user.user_id] = user
        self.store.users_by_contract[contract_number] = user.user_id
        return user

    def login(self, contract_number: str, password: str) -> Session:
        """Prueft Zugangsdaten und erzeugt ein Session-Token."""

        user_id = self.store.users_by_contract.get(contract_number)
        if user_id is None:
            raise UnauthorizedError("Invalid contract number or password")

        user = self.store.users[user_id]
        if user.password_hash != hash_password(password):
            raise UnauthorizedError("Invalid contract number or password")

        now = datetime.utcnow()
        session = Session(
            token=secrets.token_urlsafe(24),
            user_id=user.user_id,
            created_at=now,
            expires_at=now + timedelta(hours=12),
        )
        self.store.sessions[session.token] = session

        # Anforderung: Faellige Dauerauftraege nach erfolgreichem Login verarbeiten.
        if self._recurring_service is not None:
            self._recurring_service.process_due_recurring_payments(user.user_id, now.date())

        return session

    def logout(self, token: str) -> None:
        """Macht ein Session-Token ungueltig, falls es existiert."""

        self.store.sessions.pop(token, None)
