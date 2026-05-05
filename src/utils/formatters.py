"""Formatierungs-Helfer (Utils-Schicht).

Dieses Modul sammelt kleine Funktionen, die Daten „schön“ für die Oberfläche
formatieren (z. B. Datumsanzeige oder Übersetzungen von Codes zu Labels).
Es gehört zur Utils-Schicht und wird typischerweise von Views/Controllers
verwendet, damit UI-Code nicht überall Formatierungslogik dupliziert.
"""

from __future__ import annotations

from datetime import date


TRANSACTION_TYPE_LABELS = {
	"expense": "Ausgabe",
	"income": "Einkommen",
}


def format_date_dmy(value: date) -> str:
	"""Formatiert ein Datum als Tag-Monat-Jahr.

	Args:
		value: Ein Python-``date``-Objekt.

	Returns:
		Datum als String im Format ``DD-MM-YYYY``.
	"""
	return value.strftime("%d-%m-%Y")


def format_transaction_type(transaction_type: str) -> str:
	"""Übersetzt einen internen Transaktions-Typcode in ein deutsches Label.

	Die Datenbank/Services arbeiten mit kurzen Codes (z. B. ``income``),
aber die UI soll lesbare Begriffe anzeigen.

	Args:
		transaction_type: Interner Typcode (z. B. ``"expense"`` oder ``"income"``).

	Returns:
		Ein deutsches Label (z. B. ``"Ausgabe"``) oder den Originalwert,
		falls der Code unbekannt ist.
	"""
	return TRANSACTION_TYPE_LABELS.get(transaction_type, transaction_type)