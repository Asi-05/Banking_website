"""src.data_access.repositories.account_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS IST EIN REPOSITORY? ===
Ein Repository ist der "Datenbankzugriffs-Helfer". Es stellt einfache Methoden
bereit, um Daten aus der Datenbank zu lesen oder darin zu speichern - ohne dass
der Service direkt mit SQL arbeiten muss.

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank (SQLite)

    Repositories enthalten KEINE Geschaeftsregeln (z.B. "Konto darf nur geschlossen
    werden wenn Saldo 0 ist"). Das ist die Aufgabe des Service.
    Repositories machen nur: Laden, Speichern, Loeschen von Daten.

=== WAS IST EINE SESSION? ===
Eine Session ist wie eine "offene Datenbankverbindung mit Gedaechtnis".
Sie funktioniert so:
    1. session.add(objekt)    → "Merke dir, dass dieses Objekt gespeichert werden soll"
    2. session.commit()       → "Schreibe jetzt wirklich in die Datenbank"
    3. session.refresh(objekt)→ "Lese die aktuellen Werte aus der DB (z.B. neue ID)"

    Sessions werden immer mit `with Session(engine) as session:` geoeffnet.
    Beim Verlassen des `with`-Blocks wird die Session automatisch geschlossen.

=== VERWENDUNG ===
Wird ausschliesslich vom AccountService verwendet:
    account_service.py → AccountRepository → SQLite-Datenbank (banking.db)
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Account


# Kapselt reine Datenbankzugriffe fuer Konten.
class AccountRepository:
    """Datenbankzugriffe fuer `Account`-Objekte.

    Jede Methode bekommt eine Session (offene DB-Verbindung) im Konstruktor
    und nutzt diese fuer alle Queries. Die Session wird vom aufrufenden Service
    verwaltet (geoeffnet und geschlossen).

    Hinweis:
        Die Methoden committen die Session selbst (create/save). Dadurch kann
        jede Methode als eigenstaendige Einheit verwendet werden.
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        WOHER KOMMT DIE SESSION?
            Der Service erstellt die Session mit `with Session(engine) as session:`
            und uebergibt sie dem Repository-Konstruktor:
            `account_repository = AccountRepository(session)`

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        # Die Session wird als Instanz-Variable gespeichert, damit alle Methoden sie nutzen koennen
        self.session = session

    def create(self, account: Account) -> Account:
        """Legt ein neues Konto in der Datenbank an.

        AUFRUF-KETTE:
            account_service.open_account(payload)
            → AccountRepository.create(account) → Datenbank (INSERT INTO accounts ...)

        WAS PASSIERT SCHRITT FUER SCHRITT:
            1. session.add(account):    SQLModel merkt sich das Objekt (noch NICHT in DB)
            2. session.commit():        Jetzt wird der INSERT in die SQLite-Datei geschrieben
            3. session.refresh(account): Laedt die neu generierte account_id aus der DB zurueck

        Args:
            account: Ein neues Account-Objekt mit gesetzten Feldern (ausser account_id).
                     account_id wird von der Datenbank automatisch vergeben.

        Returns:
            Das gespeicherte Account-Objekt, jetzt mit befuellter account_id.
        """
        self.session.add(account)      # In Session-Puffer aufnehmen
        self.session.commit()          # Wirklich in die Datenbank schreiben
        self.session.refresh(account)  # Generierte account_id zurueckladen
        return account

    def get_by_id(self, account_id: int) -> Account | None:
        """Laedt ein Konto anhand seiner ID (Primaerschluessel).

        AUFRUF-KETTE:
            Verschiedene Services → AccountRepository.get_by_id(account_id)
            → SQL: SELECT * FROM accounts WHERE account_id = :account_id

        session.get() ist die schnellste Art, nach Primaerschluessel zu suchen.
        SQLModel/SQLAlchemy kann dabei sogar den internen Cache nutzen.

        Args:
            account_id: Die eindeutige ID des Kontos (Ganzzahl).

        Returns:
            Account-Objekt wenn gefunden, None wenn kein Konto mit dieser ID existiert.
        """
        return self.session.get(Account, account_id)

    def get_by_iban(self, iban: str) -> Account | None:
        """Laedt ein Konto anhand seiner IBAN.

        AUFRUF-KETTE:
            account_service.open_account() (IBAN-Eindeutigkeitspruefung)
            → AccountRepository.get_by_iban(iban)
            → SQL: SELECT * FROM accounts WHERE iban = :iban

        WOZU DIESE METHODE?
            Beim Eroeffnen eines Kontos wird geprueft, ob die generierte IBAN
            schon vergeben ist. Falls ja, wird eine andere generiert.

        Args:
            iban: IBAN-String (z.B. "CH1200700110003461890").

        Returns:
            Account-Objekt wenn IBAN gefunden, None wenn IBAN noch nicht vergeben.
        """
        # select(Account) = "Suche in der accounts-Tabelle"
        # .where(...) = "Filtere: nur wo iban = der gesuchte Wert"
        statement = select(Account).where(Account.iban == iban)
        # .first() = "Nimm das erste (und einzige) Ergebnis, oder None wenn keins gefunden"
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: int) -> list[Account]:
        """Gibt alle Konten eines Users als Liste zurueck.

        AUFRUF-KETTE:
            account_service.list_accounts(user_id)
            → AccountRepository.list_by_user(user_id)
            → SQL: SELECT * FROM accounts WHERE user_id = :user_id

        RUECKGABE:
            Alle Konten des Users, egal welchen Status sie haben (aktiv, geschlossen).
            Die View kann dann selbst filtern, wenn sie z.B. nur aktive anzeigen moechte.

        Args:
            user_id: ID des Users, dessen Konten geladen werden sollen.

        Returns:
            Liste von Account-Objekten (kann leer sein, wenn User keine Konten hat).
        """
        statement = select(Account).where(Account.user_id == user_id)
        # .all() gibt alle passenden Zeilen zurueck (list() wandelt in normale Python-Liste um)
        return list(self.session.exec(statement).all())

    def save(self, account: Account) -> Account:
        """Speichert Aenderungen an einem bestehenden Konto.

        AUFRUF-KETTE:
            account_service (Saldo-Update, Status-Aenderung)
            → AccountRepository.save(account)
            → SQL: UPDATE accounts SET balance=..., status=... WHERE account_id=...

        WANN WIRD DIESE METHODE GENUTZT?
            - Nach einer Transaktion (Saldo aendern)
            - Beim Schliessen eines Kontos (Status auf "geschlossen" setzen)
            - Beim Eroeffnen eines Kontos (Status auf "aktiv" setzen)

        WAS PASSIERT SCHRITT FUER SCHRITT:
            1. session.add(account):    SQLModel sieht, dass dieses Objekt schon existiert
                                        (hat eine account_id) → wird als UPDATE behandelt
            2. session.commit():        UPDATE wird in die Datenbank geschrieben
            3. session.refresh(account): Aktuelle Werte aus DB zurueckladen

        Args:
            account: Das Account-Objekt mit den geaenderten Feldern.

        Returns:
            Das gespeicherte Account-Objekt nach dem Update.
        """
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account
