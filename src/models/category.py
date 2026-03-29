from __future__ import annotations

from dataclasses import dataclass

from .category_code import CategoryCode


@dataclass
class Category:
    category_id: int
    code: CategoryCode
    display_name: str
