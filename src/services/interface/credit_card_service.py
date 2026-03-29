from __future__ import annotations

from abc import ABC, abstractmethod

from ...models import CreditCard


class CreditCardService(ABC):
    @abstractmethod
    def order_credit_card(self, user_id: int, desired_limit: float) -> CreditCard:
        raise NotImplementedError

    @abstractmethod
    def block_credit_card(self, creditcard_id: int) -> CreditCard:
        raise NotImplementedError

    @abstractmethod
    def replace_credit_card(self, creditcard_id: int) -> CreditCard:
        raise NotImplementedError
