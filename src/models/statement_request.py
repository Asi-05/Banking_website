from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class StatementRequest:
    statement_id: int
    account_id: int
    start_date: date
    end_date: date
    generated_file_path: Optional[str] = None
