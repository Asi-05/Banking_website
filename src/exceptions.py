"""Benutzerdefinierte Exceptions fuer die Finanzdomäne.

Diese Exception-Typen machen Fehler leichter verstaendlich und in der UI
einfacher behandelbar.
"""


class FinanceError(Exception):
    """Basis-Exception fuer Domain- und Geschaeftslogikfehler."""


class ValidationError(FinanceError):
    """Wird ausgeloest, wenn die Eingabevalidierung fehlschlaegt."""


class NotFoundError(FinanceError):
    """Wird ausgeloest, wenn eine Entitaet nicht gefunden wird."""


class UnauthorizedError(FinanceError):
    """Wird bei Authentifizierungs- oder Autorisierungsfehlern ausgeloest."""


class BusinessRuleViolation(FinanceError):
    """Wird ausgeloest, wenn eine Geschaeftsregel verletzt wird."""


class InsufficientFundsError(BusinessRuleViolation):
    """Wird ausgeloest, wenn ein Konto nicht genug Guthaben hat."""


class CreditLimitExceededError(BusinessRuleViolation):
    """Wird ausgeloest, wenn eine Kreditkartenzahlung das verfuegbare Limit ueberschreitet."""


class AccountClosureError(BusinessRuleViolation):
    """Wird ausgeloest, wenn die Voraussetzungen zum Kontoschliessen nicht erfuellt sind."""


class CardOperationError(BusinessRuleViolation):
    """Wird ausgeloest, wenn eine Kartenoperation nicht durchfuehrbar ist."""
