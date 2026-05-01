from __future__ import annotations

from src.services.category_service import category_service


class CategoryController:
    def list_categories(self) -> dict:
        try:
            categories = category_service.list_categories()
            return {c.category_id: c.name for c in categories}
        except Exception:
            return {}


category_controller = CategoryController()
