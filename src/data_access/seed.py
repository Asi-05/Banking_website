"""src.data_access.seed

Diese Datei gehoert zur **Data-Access-Schicht**.

=== WAS MACHT DIESE DATEI? ===
`seed_database()` legt beim ersten App-Start Demo-Daten an:
    - 11 Kategorien (Lebensmittel, Transport, Freizeit, ...)
    - 2 Test-User (Hermann Grieder, Felix Haerer)
    - Pro User: 1 Privatkonto + 1 Sparkonto
    - Pro User: 1 Debitkarte (ans Privatkonto gebunden)
    - Pro User: 1 Kreditkarte
    - Hermann: Monatliche Gehaltsbuchungen (CHF 8'500 ab Januar des aktuellen Jahres)
    - Felix:   Gehaltsbuchungen (CHF 7'860, Jan-Mai 2026) + Lastschriften

=== WAS BEDEUTET "IDEMPOTENT"? ===
Idempotent = kann mehrfach ausgefuehrt werden, ohne Duplikate zu erzeugen.

    Jede Seed-Funktion prueft: "Existiert das schon?"
    - JA → nichts tun
    - NEIN → anlegen

    So kann `seed_database()` bei jedem App-Start aufgerufen werden, ohne
    doppelte User, Konten oder Kategorien zu erstellen.

=== WARUM HAT PASSWORT_HASH "DUMMY_HASH"? ===
Die Demo-User haben kein echtes gehashtes Passwort ("Dummy_hash_1").
Das ist Absicht: Beim ersten echten Login erkennt `auth_service` das alte
Format (kein "$"-Zeichen) und migriert es automatisch auf PBKDF2.

Anmeldung mit:
    Hermann Grieder: Vertragsnummer="BB-100001", Passwort="Dummy_hash_1"
    Felix Haerer:    Vertragsnummer="BB-100002", Passwort="Dummy_hash_2"

=== SEED-REIHENFOLGE (WARUM IN DIESER REIHENFOLGE?) ===
    1. Kategorien → werden von Transaktionen benoetigt (Foreign Key!)
    2. User       → werden von Konten benoetigt
    3. Konten     → werden von Karten und Transaktionen benoetigt
    4. Debitkarten → werden von Transaktionen benoetigt
    5. Kreditkarten → werden von Transaktionen benoetigt
    6. Gehaltsbuchungen → brauchen Kategorien + Konten

=== ARCHITEKTUR-KETTE ===
    src/__main__.py → seed_database()
    → seed_categories, seed_users, seed_accounts_for_users,
      seed_debit_cards_for_users, seed_credit_cards_for_users,
      seed_monthly_income_for_users, seed_felix_income
    → SQL: INSERT INTO ... (nur wenn Datensatz noch nicht existiert)
"""

from datetime import date

from sqlmodel import Session, select

from src.data_access.db import create_db_and_tables, engine
from src.domain.models import Account, Budget, Category, CreditCard, DebitCard, RecurringTransaction, Transaction, User
from src.utils.validators import generate_ch_iban


# Alle erlaubten Kategorien (Stammdaten, einmalig angelegt).
CATEGORY_NAMES = [
    "Transport",
    "Einkaeufe",
    "Versicherungen",
    "Miete",
    "Steuern",
    "Freizeit",
    "Sparen",
    "Well-being",
    "Kontouebertrag",
    "Sonstiges",
    "Gehalt",
]

# Startsaldo fuer Demo-Konten.
INITIAL_USER_BALANCE = 5000.0
INITIAL_SAVINGS_BALANCE = 10000.0

# Stichtag: Transaktionen bis einschliesslich diesem Datum gelten als gebucht (is_settled=True),
# danach als geplant (is_settled=False).
SEED_TODAY = date(2026, 5, 24)

# Zwei vordefinierte Test-User.
TEST_USERS = [
    {
        "first_name": "Hermann",
        "last_name": "Grieder",
        "contract_number": "BB-100001",
        "password_hash": "Dummy_hash_1",   # Demo: wird beim ersten Login auf PBKDF2 migriert.
        "phone": "+41 79 123 45 67",
        "address": "Bahnhofstrasse 12, 4001 Basel",
    },
    {
        "first_name": "Felix",
        "last_name": "Haerer",
        "contract_number": "BB-100002",
        "password_hash": "Dummy_hash_2",
        "phone": "+41 76 987 65 43",
        "address": "Rümelinsplatz 5, 4001 Basel",
    },
]


def seed_categories(session: Session) -> None:
    """Legt die vordefinierten Kategorien an, falls sie noch fehlen (idempotent).

    WARUM KATEGORIEN ZUERST?
        Transaktionen haben einen Foreign Key auf category_id.
        Wenn Kategorien fehlen, koennen keine Transaktionen angelegt werden.

    Args:
        session: Offene Datenbank-Session.
    """
    for category_name in CATEGORY_NAMES:
        # Pruefe, ob die Kategorie schon existiert.
        existing_category = session.exec(
            select(Category).where(Category.name == category_name)
        ).first()
        if existing_category is None:
            session.add(Category(name=category_name))
    session.commit()


def seed_users(session: Session) -> list[User]:
    """Legt genau die zwei vordefinierten Test-User an, falls sie fehlen (idempotent).

    WARUM NACH KATEGORIEN?
        User sind unabhaengig von Kategorien, aber Konten und Transaktionen
        brauchen sowohl User als auch Kategorien.

    VERTRAGSNUMMER ALS EINDEUTIGER SCHLUESSEL:
        Die Vertragsnummer (z.B. "BB-100001") ist der eindeutige Identifikator
        fuer den Existenz-Check. Wenn sie schon in der DB ist, wird kein
        neuer User angelegt.

    Args:
        session: Offene Datenbank-Session.

    Returns:
        Liste der (existierenden oder neu angelegten) User-Objekte.
    """
    users: list[User] = []

    for user_data in TEST_USERS:
        # Pruefe anhand der Vertragsnummer: Existiert der User schon?
        existing_user = session.exec(
            select(User).where(User.contract_number == user_data["contract_number"])
        ).first()

        if existing_user is None:
            # User noch nicht vorhanden → anlegen.
            # Nach `commit()` wird user_id von der DB vergeben.
            existing_user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                contract_number=user_data["contract_number"],
                password_hash=user_data["password_hash"],
                phone=user_data.get("phone"),
                address=user_data.get("address"),
            )
            session.add(existing_user)
            session.commit()
            session.refresh(existing_user)  # user_id aus DB laden.
        else:
            # Fehlende Kontaktdaten nachträglich ergänzen.
            updated = False
            if existing_user.phone is None and user_data.get("phone"):
                existing_user.phone = user_data["phone"]
                updated = True
            if existing_user.address is None and user_data.get("address"):
                existing_user.address = user_data["address"]
                updated = True
            if updated:
                session.add(existing_user)
                session.commit()
                session.refresh(existing_user)

        users.append(existing_user)

    return users


def seed_accounts_for_users(session: Session, users: list[User]) -> None:
    """Legt pro User ein Privat- und ein Sparkonto an, falls sie fehlen (idempotent).

    IBAN-GENERIERUNG:
        Die IBAN wird deterministisch aus user_id + Suffix generiert:
        user_id=1 → "0000000001" + "01" → Privatkonto-IBAN
        user_id=1 → "0000000001" + "02" → Sparkonto-IBAN
        Das ist reproduzierbar (gleiche user_id → gleiche IBAN).

    WARUM STARTSALDO?
        Demo-Konten starten mit CHF 5'000 (Privat) und CHF 10'000 (Spar),
        damit das Dashboard interessante Zahlen zeigt.

    Args:
        session: Offene Datenbank-Session.
        users: Liste der User (aus seed_users).
    """
    for user in users:
        # Privatkonto pruefen/anlegen.
        privat_account = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "privat",
            )
        ).first()
        if privat_account is None:
            privat_account = Account(
                account_type="privat",
                balance=0.0,
                status="aktiv",
                iban=generate_ch_iban("09000", f"{user.user_id:010d}01"),
                user_id=user.user_id,
            )
            session.add(privat_account)
            session.flush()

        # Sparkonto pruefen/anlegen.
        spar_account = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "spar",
            )
        ).first()
        if spar_account is None:
            spar_account = Account(
                account_type="spar",
                balance=0.0,
                status="aktiv",
                iban=generate_ch_iban("09000", f"{user.user_id:010d}02"),
                user_id=user.user_id,
            )
            session.add(spar_account)
            session.flush()

    session.commit()

    # Eröffnungsgutschrift für jedes neue Konto anlegen (idempotent).
    # Statt balance direkt zu setzen, wird eine echte Transaktion gebucht,
    # damit Kontoauszüge und Transaktionssummen immer übereinstimmen.
    categories = {c.name: c for c in session.exec(select(Category)).all()}
    sonstiges_id = categories["Sonstiges"].category_id if "Sonstiges" in categories else None
    for user in users:
        for account_type, initial in [("privat", INITIAL_USER_BALANCE), ("spar", INITIAL_SAVINGS_BALANCE)]:
            acc = session.exec(
                select(Account).where(
                    Account.user_id == user.user_id,
                    Account.account_type == account_type,
                )
            ).first()
            if acc is None or sonstiges_id is None:
                continue
            already = session.exec(
                select(Transaction).where(
                    Transaction.account_id == acc.account_id,
                    Transaction.note == "Eröffnungsgutschrift",
                )
            ).first()
            if already is None:
                session.add(Transaction(
                    amount=initial,
                    date=date(2025, 12, 31),
                    type="income",
                    note="Eröffnungsgutschrift",
                    category_id=sonstiges_id,
                    account_id=acc.account_id,
                    is_settled=True,
                ))
                acc.balance += initial
    session.commit()


def seed_debit_cards_for_users(session: Session, users: list[User]) -> None:
    """Stellt sicher, dass jeder Test-User eine aktive Debitkarte hat (idempotent).

    WARUM AN PRIVATKONTO?
        Debitkarten sind nur fuer Privatkonten erlaubt (Geschaeftsregel).
        Das Sparkonto bekommt keine Debitkarte.

    Args:
        session: Offene Datenbank-Session.
        users: Liste der User.
    """
    today = date.today()
    for user in users:
        # Pruefe: Hat der User schon eine aktive Debitkarte (via Konto)?
        has_active_debit = session.exec(
            select(DebitCard)
            .join(Account, Account.account_id == DebitCard.account_id)
            .where(
                Account.user_id == user.user_id,
                DebitCard.status == "aktiv",
            )
        ).first()

        if has_active_debit is not None:
            continue  # Schon vorhanden → ueberspringen.

        # Privatkonto des Users laden (Debitkarte gehoert ans Privatkonto).
        private_account = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "privat",
            )
        ).first()

        if private_account is None:
            continue  # Kein Privatkonto? (sollte nicht passieren)

        # Kartennummer deterministisch aus user_id generieren.
        session.add(
            DebitCard(
                card_number=f"420000{user.user_id:010d}",
                expire_date=date(today.year + 4, today.month, 1),
                status="aktiv",
                account_id=private_account.account_id,
            )
        )

    session.commit()


def seed_credit_cards_for_users(session: Session, users: list[User]) -> None:
    """Stellt sicher, dass jeder Test-User eine aktive Kreditkarte hat (idempotent).

    UNTERSCHIED ZU DEBITKARTE:
        Kreditkarten gehoeren direkt zum User (user_id), nicht zu einem Konto.
        Kreditrahmen: CHF 5'000, Startguthaben: 0.0 (kein genutzter Kredit).

    Args:
        session: Offene Datenbank-Session.
        users: Liste der User.
    """
    today = date.today()
    for user in users:
        # Pruefe: Hat der User schon eine aktive Kreditkarte?
        has_active_credit = session.exec(
            select(CreditCard).where(
                CreditCard.user_id == user.user_id,
                CreditCard.status == "aktiv",
            )
        ).first()

        if has_active_credit is not None:
            continue

        # Privatkonto als Standard-Abrechnungskonto ermitteln.
        privat = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "privat",
            )
        ).first()

        session.add(
            CreditCard(
                card_number=f"510000{user.user_id:010d}",
                expire_date=date(today.year + 4, today.month, 1),
                limit=5000.0,
                balance=0.0,
                status="aktiv",
                user_id=user.user_id,
                billing_account_id=privat.account_id if privat else None,
            )
        )

    session.commit()


def seed_monthly_income_for_users(session: Session, users: list[User]) -> None:
    """Legt pro User monatliche Gehaltsbuchungen von CHF 8'500 an (idempotent).

    WARUM GEHALTS-BUCHUNGEN?
        Damit das Dashboard und die Transaktionsliste interessante Daten zeigen
        (nicht komplett leer). Ohne Gehalt waere der Kontostand unrealistisch.

    ZEITRAUM:
        Januar bis heute (aktuelles Jahr). D.h. wenn die App im Mai gestartet
        wird, gibt es Gehaltsbuchungen fuer Januar, Februar, Maerz, April, Mai.

    IDEMPOTENZ:
        Pruefe pro User + Konto + Datum + Typ: "Gibt es schon eine Buchung?"
        Nur wenn keine existiert, wird eine neue angelegt.

    Args:
        session: Offene Datenbank-Session.
        users: Liste der User.
    """
    # Kategorie "Gehalt" muss vorher in seed_categories angelegt worden sein.
    gehalt_category = session.exec(
        select(Category).where(Category.name == "Gehalt")
    ).first()
    if gehalt_category is None:
        return  # Kategorie fehlt → Abbruch (sollte nach seed_categories nicht passieren).

    today = date.today()

    for user in users:
        # Felix hat eigene Einnahmen via seed_felix_income_and_expenses.
        if user.contract_number == "BB-100002":
            continue

        # Privatkonto des Users laden (Gehalt geht aufs Privatkonto).
        privat_account = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "privat",
            )
        ).first()
        if privat_account is None:
            continue

        # Monatliche Gehaltsbuchungen anlegen (Januar bis heute).
        for month in range(1, today.month + 1):
            salary_date = date(today.year, month, 1)

            # Idempotenz: Gibt es schon eine Buchung fuer dieses Datum + Konto?
            existing = session.exec(
                select(Transaction).where(
                    Transaction.account_id == privat_account.account_id,
                    Transaction.date == salary_date,
                    Transaction.type == "income",
                    Transaction.note == "Monatsgehalt",
                )
            ).first()
            if existing is not None:
                continue  # Schon vorhanden → ueberspringen.

            # Neue Gehaltsbuchung anlegen.
            session.add(Transaction(
                amount=8500.0,
                date=salary_date,
                type="income",
                note="Monatsgehalt",
                category_id=gehalt_category.category_id,
                account_id=privat_account.account_id,
            ))
            # Kontostand erhoehen (keine Session-Neuladen noetig, da gleiche Session).
            privat_account.balance += 8500.0

        # Monatliche Ausgaben fuer Hermann (Jan-Mai 2026, realistisch).
        categories = {c.name: c for c in session.exec(select(Category)).all()}
        hermann_expenses = [
            # --- Januar ---
            (date(2026, 1,  1), 2100.00, "Dauerauftrag Miete",        "Miete"),
            (date(2026, 1,  1),  450.00, "Krankenkasse",              "Versicherungen"),
            (date(2026, 1,  1),   95.00, "OeV Monatsabo",             "Transport"),
            (date(2026, 1,  5),  134.80, "Coop Wocheneinkauf",        "Einkaeufe"),
            (date(2026, 1, 12),   98.40, "Migros Einkauf",            "Einkaeufe"),
            (date(2026, 1, 15),   70.00, "Fitness Abo",               "Well-being"),
            (date(2026, 1, 18),  112.60, "Coop Einkauf 2",            "Einkaeufe"),
            (date(2026, 1, 22),   38.20, "Apotheke",                  "Well-being"),
            (date(2026, 1, 25),   55.00, "Spotify & Netflix",         "Freizeit"),
            (date(2026, 1, 28),   78.50, "Restaurant Abendessen",     "Freizeit"),
            (date(2026, 1, 29),   45.00, "Telefonrechnung",           "Sonstiges"),
            (date(2026, 1, 31),  180.00, "Strom & Nebenkosten",       "Sonstiges"),
            # --- Februar ---
            (date(2026, 2,  1), 2100.00, "Dauerauftrag Miete",        "Miete"),
            (date(2026, 2,  1),  450.00, "Krankenkasse",              "Versicherungen"),
            (date(2026, 2,  1),   95.00, "OeV Monatsabo",             "Transport"),
            (date(2026, 2,  6),  118.20, "Coop Einkauf",              "Einkaeufe"),
            (date(2026, 2, 13),   92.70, "Migros Einkauf",            "Einkaeufe"),
            (date(2026, 2, 18),  105.00, "Zahnarzt",                  "Well-being"),
            (date(2026, 2, 20),  107.40, "Coop Einkauf 2",            "Einkaeufe"),
            (date(2026, 2, 24),   45.80, "Kino & Ausgang",            "Freizeit"),
            (date(2026, 2, 25),   68.00, "Theaterticket",             "Freizeit"),
            (date(2026, 2, 26),   55.00, "Spotify & Netflix",         "Freizeit"),
            (date(2026, 2, 28),  180.00, "Strom & Nebenkosten",       "Sonstiges"),
            # --- Maerz ---
            (date(2026, 3,  1), 2100.00, "Dauerauftrag Miete",        "Miete"),
            (date(2026, 3,  1),  450.00, "Krankenkasse",              "Versicherungen"),
            (date(2026, 3,  1),   95.00, "OeV Monatsabo",             "Transport"),
            (date(2026, 3,  4),  125.30, "Coop Einkauf",              "Einkaeufe"),
            (date(2026, 3, 10),   87.60, "Migros Einkauf",            "Einkaeufe"),
            (date(2026, 3, 15),   70.00, "Fitness Abo",               "Well-being"),
            (date(2026, 3, 20),  115.90, "Coop Einkauf 2",            "Einkaeufe"),
            (date(2026, 3, 24),  280.00, "Steuervorauszahlung",       "Steuern"),
            (date(2026, 3, 27),   84.00, "Restaurant mit Familie",    "Freizeit"),
            (date(2026, 3, 29),   55.00, "Spotify & Netflix",         "Freizeit"),
            (date(2026, 3, 31),  185.00, "Strom & Nebenkosten",       "Sonstiges"),
            # --- April ---
            (date(2026, 4,  1), 2100.00, "Dauerauftrag Miete",        "Miete"),
            (date(2026, 4,  1),  450.00, "Krankenkasse",              "Versicherungen"),
            (date(2026, 4,  1),   95.00, "OeV Monatsabo",             "Transport"),
            (date(2026, 4,  7),  119.40, "Coop Einkauf",              "Einkaeufe"),
            (date(2026, 4, 12),   94.20, "Migros Einkauf",            "Einkaeufe"),
            (date(2026, 4, 17),   70.00, "Fitness Abo",               "Well-being"),
            (date(2026, 4, 21),  108.70, "Coop Einkauf 2",            "Einkaeufe"),
            (date(2026, 4, 23),   32.60, "Apotheke",                  "Well-being"),
            (date(2026, 4, 24),   62.50, "Ausflug Ostern",            "Freizeit"),
            (date(2026, 4, 26),  138.00, "Kleider Shopping",          "Sonstiges"),
            (date(2026, 4, 27),   55.00, "Spotify & Netflix",         "Freizeit"),
            (date(2026, 4, 30),  180.00, "Strom & Nebenkosten",       "Sonstiges"),
            # --- Mai (bis 28.05) ---
            (date(2026, 5,  1), 2100.00, "Dauerauftrag Miete",        "Miete"),
            (date(2026, 5,  1),  450.00, "Krankenkasse",              "Versicherungen"),
            (date(2026, 5,  1),   95.00, "OeV Monatsabo",             "Transport"),
            (date(2026, 5,  8),  122.80, "Coop Einkauf",              "Einkaeufe"),
            (date(2026, 5, 12),   91.30, "Migros Einkauf",            "Einkaeufe"),
            (date(2026, 5, 13),   55.00, "Spotify & Netflix",         "Freizeit"),
            (date(2026, 5, 15),   70.00, "Fitness Abo",               "Well-being"),
            (date(2026, 5, 20),  118.50, "Coop Einkauf 2",            "Einkaeufe"),
            (date(2026, 5, 22),   34.60, "Apotheke",                  "Well-being"),
            (date(2026, 5, 24),   45.00, "Telefonrechnung",           "Sonstiges"),
            (date(2026, 5, 27),   76.50, "Restaurant Abendessen",     "Freizeit"),
            (date(2026, 5, 28),  180.00, "Strom & Nebenkosten",       "Sonstiges"),
        ]
        for exp_date, amount, note, cat_name in hermann_expenses:
            if cat_name not in categories:
                continue
            if session.exec(
                select(Transaction).where(
                    Transaction.account_id == privat_account.account_id,
                    Transaction.date == exp_date,
                    Transaction.amount == amount,
                    Transaction.note == note,
                )
            ).first() is None:
                settled = exp_date <= SEED_TODAY
                session.add(
                    Transaction(
                        amount=amount,
                        date=exp_date,
                        type="expense",
                        note=note,
                        category_id=categories[cat_name].category_id,
                        account_id=privat_account.account_id,
                        is_settled=settled,
                    )
                )
                if settled:
                    privat_account.balance -= amount

    session.commit()


def seed_felix_income(session: Session, felix: User) -> None:
    """Legt Felix's Einnahmen und Lastschriften (Jan-Apr 2026) an (idempotent).

    ABLAUF:
        1. Alte 8'500-Buchungen loeschen, falls noch vorhanden (einmalige Bereinigung).
        2. Neue Gehaltsbuchungen CHF 7'860 fuer Jan-Apr 2026 anlegen.
        3. Monatliche Lastschriften anlegen (Miete, Krankenkasse, Einkauf, ...).

    Args:
        session: Offene Datenbank-Session.
        felix: Felix-User-Objekt.
    """
    categories = {c.name: c for c in session.exec(select(Category)).all()}

    privat1_iban = generate_ch_iban("09000", f"{felix.user_id:010d}01")
    privat1 = session.exec(select(Account).where(Account.iban == privat1_iban)).first()
    if privat1 is None or "Gehalt" not in categories:
        return

    # Gehalt Jan-Mai 2026 anlegen.
    for month in range(1, 6):
        salary_date = date(2026, month, 1)
        if session.exec(
            select(Transaction).where(
                Transaction.account_id == privat1.account_id,
                Transaction.date == salary_date,
                Transaction.type == "income",
                Transaction.note == "Monatsgehalt",
            )
        ).first() is None:
            session.add(
                Transaction(
                    amount=7860.0,
                    date=salary_date,
                    type="income",
                    note="Monatsgehalt",
                    category_id=categories["Gehalt"].category_id,
                    account_id=privat1.account_id,
                )
            )
            privat1.balance += 7860.0
    session.commit()

    # Monatliche Lastschriften (Miete, Krankenkasse, Einkauf, Freizeit, ...).
    expense_data = [
        # --- Januar ---
        (date(2026, 1,  1), 1650.00, "Dauerauftrag Miete",      "Miete"),
        (date(2026, 1,  1),  290.00, "Krankenkasse",            "Versicherungen"),
        (date(2026, 1,  1),   95.00, "OeV Monatsabo",           "Transport"),
        (date(2026, 1,  9),  113.40, "Coop Wocheneinkauf",      "Einkaeufe"),
        (date(2026, 1, 14),   87.20, "Migros Einkauf",          "Einkaeufe"),
        (date(2026, 1, 16),   70.00, "Fitness Abo",             "Well-being"),
        (date(2026, 1, 20),   34.90, "Spotify & Netflix",       "Freizeit"),
        (date(2026, 1, 23),   92.60, "Migros Einkauf 2",        "Einkaeufe"),
        (date(2026, 1, 27),   65.00, "Restaurant Feierabend",   "Freizeit"),
        (date(2026, 1, 31),  155.00, "Strom & Nebenkosten",     "Sonstiges"),
        # --- Februar ---
        (date(2026, 2,  1), 1650.00, "Dauerauftrag Miete",      "Miete"),
        (date(2026, 2,  1),  290.00, "Krankenkasse",            "Versicherungen"),
        (date(2026, 2,  1),   95.00, "OeV Monatsabo",           "Transport"),
        (date(2026, 2,  7),  108.50, "Coop Einkauf",            "Einkaeufe"),
        (date(2026, 2, 12),   79.80, "Migros Einkauf",          "Einkaeufe"),
        (date(2026, 2, 16),   89.00, "Valentinstag Dinner",     "Freizeit"),
        (date(2026, 2, 19),   96.30, "Migros Einkauf 2",        "Einkaeufe"),
        (date(2026, 2, 25),   55.00, "Kino & Bar",              "Freizeit"),
        (date(2026, 2, 27),   34.90, "Spotify & Netflix",       "Freizeit"),
        (date(2026, 2, 28),  155.00, "Strom & Nebenkosten",     "Sonstiges"),
        # --- Maerz ---
        (date(2026, 3,  1), 1650.00, "Dauerauftrag Miete",      "Miete"),
        (date(2026, 3,  1),  290.00, "Krankenkasse",            "Versicherungen"),
        (date(2026, 3,  1),   95.00, "OeV Monatsabo",           "Transport"),
        (date(2026, 3,  6),  121.70, "Coop Einkauf",            "Einkaeufe"),
        (date(2026, 3, 13),   83.40, "Migros Einkauf",          "Einkaeufe"),
        (date(2026, 3, 15),   70.00, "Fitness Abo",             "Well-being"),
        (date(2026, 3, 19),   98.20, "Migros Einkauf 2",        "Einkaeufe"),
        (date(2026, 3, 22),  145.00, "Kleider Shopping H&M",    "Sonstiges"),
        (date(2026, 3, 27),   72.50, "Restaurant mit Kollegen", "Freizeit"),
        (date(2026, 3, 29),   34.90, "Spotify & Netflix",       "Freizeit"),
        (date(2026, 3, 31),  160.00, "Strom & Nebenkosten",     "Sonstiges"),
        # --- April ---
        (date(2026, 4,  1), 1650.00, "Dauerauftrag Miete",      "Miete"),
        (date(2026, 4,  1),  290.00, "Krankenkasse",            "Versicherungen"),
        (date(2026, 4,  1),   95.00, "OeV Monatsabo",           "Transport"),
        (date(2026, 4,  4),  103.60, "Coop Einkauf",            "Einkaeufe"),
        (date(2026, 4,  9),   88.90, "Migros Einkauf",          "Einkaeufe"),
        (date(2026, 4, 13),   48.50, "Ostern Feier",            "Freizeit"),
        (date(2026, 4, 17),   70.00, "Fitness Abo",             "Well-being"),
        (date(2026, 4, 21),   99.70, "Migros Einkauf 2",        "Einkaeufe"),
        (date(2026, 4, 24),   42.80, "Apotheke",                "Well-being"),
        (date(2026, 4, 27),   34.90, "Spotify & Netflix",       "Freizeit"),
        (date(2026, 4, 30),  155.00, "Strom & Nebenkosten",     "Sonstiges"),
        # --- Mai (bis 28.05) ---
        (date(2026, 5,  1), 1650.00, "Dauerauftrag Miete",      "Miete"),
        (date(2026, 5,  1),  290.00, "Krankenkasse",            "Versicherungen"),
        (date(2026, 5,  1),   95.00, "OeV Monatsabo",           "Transport"),
        (date(2026, 5,  7),  109.20, "Coop Einkauf",            "Einkaeufe"),
        (date(2026, 5, 10),   81.50, "Migros Einkauf",          "Einkaeufe"),
        (date(2026, 5, 11),   34.90, "Spotify & Netflix",       "Freizeit"),
        (date(2026, 5, 13),   52.40, "Restaurant Mittagessen",  "Freizeit"),
        (date(2026, 5, 15),   70.00, "Fitness Abo",             "Well-being"),
        (date(2026, 5, 20),   97.40, "Migros Einkauf 2",        "Einkaeufe"),
        (date(2026, 5, 24),   41.20, "Apotheke",                "Well-being"),
        (date(2026, 5, 26),   62.00, "Kino & Bar",              "Freizeit"),
        (date(2026, 5, 28),  155.00, "Strom & Nebenkosten",     "Sonstiges"),
    ]
    for exp_date, amount, note, cat_name in expense_data:
        if session.exec(
            select(Transaction).where(
                Transaction.account_id == privat1.account_id,
                Transaction.date == exp_date,
                Transaction.amount == amount,
                Transaction.note == note,
            )
        ).first() is None:
            settled = exp_date <= SEED_TODAY
            session.add(
                Transaction(
                    amount=amount,
                    date=exp_date,
                    type="expense",
                    note=note,
                    category_id=categories[cat_name].category_id,
                    account_id=privat1.account_id,
                    is_settled=settled,
                )
            )
            if settled:
                privat1.balance -= amount
    session.commit()


def seed_recurring_rent(session: Session, users: list[User]) -> None:
    """Legt Miete-Dauerauftraege fuer Hermann und Felix an (idempotent).

    Fuer jeden User wird:
        1. Alle bestehenden Miete-Transaktionen auf "Dauerauftrag Miete" umbenannt,
           damit sie konsistent mit automatisch gebuchten Dauerauftraegen aussehen.
        2. Eine Template-Transaktion angelegt (is_settled=False, naechste Faelligkeit
           01.06.2026), die in den geplanten Zahlungen erscheint.
        3. Ein RecurringTransaction-Eintrag angelegt, der auf die Template-Transaktion
           zeigt und last_executed=01.05.2026 traegt (letzter Monat war Mai).

    Vermieter-IBANs (gueltige CH-IBANs, Modulo-97-geprueft):
        Hermann → CH7200762011200000001  (UBS, Musterstrasse Immobilien AG)
        Felix   → CH8708390016500000001  (Raiffeisen, Basler Wohnungen GmbH)
    """
    miete_cat = session.exec(select(Category).where(Category.name == "Miete")).first()
    if miete_cat is None:
        return

    # Vermieter-IBANs deterministisch generiert (Modulo-97, gueltig).
    landlord_ibans = {
        "BB-100001": generate_ch_iban("00762", "011200000001"),  # Hermann
        "BB-100002": generate_ch_iban("08390", "016500000001"),  # Felix
    }
    rent_amounts = {
        "BB-100001": 2100.0,
        "BB-100002": 1650.0,
    }

    for user in users:
        iban = landlord_ibans.get(user.contract_number)
        amount = rent_amounts.get(user.contract_number)
        if iban is None or amount is None:
            continue

        privat = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "privat",
            )
        ).first()
        if privat is None:
            continue

        # Idempotenz: Dauerauftrag schon vorhanden?
        existing = session.exec(
            select(RecurringTransaction).where(
                RecurringTransaction.account_id == privat.account_id,
                RecurringTransaction.target_iban == iban,
            )
        ).first()
        if existing is not None:
            continue

        # Schritt 2: Template-Transaktion (naechste geplante Ausfuehrung: 01.06.2026).
        template = Transaction(
            amount=amount,
            date=date(2026, 6, 1),
            type="expense",
            note="Dauerauftrag Miete",
            category_id=miete_cat.category_id,
            account_id=privat.account_id,
            is_settled=False,
        )
        session.add(template)
        session.flush()  # transaction_id aus DB holen.

        # Schritt 3: Dauerauftrag anlegen.
        # last_executed = 2026-05-01 → _next_due_date = 2026-06-01 (faellig im Juni).
        recurring = RecurringTransaction(
            amount=amount,
            target_iban=iban,
            interval="monthly",
            start_date=date(2026, 1, 1),
            end_date=None,
            last_executed=date(2026, 5, 1),
            account_id=privat.account_id,
            category_id=miete_cat.category_id,
            transaction_id=template.transaction_id,
        )
        session.add(recurring)
    session.commit()


def seed_budgets(session: Session, users: list[User]) -> None:
    """Legt monatliche Budgets fuer Hermann und Felix an (idempotent).

    Erstellt Budgets fuer Januar bis zum aktuellen Monat des laufenden Jahres.
    Idempotenz: UniqueConstraint (user_id, month, year, category_id) verhindert Duplikate.

    Args:
        session: Offene Datenbank-Session.
        users: Liste der User (aus seed_users).
    """
    today = date.today()
    categories = {c.name: c.category_id for c in session.exec(select(Category)).all()}

    # Budgets pro User: Kategorie → monatliches Limit in CHF
    budgets_per_user = {
        "BB-100001": {   # Hermann
            "Miete":          2200.0,
            "Versicherungen":  500.0,
            "Transport":       130.0,
            "Einkaeufe":       420.0,
            "Well-being":      160.0,
            "Freizeit":        220.0,
            "Steuern":         300.0,
            "Sonstiges":       320.0,
        },
        "BB-100002": {   # Felix
            "Miete":          1700.0,
            "Versicherungen":  320.0,
            "Transport":       130.0,
            "Einkaeufe":       350.0,
            "Well-being":      120.0,
            "Freizeit":        200.0,
            "Sonstiges":       200.0,
        },
    }

    for user in users:
        limits = budgets_per_user.get(user.contract_number, {})
        for month in range(1, today.month + 1):
            for cat_name, limit in limits.items():
                cat_id = categories.get(cat_name)
                if cat_id is None:
                    continue
                exists = session.exec(
                    select(Budget).where(
                        Budget.user_id == user.user_id,
                        Budget.month == month,
                        Budget.year == today.year,
                        Budget.category_id == cat_id,
                    )
                ).first()
                if exists is None:
                    session.add(Budget(
                        user_id=user.user_id,
                        limit_amount=limit,
                        month=month,
                        year=today.year,
                        category_id=cat_id,
                    ))
    session.commit()


def seed_database() -> None:
    """Fuehrt den kompletten Seeding-Prozess aus.

    AUFRUF-KETTE:
        src/__main__.py → seed_database()
        → create_db_and_tables() [Tabellen sicherstellen]
        → seed_categories(session)
        → seed_users(session)
        → seed_accounts_for_users(session, users)
        → seed_debit_cards_for_users(session, users)
        → seed_credit_cards_for_users(session, users)
        → seed_monthly_income_for_users(session, users)  [nur Hermann]
        → seed_felix_income(session, felix)
        → seed_recurring_rent(session, users)
        → seed_budgets(session, users)

    ALLE SCHRITTE SIND IDEMPOTENT: mehrfaches Ausfuehren erzeugt keine Duplikate.
    """
    # Tabellen sicherstellen (falls noch nicht vorhanden).
    create_db_and_tables()

    with Session(engine) as session:
        seed_categories(session)
        users = seed_users(session)
        seed_accounts_for_users(session, users)
        seed_debit_cards_for_users(session, users)
        seed_credit_cards_for_users(session, users)
        seed_monthly_income_for_users(session, users)
        felix = next(u for u in users if u.contract_number == "BB-100002")
        seed_felix_income(session, felix)
        seed_recurring_rent(session, users)
        seed_budgets(session, users)
        _recalculate_balances(session)


def _recalculate_balances(session: Session) -> None:
    """Korrigiert alle Kontosalden anhand der tatsaechlich gebuchten Transaktionen.

    Verhindert, dass Saldo und Transaktionshistorie auseinanderlaufen,
    wenn Seed-Funktionen mehrfach ausgefuehrt werden oder Duplikate geloescht werden.
    """
    accounts = session.exec(select(Account)).all()
    for account in accounts:
        settled = session.exec(
            select(Transaction).where(
                Transaction.account_id == account.account_id,
                Transaction.is_settled == True,  # noqa: E712
            )
        ).all()
        balance = sum(
            t.amount if t.type == "income" else -t.amount
            for t in settled
        )
        account.balance = round(balance, 2)
        session.add(account)
    session.commit()


# Wird ausgefuehrt wenn `python -m src.data_access.seed` aufgerufen wird.
if __name__ == "__main__":
    seed_database()
