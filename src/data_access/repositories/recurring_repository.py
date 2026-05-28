"""src.data_access.repositories.recurring_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS IST EIN DAUERAUFTRAG (RecurringTransaction)? ===
Ein Dauerauftrag ist eine konfigurierte, wiederkehrende Ausgabe:
    - Betrag (amount): z.B. CHF 1'200 fuer Miete
    - Intervall (interval): "monthly" oder "yearly"
    - Startdatum (start_date): Ab wann wird der Auftrag ausgefuehrt?
    - Enddatum (end_date, optional): Ab wann wird er NICHT mehr ausgefuehrt?
    - last_executed: Wann wurde er zuletzt ausgefuehrt? (Zustandsspeicherung)
    - account_id: Von welchem Konto wird abgebucht?

=== WICHTIG: TRENNUNG ZWISCHEN REPOSITORY UND SERVICE ===
Das Repository fragt die Datenbank: "Welche Dauerauftraege existieren und
haben ein Startdatum <= heute?" (list_due_by_user)

Ob ein Dauerauftrag WIRKLICH faellig ist (Intervall + last_executed + Enddatum),
entscheidet der recurring_service.py - das ist Geschaeftslogik, die NICHT hier
ins Repository gehoert.

=== WARUM JOIN MIT ACCOUNT? ===
RecurringTransaction hat account_id, aber KEINE user_id.
Um alle Dauerauftraege EINES Users zu finden:
    User → Accounts (via Account.user_id)
    Account → RecurringTransactions (via RecurringTransaction.account_id)
    SQL: JOIN accounts ON accounts.account_id = recurring_transactions.account_id
         WHERE accounts.user_id = :user_id

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank

    Aufgerufen von: recurring_service.py
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from src.domain.models import Account, RecurringTransaction


# Kapselt reine Datenbankzugriffe fuer Dauerauftraege.
class RecurringRepository:
    """Datenbankzugriffe fuer RecurringTransaction-Objekte.

    Alle "Faelligkeits-Logik" (Intervall, letztes Ausfuehrungsdatum) ist bewusst
    im recurring_service.py, nicht hier. Das Repository liefert nur DB-Daten.
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        self.session = session

    def create(self, recurring: RecurringTransaction) -> RecurringTransaction:
        """Legt einen neuen Dauerauftrag in der Datenbank an.

        AUFRUF-KETTE:
            recurring_service.create_recurring(payload)
            → RecurringRepository.create(recurring)
            → SQL: INSERT INTO recurring_transactions (...) VALUES (...)

        WAS PASSIERT INTERN:
            1. session.add(recurring):    Objekt zur Session hinzufuegen
            2. session.commit():          INSERT ausfuehren
            3. session.refresh(recurring): recurring_id aus DB laden

        Args:
            recurring: Neues RecurringTransaction-Objekt (recurring_id noch nicht gesetzt).

        Returns:
            Gespeicherter Dauerauftrag mit recurring_id aus der Datenbank.
        """
        self.session.add(recurring)
        self.session.commit()
        self.session.refresh(recurring)
        return recurring

    def get_by_id(self, recurring_id: int) -> RecurringTransaction | None:
        """Laedt einen einzelnen Dauerauftrag anhand seiner ID.

        AUFRUF-KETTE:
            recurring_service.process_due_recurring_on_login()
            → RecurringRepository.get_by_id(recurring_id)
            → SQL: SELECT * FROM recurring_transactions WHERE recurring_id = :recurring_id

        WARUM WIRD DIESE METHODE AUCH BEIM LOGIN AUFGERUFEN?
            Beim Ausfuehren eines Dauerauftrags (process_due_recurring_on_login)
            wird der Dauerauftrag in einer neuen Session frisch geladen, damit
            `last_executed` korrekt gespeichert werden kann.

        Args:
            recurring_id: Primaerschluessel des Dauerauftrags.

        Returns:
            RecurringTransaction-Objekt wenn gefunden, None wenn nicht existent.
        """
        return self.session.get(RecurringTransaction, recurring_id)

    def list_by_user(self, user_id: int) -> list[RecurringTransaction]:
        """Laedt alle Dauerauftraege eines Users.

        AUFRUF-KETTE:
            recurring_service.list_recurring(user_id)
            → RecurringRepository.list_by_user(user_id)
            → SQL: SELECT rt.* FROM recurring_transactions rt
                   JOIN accounts a ON a.account_id = rt.account_id
                   WHERE a.user_id = :user_id

        WARUM JOIN UEBER accounts?
            RecurringTransaction hat keine direkte user_id. Sie haengt am Konto
            (account_id), und das Konto haengt am User (user_id). Deshalb muss
            die accounts-Tabelle dazwischengeschaltet werden.

        Args:
            user_id: ID des Users, dessen Dauerauftraege geladen werden sollen.

        Returns:
            Alle Dauerauftraege des Users.
        """
        # JOIN: recurring_transactions → accounts → User
        statement = (
            select(RecurringTransaction)
            .join(Account, Account.account_id == RecurringTransaction.account_id)
            .where(Account.user_id == user_id)
        )
        return list(self.session.exec(statement).all())

    def list_due_by_user(
        self,
        user_id: int,
        reference_date: date,
    ) -> list[RecurringTransaction]:
        """Laedt Dauerauftraege, die POTENZIELL faellig sind (Startdatum erreicht).

        AUFRUF-KETTE:
            recurring_service.process_due_recurring_on_login(user_id, login_date)
            → RecurringRepository.list_due_by_user(user_id, login_date)
            → SQL: SELECT rt.* FROM recurring_transactions rt
                   JOIN accounts a ON a.account_id = rt.account_id
                   WHERE a.user_id = :user_id
                   AND rt.start_date <= :reference_date

        WAS BEDEUTET "POTENZIELL FAELLIG"?
            Diese Methode prueft NUR: "Hat der Dauerauftrag schon begonnen?"
            (start_date <= reference_date)

            Der Service prueft danach noch:
            - Ist er wirklich faellig? (Intervall + last_executed berechnen)
            - Ist das Enddatum noch nicht ueberschritten?
            - Reicht der Kontostand fuer die Buchung?

        BEISPIEL:
            reference_date = date(2026, 5, 3)
            → Gibt alle Dauerauftraege zurueck, die am 3. Mai oder frueher begonnen haben.
            Der Service entscheidet dann, welche davon wirklich ausgefuehrt werden.

        Args:
            user_id: ID des eingeloggten Users.
            reference_date: Das Datum, gegen das geprueft wird (meist date.today()).

        Returns:
            Liste der Dauerauftraege, die theoretisch faellig sein koennten.
        """
        statement = (
            select(RecurringTransaction)
            .join(Account, Account.account_id == RecurringTransaction.account_id)
            .where(Account.user_id == user_id)
            # Nur Dauerauftraege, deren Startdatum bereits erreicht ist
            .where(RecurringTransaction.start_date <= reference_date)
        )
        return list(self.session.exec(statement).all())

    def save(self, recurring: RecurringTransaction) -> RecurringTransaction:
        """Speichert Aenderungen an einem Dauerauftrag.

        AUFRUF-KETTE:
            recurring_service.process_due_recurring_on_login() → last_executed aktualisieren
            recurring_service.update_recurring() → andere Felder aendern
            → RecurringRepository.save(recurring)
            → SQL: UPDATE recurring_transactions SET last_executed=... WHERE recurring_id=...

        WICHTIGER ANWENDUNGSFALL:
            Nach der Ausfuehrung eines Dauerauftrags wird last_executed auf das heutige
            Datum gesetzt, damit er nicht nochmal ausgefuehrt wird:
            recurring.last_executed = date.today()
            recurring_repository.save(recurring)

        Args:
            recurring: RecurringTransaction-Objekt mit geaenderten Feldern.

        Returns:
            Aktualisiertes RecurringTransaction-Objekt nach dem Speichern.
        """
        self.session.add(recurring)
        self.session.commit()
        self.session.refresh(recurring)
        return recurring

    def delete(self, recurring_id: int) -> None:
        """Loescht einen Dauerauftrag dauerhaft aus der Datenbank.

        AUFRUF-KETTE:
            recurring_service.delete_recurring(recurring_id)
            → RecurringRepository.delete(recurring_id)
            → SQL: DELETE FROM recurring_transactions WHERE recurring_id = :recurring_id

        SICHERHEIT:
            Wenn kein Dauerauftrag mit dieser ID existiert, passiert nichts.

        Args:
            recurring_id: ID des zu loeschenden Dauerauftrags.
        """
        recurring = self.session.get(RecurringTransaction, recurring_id)
        if recurring is not None:
            self.session.delete(recurring)  # Fuer Loeschung markieren
            self.session.commit()           # DELETE ausfuehren
