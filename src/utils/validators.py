from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import date


# Prueft die Passwortregeln gemaess Spezifikation.
def validate_password_rules(password: str) -> None:
	if len(password) < 8 or not re.search(r"[^A-Za-z0-9]", password):
		raise ValueError(
			"Passwort ungueltig: min. 8 Zeichen und 1 Sonderzeichen erforderlich"
		)


# Erstellt einen sicheren Passwort-Hash mit Salt (PBKDF2-HMAC).
def hash_password(password: str) -> str:
	validate_password_rules(password)
	salt = secrets.token_hex(16)
	digest = hashlib.pbkdf2_hmac(
		"sha256",
		password.encode("utf-8"),
		salt.encode("utf-8"),
		200_000,
	)
	return f"{salt}${digest.hex()}"


# Vergleicht ein Passwort gegen einen gespeicherten Salt$Hash-Wert.
def verify_password(password: str, stored_hash: str) -> bool:
	parts = stored_hash.split("$", 1)
	if len(parts) != 2:
		return False
	salt, expected_hex = parts
	calculated_hex = hashlib.pbkdf2_hmac(
		"sha256",
		password.encode("utf-8"),
		salt.encode("utf-8"),
		200_000,
	).hex()
	return hmac.compare_digest(calculated_hex, expected_hex)


# Validiert eine Schweizer IBAN in einem pragmatischen, strengen Format.
def validate_iban(target_iban: str) -> None:
	normalized = target_iban.replace(" ", "").upper()
	if re.fullmatch(r"CH\d{19}", normalized) is None:
		raise ValueError("Ungültige IBAN")


# Validiert den Transaktionstyp gegen die erlaubten Werte.
def validate_transaction_type(transaction_type: str) -> None:
	if transaction_type not in {"income", "expense"}:
		raise ValueError(
			"Ungültiger Transaktionstyp: erlaubt sind income und expense"
		)


# Validiert, dass ein Betrag strikt groesser als 0 ist.
def validate_positive_amount(amount: float) -> None:
	if amount <= 0:
		raise ValueError("Betrag muss groesser als 0 sein")


# Validiert Monat und Jahr eines Budgets.
def validate_budget_month_year(month: int, year: int) -> None:
	if month < 1 or month > 12 or year < 1900 or year > 9999:
		raise ValueError("Ungültiger Monat oder Jahr")


# Validiert das Intervall fuer wiederkehrende Zahlungen.
def validate_recurring_interval(interval: str) -> None:
	if interval not in {"monthly", "yearly"}:
		raise ValueError(
			"Ungueltiges Intervall: erlaubt sind monthly und yearly"
		)


# Validiert die Exactly-one-Regel fuer Transaktionsquellen.
def validate_exactly_one_source(
	account_id: int | None,
	card_id: int | None,
	creditcard_id: int | None,
) -> None:
	set_sources = sum(value is not None for value in (account_id, card_id, creditcard_id))
	if set_sources != 1:
		raise ValueError(
			"Genau eine Belastungsquelle muss gesetzt sein: account_id, card_id oder creditcard_id"
		)


# Validiert, dass ein Datumsintervall logisch korrekt ist.
def validate_date_range(start_date: date, end_date: date) -> None:
	if start_date > end_date:
		raise ValueError("Ungueltiger Datumsbereich: start_date darf nicht nach end_date liegen")
