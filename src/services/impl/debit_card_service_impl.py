from __future__ import annotations

"""Debitkarten-Operationen: bestellen, sperren und ersetzen."""

from ...exceptions import CardOperationError, NotFoundError
from ...models import AccountType, CardStatus, DebitCard
from ..interface.debit_card_service import DebitCardService
from .shared import InMemoryStore, mask_card_number


class InMemoryDebitCardService(DebitCardService):
    """Implementiert Geschaeftsregeln fuer Debitkarten im In-Memory-Speicher."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def order_card(self, account_id: int) -> DebitCard:
        """Bestellt eine Debitkarte fuer ein Privatkonto."""

        account = self.store.accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found")
        if account.account_type != AccountType.PRIVATE:
            raise CardOperationError("Debit cards can only be ordered for private accounts")

        card_id = self.store.next_debit_card_id()
        card = DebitCard(
            card_id=card_id,
            account_id=account_id,
            card_number_masked=mask_card_number(card_id),
            status=CardStatus.ACTIVE,
        )
        self.store.debit_cards[card.card_id] = card
        return card

    def block_card(self, card_id: int) -> DebitCard:
        """Sperrt eine bestehende Debitkarte sofort."""

        card = self.store.debit_cards.get(card_id)
        if card is None:
            raise NotFoundError(f"Card {card_id} not found")
        card.status = CardStatus.BLOCKED
        return card

    def replace_card(self, card_id: int) -> DebitCard:
        """Ersetzt eine gesperrte Karte durch eine neue aktive Karte."""

        old_card = self.store.debit_cards.get(card_id)
        if old_card is None:
            raise NotFoundError(f"Card {card_id} not found")
        if old_card.status != CardStatus.BLOCKED:
            raise CardOperationError("Only blocked cards can be replaced")

        old_card.status = CardStatus.REPLACED
        new_id = self.store.next_debit_card_id()
        new_card = DebitCard(
            card_id=new_id,
            account_id=old_card.account_id,
            card_number_masked=mask_card_number(new_id),
            status=CardStatus.ACTIVE,
        )
        self.store.debit_cards[new_card.card_id] = new_card
        return new_card
