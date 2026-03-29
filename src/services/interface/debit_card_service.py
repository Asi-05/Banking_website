from __future__ import annotations

from abc import ABC, abstractmethod

from ...models import DebitCard


class DebitCardService(ABC):
    @abstractmethod
    def order_card(self, account_id: int) -> DebitCard:
        raise NotImplementedError

    @abstractmethod
    def block_card(self, card_id: int) -> DebitCard:
        raise NotImplementedError

    @abstractmethod
    def replace_card(self, card_id: int) -> DebitCard:
        raise NotImplementedError
