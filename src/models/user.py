from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    contract_number: str
    password_hash: str
    full_name: str
