from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Session


class AuthService(ABC):
    @abstractmethod
    def login(self, contract_number: str, password: str) -> Session:
        raise NotImplementedError

    @abstractmethod
    def logout(self, token: str) -> None:
        raise NotImplementedError
