"""src.utils.formatters

Dieses Modul gehoert zur **Utils-Schicht**.

=== WAS MACHT DIESE DATEI? ===
Sie sammelt kleine, wiederverwendbare Funktionen, die Daten fuer die Anzeige
in der Benutzeroberflaeche (UI) "schoen" formatieren:

    format_date_dmy(value)          → date-Objekt → "DD-MM-YYYY" (z.B. "11-05-2026")
    format_transaction_type(code)   → "expense" → "Ausgabe", "income" → "Einkommen"
    format_chf(value)               → float → "8'500.00" (Schweizer Tausendertrennzeichen)

=== WARUM EINE EIGENE DATEI DAFUER? ===
Ohne diese Helfer wuerde in jeder View die gleiche Formatierungslogik stehen:
    - "Wie zeige ich CHF 8500 an?" → 3x dieselbe f-String-Logik
    - "Wie uebersetze ich 'expense' ins Deutsche?" → 5x dasselbe Dictionary

DRY-Prinzip: "Don't Repeat Yourself". Eine aenderung hier verbessert alle
Anzeigen in der gesamten App gleichzeitig.

=== WER NUTZT DIESE FUNKTIONEN? ===
    format_chf:              dashboard_view.py (Kontostand, Einnahmen, Ausgaben)
    format_transaction_type: wird von Views genutzt, die Typen anzeigen
    format_date_dmy:         Views, die ein lesbares Datum brauchen

=== ARCHITEKTUR-KETTE ===
    Views (ui/views/*.py) → formatters.py → formatierter String → NiceGUI ui.label(...)
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


def format_chf(value: float) -> str:
	"""Formatiert einen Geldbetrag im CHF-Format mit Schweizer Tausendertrennzeichen.

	Args:
		value: Geldbetrag.

	Returns:
		Formatierter Betrag, z. B. ``8'500.00``.
	"""
	return f"{value:,.2f}".replace(",", "'")