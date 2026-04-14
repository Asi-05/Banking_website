from __future__ import annotations

from datetime import date


TRANSACTION_TYPE_LABELS = {
	"expense": "Ausgabe",
	"income": "Einkommen",
}


def format_date_dmy(value: date) -> str:
	return value.strftime("%d-%m-%Y")


def format_transaction_type(transaction_type: str) -> str:
	return TRANSACTION_TYPE_LABELS.get(transaction_type, transaction_type)