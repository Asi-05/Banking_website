"""src.data_access.seed

Diese Datei gehoert zur **Data-Access-Schicht**.

=== WAS MACHT DIESE DATEI? ===
`seed_database()` legt beim ersten App-Start Demo-Daten an:
    - 11 Kategorien (Lebensmittel, Transport, Freizeit, ...)
    - 2 Test-User (Hermann Grieder, Felix Haerer)
    - Pro User: 1 Privatkonto + 1 Sparkonto
    - Pro User: 1 Debitkarte (ans Privatkonto gebunden)
    - Pro User: 1 Kreditkarte
    - Pro User: Monatliche Gehaltsbuchungen (CHF 8'500 ab Januar des aktuellen Jahres)

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
      seed_monthly_income_for_users
    → SQL: INSERT INTO ... (nur wenn Datensatz noch nicht existiert)
"""

from datetime import date

from sqlmodel import Session, select

from src.data_access.db import create_db_and_tables, engine
from src.domain.models import Account, Category, CreditCard, DebitCard, Transaction, User
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

# Zwei vordefinierte Test-User.
TEST_USERS = [
    {
        "first_name": "Hermann",
        "last_name": "Grieder",
        "contract_number": "BB-100001",
        "password_hash": "Dummy_hash_1",   # Demo: wird beim ersten Login auf PBKDF2 migriert.
    },
    {
        "first_name": "Felix",
        "last_name": "Haerer",
        "contract_number": "BB-100002",
        "password_hash": "Dummy_hash_2",
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
            )
            session.add(existing_user)
            session.commit()
            session.refresh(existing_user)  # user_id aus DB laden.

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
            session.add(
                Account(
                    account_type="privat",
                    balance=INITIAL_USER_BALANCE,
                    status="aktiv",
                    iban=generate_ch_iban("09000", f"{user.user_id:010d}01"),
                    user_id=user.user_id,
                )
            )

        # Sparkonto pruefen/anlegen.
        spar_account = session.exec(
            select(Account).where(
                Account.user_id == user.user_id,
                Account.account_type == "spar",
            )
        ).first()
        if spar_account is None:
            session.add(
                Account(
                    account_type="spar",
                    balance=INITIAL_SAVINGS_BALANCE,
                    status="aktiv",
                    iban=generate_ch_iban("09000", f"{user.user_id:010d}02"),
                    user_id=user.user_id,
                )
            )

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
            continue  # Schon vorhanden → ueberspringen.

        # Kreditkarte direkt am User (keine Konto-Bindung).
        session.add(
            CreditCard(
                card_number=f"510000{user.user_id:010d}",
                expire_date=date(today.year + 4, today.month, 1),
                limit=5000.0,    # Kreditrahmen.
                balance=0.0,     # Genutzter Kredit am Anfang: 0.
                status="aktiv",
                user_id=user.user_id,
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
        → seed_monthly_income_for_users(session, users)

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


# Wird ausgefuehrt wenn `python -m src.data_access.seed` aufgerufen wird.
if __name__ == "__main__":
    seed_database()
