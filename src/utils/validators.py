"""src.utils.validators

Dieses Modul gehoert zur **Utils-Schicht**.

=== WAS MACHT DIESE DATEI? ===
Sie enthaelt kleine, wiederverwendbare Funktionen fuer zwei Aufgaben:

    1. VALIDIERUNG (Regelpruefung):
       Prueft ob Eingaben den Geschaeftsregeln entsprechen.
       Wenn nicht → ValueError mit erklaerenden Text.

    2. SICHERHEIT (Passwort-Hashing):
       Speichert Passwoerter NIE im Klartext, sondern als Hash.
       PBKDF2 mit 200.000 Iterationen macht Brute-Force-Angriffe sehr langsam.

=== WELCHE FUNKTIONEN GIBT ES? ===
    validate_password_rules(password)     → mind. 8 Zeichen + 1 Sonderzeichen
    hash_password(password)               → Klartext → "salt$hash" (PBKDF2)
    verify_password(password, stored)     → prueft Login-Eingabe gegen gespeicherten Hash
    generate_ch_iban(bank_code, acct)     → erzeugt eine gueltige CH-IBAN (Modulo-97)
    validate_iban(iban)                   → prueft CH + 19 Ziffern
    validate_transaction_type(type)       → nur "income" oder "expense" erlaubt
    validate_positive_amount(amount)      → Betrag muss > 0 sein
    validate_budget_month_year(m, y)      → Monat 1-12, Jahr 1900-9999
    validate_recurring_interval(interval) → nur "monthly" oder "yearly" erlaubt
    validate_exactly_one_source(...)      → Exactly-one-Regel fuer Transaktionsquellen
    validate_date_range(start, end)       → start darf nicht nach end liegen

=== PASSWORT-SICHERHEIT: WARUM PBKDF2? ===
Ein direktes MD5/SHA256 wuerde in Millisekunden millionen von Passwoertern
testen. PBKDF2 mit 200.000 Iterationen macht jeden Test ~200.000x langsamer:
    - Normaler Login: kaum merklich (< 1 Sekunde)
    - Angreifer mit 1 Mio. Passwoertern: dauert statt 1 Sekunde 2+ Tage

Format: "salt$hash"
    salt = zufaellige 32 Zeichen (verhindert, dass gleiche Passwoerter
           den gleichen Hash haben → Rainbow-Table-Angriffe wirkungslos)
    hash = PBKDF2-HMAC-SHA256 mit dem Salt als "Schluessel"

=== EXACTLY-ONE-REGEL ===
Eine Transaktion darf nur EINE Belastungsquelle haben:
    account_id   → Kontobelastung
    card_id      → Debitkarte
    creditcard_id→ Kreditkarte
`validate_exactly_one_source` stellt sicher, dass genau einer dieser Werte
gesetzt ist (nicht null, nicht zwei auf einmal).

=== WER NUTZT DIESE FUNKTIONEN? ===
    hash_password / verify_password:     auth_service.py (Login, Passwortaenderung)
    validate_password_rules:             auth_service.py (Passwort setzen)
    generate_ch_iban:                    account_service.py, seed.py
    validate_iban:                       transaction_service.py, payment_service.py
    validate_transaction_type:           transaction_service.py
    validate_positive_amount:            transaction_service.py, budget_service.py
    validate_exactly_one_source:         transaction_service.py
    validate_date_range:                 dashboard_service.py, transaction_service.py
    validate_budget_month_year:          budget_service.py
    validate_recurring_interval:         recurring_service.py

=== ARCHITEKTUR-KETTE ===
    Services (services/*.py) → validators.py → ValueError falls ungueltig
                                              → gesicherter Wert falls OK
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import date


# Prueft die Passwortregeln gemaess Spezifikation.
def validate_password_rules(password: str) -> None:
	"""Prüft, ob ein Passwort die Minimalregeln erfüllt.

	Diese Funktion wirft absichtlich eine Exception (statt True/False zurückzugeben),
	weil die aufrufende Logik (z. B. Service beim Registrieren) dann den Fehlertext
	direkt an den User weitergeben kann.

	Args:
		password: Das Passwort im Klartext (so wie der User es eingegeben hat).

	Raises:
		ValueError: Wenn das Passwort zu kurz ist oder kein Sonderzeichen enthält.
	"""
	if len(password) < 8 or not re.search(r"[^A-Za-z0-9]", password):
		raise ValueError(
			"Passwort ungueltig: min. 8 Zeichen und 1 Sonderzeichen erforderlich"
		)


# Erstellt einen sicheren Passwort-Hash mit Salt (PBKDF2-HMAC).
def hash_password(password: str) -> str:
	"""Erzeugt einen sicheren, gespeicherten Passwort-Hash im Format ``salt$hash``.

	Wichtig: Wir speichern **niemals** das echte Passwort in der Datenbank.
	Stattdessen speichern wir einen Hash, der aus Passwort + zufälligem Salt
	berechnet wird. PBKDF2 (Key-Derivation-Function) macht diese Berechnung
	absichtlich langsam, damit ein Angreifer nicht schnell Millionen Passwörter
	durchprobieren kann.

	Args:
		password: Das Passwort im Klartext.

	Returns:
		Ein String im Format ``<salt>$<hashhex>``.

	Raises:
		ValueError: Wenn das Passwort die Regeln nicht erfüllt.
	"""
	# Erst prüfen wir die Passwort-Regeln, damit wir nur „brauchbare" Passwörter hashen.
	validate_password_rules(password)
	# Salt = zufälliger Zusatz, damit gleiche Passwörter nicht den gleichen Hash ergeben.
	salt = secrets.token_hex(16)
	# PBKDF2-HMAC: viele Iterationen (200'000) machen Brute-Force-Angriffe teurer.
	digest = hashlib.pbkdf2_hmac(
		"sha256",
		password.encode("utf-8"),
		salt.encode("utf-8"),
		200_000,
	)
	return f"{salt}${digest.hex()}"


# Vergleicht ein Passwort gegen einen gespeicherten Salt$Hash-Wert.
def verify_password(password: str, stored_hash: str) -> bool:
	"""Prüft, ob ein eingegebenes Passwort zu einem gespeicherten Hash passt.

	Args:
		password: Passwort im Klartext (Login-Eingabe).
		stored_hash: Gespeicherter Wert aus der DB im Format ``salt$hash``.

	Returns:
		True, wenn das Passwort korrekt ist, sonst False.
	"""
	# Das gespeicherte Format ist „salt$hash". Wenn das Format kaputt ist: Login ablehnen.
	parts = stored_hash.split("$", 1)
	if len(parts) != 2:
		return False
	salt, expected_hex = parts
	# Wir rechnen den Hash mit dem gleichen Salt neu aus und vergleichen danach.
	calculated_hex = hashlib.pbkdf2_hmac(
		"sha256",
		password.encode("utf-8"),
		salt.encode("utf-8"),
		200_000,
	).hex()
	# compare_digest vergleicht „zeitkonstant" (schützt besser vor Timing-Angriffen).
	return hmac.compare_digest(calculated_hex, expected_hex)


# Generiert eine gueltige Schweizer IBAN aus Bankleitzahl (5 Stellen) und Kontonummer (12 Stellen).
def generate_ch_iban(bank_code: str, account_num: str) -> str:
	"""Generiert eine Schweizer IBAN (CH) aus Bankcode und Kontonummer.

	Das ist eine vereinfachte/„pragmatische" Generierung für Demo-Daten.
	Die Prüfziffern werden mit dem Standard-Modulo-97-Verfahren berechnet.

	Args:
		bank_code: Bankleitzahl (erwartet 5 Ziffern als String).
		account_num: Kontonummer (erwartet 12 Ziffern als String).

	Returns:
		Eine IBAN im Format ``CHkk<bank_code><account_num>``.
	"""
	bban = f"{bank_code}{account_num}"
	# Für die Prüfziffer-Berechnung hängt man den Ländercode „CH" (als Zahlen) ans Ende.
	# CH -> 12 17 (A=10, B=11, ..., Z=35) und „00" als Platzhalter für die Prüfziffer.
	numeric = bban + "121700"  # CH=1217, Prüfziffern-Platzhalter 00
	check = 98 - (int(numeric) % 97)
	return f"CH{check:02d}{bban}"


# Validiert eine Schweizer IBAN in einem pragmatischen, strengen Format.
def validate_iban(target_iban: str) -> None:
	"""Validiert, ob eine Eingabe wie eine Schweizer IBAN aussieht.

	Die App verwendet hier bewusst eine einfache, strenge Regel:
	- nur CH-IBANs
	- genau 21 Zeichen ohne Leerzeichen (CH + 19 Ziffern)

	Args:
		target_iban: Die IBAN-Eingabe des Users.

	Raises:
		ValueError: Wenn Format oder Länge nicht passen.
	"""
	# Normalisieren, damit „ch12 345..." auch geprüft werden kann.
	normalized = target_iban.replace(" ", "").upper()
	if re.fullmatch(r"CH\d{19}", normalized) is None:
		raise ValueError("Ungültige IBAN")


# Validiert den Transaktionstyp gegen die erlaubten Werte.
def validate_transaction_type(transaction_type: str) -> None:
	"""Validiert, ob der Transaktionstyp erlaubt ist.

	Args:
		transaction_type: Erwartet ``"income"`` oder ``"expense"``.

	Raises:
		ValueError: Wenn ein anderer Wert übergeben wird.
	"""
	if transaction_type not in {"income", "expense"}:
		raise ValueError(
			"Ungültiger Transaktionstyp: erlaubt sind income und expense"
		)


# Validiert, dass ein Betrag strikt groesser als 0 ist.
def validate_positive_amount(amount: float) -> None:
	"""Validiert, dass ein Betrag größer als 0 ist.

	Args:
		amount: Geldbetrag.

	Raises:
		ValueError: Wenn ``amount`` kleiner/gleich 0 ist.
	"""
	if amount <= 0:
		raise ValueError("Betrag muss groesser als 0 sein")


# Validiert Monat und Jahr eines Budgets.
def validate_budget_month_year(month: int, year: int) -> None:
	"""Validiert, ob Monat und Jahr in einem plausiblen Bereich liegen.

	Args:
		month: 1 bis 12.
		year: Jahrzahl (z. B. 2026).

	Raises:
		ValueError: Wenn Monat oder Jahr außerhalb der erlaubten Grenzen liegt.
	"""
	if month < 1 or month > 12 or year < 1900 or year > 9999:
		raise ValueError("Ungültiger Monat oder Jahr")


# Validiert das Intervall fuer wiederkehrende Zahlungen.
def validate_recurring_interval(interval: str) -> None:
	"""Validiert das Intervall für Daueraufträge.

	Args:
		interval: Erwartet ``"monthly"`` oder ``"yearly"``.

	Raises:
		ValueError: Wenn ein anderer Wert übergeben wird.
	"""
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
	"""Prüft die Regel: Genau eine Belastungsquelle muss gesetzt sein.

	Warum diese Regel wichtig ist:
	Eine Transaktion darf nicht gleichzeitig „von Konto *und* von Karte" stammen,
	sonst wüssten wir nicht, wo wir den Betrag abbuchen sollen und es könnte zu
	doppelten Abbuchungen kommen.

	Args:
		account_id: Konto-ID, wenn die Transaktion ein Konto belastet.
		card_id: Debitkarten-ID, wenn die Transaktion über eine Debitkarte läuft.
		creditcard_id: Kreditkarten-ID, wenn die Transaktion über eine Kreditkarte läuft.

	Raises:
		ValueError: Wenn keine oder mehr als eine Quelle gesetzt ist.
	"""
	# Wir zählen, wie viele der drei Werte NICHT None sind.
	set_sources = sum(value is not None for value in (account_id, card_id, creditcard_id))
	if set_sources != 1:
		raise ValueError(
			"Genau eine Belastungsquelle muss gesetzt sein: account_id, card_id oder creditcard_id"
		)


# Validiert, dass ein Datumsintervall logisch korrekt ist.
def validate_date_range(start_date: date, end_date: date) -> None:
	"""Validiert, dass ein Startdatum nicht nach dem Enddatum liegt.

	Args:
		start_date: Anfang des Zeitraums.
		end_date: Ende des Zeitraums.

	Raises:
		ValueError: Wenn ``start_date`` größer als ``end_date`` ist.
	"""
	# Diese Regel schützt Filter/Reports vor „umgedrehten" Zeiträumen.
	if start_date > end_date:
		raise ValueError("Ungueltiger Datumsbereich: start_date darf nicht nach end_date liegen")
