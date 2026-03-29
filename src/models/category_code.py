from __future__ import annotations

from enum import Enum


class CategoryCode(str, Enum):
    TRANSPORT = "Transport"
    SHOPPING = "Einkaeufe"
    INSURANCE = "Versicherungen"
    RENT = "Miete"
    TAXES = "Steuern"
    LEISURE = "Freizeit"
    SAVINGS = "Sparen"
    WELL_BEING = "Well being"
    INTERNAL_TRANSFER = "Kontuebertrag"
    OTHER = "Sonstiges"
