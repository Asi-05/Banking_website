import pytest

from src.utils.validators import validate_iban


def test_validate_iban_format_tc005() -> None:
    # Gueltige CH-IBAN darf keinen Fehler werfen.
    validate_iban("CH56 0483 5012 3456 7800 9")

    # Falsches Laenderpraefix muss abgelehnt werden.
    with pytest.raises(ValueError):
        validate_iban("DE89370400440532013000")

    # Zu kurze CH-IBAN muss abgelehnt werden.
    with pytest.raises(ValueError):
        validate_iban("CH123")