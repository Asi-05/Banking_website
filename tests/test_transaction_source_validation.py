import pytest

from src.utils.validators import validate_exactly_one_source


@pytest.mark.parametrize(
    "account_id, card_id, creditcard_id, should_raise",
    [
        (1, 1, None, True),
        (None, None, None, True),
        (1, None, None, False),
    ],
)
def test_transaction_source_validation(
    account_id: int | None,
    card_id: int | None,
    creditcard_id: int | None,
    should_raise: bool,
) -> None:
    if should_raise:
        with pytest.raises(ValueError):
            validate_exactly_one_source(account_id, card_id, creditcard_id)
    else:
        validate_exactly_one_source(account_id, card_id, creditcard_id)
