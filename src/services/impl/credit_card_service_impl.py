from __future__ import annotations

"""Unabhaengige Kreditkarten-Operationen: bestellen, sperren, ersetzen."""

from ...exceptions import CardOperationError, NotFoundError, ValidationError
from ...models import CardStatus, CreditCard
from ..interface.credit_card_service import CreditCardService
from .shared import InMemoryStore, mask_card_number


class InMemoryCreditCardService(CreditCardService):
    """Implementiert Regeln fuer das Kreditkarten-Management im In-Memory-Speicher."""

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def order_credit_card(self, user_id: int, desired_limit: float) -> CreditCard:
        """Erstellt eine neue, unabhaengige Kreditkarte mit dem gewuenschten Limit."""

        if user_id not in self.store.users:
            raise NotFoundError(f"User {user_id} not found")
        if desired_limit <= 0:
            raise ValidationError("desired_limit must be greater than 0")

        creditcard_id = self.store.next_credit_card_id()
        credit_card = CreditCard(
            creditcard_id=creditcard_id,
            user_id=user_id,
            card_number_masked=mask_card_number(creditcard_id),
            credit_limit=desired_limit,
            used_balance=0.0,
            status=CardStatus.ACTIVE,
        )
        self.store.credit_cards[credit_card.creditcard_id] = credit_card
        return credit_card

    def block_credit_card(self, creditcard_id: int) -> CreditCard:
        """Sperrt eine bestehende Kreditkarte sofort."""

        card = self.store.credit_cards.get(creditcard_id)
        if card is None:
            raise NotFoundError(f"CreditCard {creditcard_id} not found")
        card.status = CardStatus.BLOCKED
        return card

    def replace_credit_card(self, creditcard_id: int) -> CreditCard:
        """Ersetzt eine gesperrte Kreditkarte und behaelt Limit sowie Nutzung bei."""

        old_card = self.store.credit_cards.get(creditcard_id)
        if old_card is None:
            raise NotFoundError(f"CreditCard {creditcard_id} not found")
        if old_card.status != CardStatus.BLOCKED:
            raise CardOperationError("Only blocked credit cards can be replaced")

        old_card.status = CardStatus.REPLACED
        new_id = self.store.next_credit_card_id()
        new_card = CreditCard(
            creditcard_id=new_id,
            user_id=old_card.user_id,
            card_number_masked=mask_card_number(new_id),
            credit_limit=old_card.credit_limit,
            used_balance=old_card.used_balance,
            status=CardStatus.ACTIVE,
        )
        self.store.credit_cards[new_card.creditcard_id] = new_card
        return new_card
