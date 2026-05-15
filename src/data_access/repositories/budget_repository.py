"""src.data_access.repositories.budget_repository

Diese Datei gehoert zur **Data-Access-Schicht** (Datenbankzugriff).

=== WAS SPEICHERT DIESES REPOSITORY? ===
Budget-Objekte aus der `budgets`-Tabelle in der SQLite-Datenbank.

Ein Budget hat:
    - user_id:      Wer hat dieses Budget gesetzt?
    - month/year:   Fuer welchen Monat gilt es?
    - limit_amount: Wie viel CHF darf maximal ausgegeben werden?
    - category_id:  Nur fuer diese Kategorie (None = gilt fuer alle Ausgaben)

=== WICHTIG: EINDEUTIGKEITSREGEL ===
Pro User, Monat, Jahr und Kategorie darf es NUR EIN Budget geben.
In der Datenbank ist das durch einen UniqueConstraint erzwungen:
UNIQUE(user_id, month, year, category_id)

Das bedeutet: Wenn ein Nutzer zweimal ein Budget fuer Mai 2026 / Lebensmittel setzt,
wird es beim zweiten Mal aktualisiert (UPSERT), nicht neu angelegt.

    ARCHITEKTUR-KETTE:
    View → Controller → Service → **Repository (du bist hier)** → Datenbank

    Aufgerufen von: budget_service.py
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Budget


# Kapselt reine Datenbankzugriffe fuer Budgets.
class BudgetRepository:
    """Datenbankzugriffe fuer `Budget`-Objekte.

    Methoden:
    - get_by_id: Budget per ID laden
    - get_by_scope: Budget per fachlichem Schluessel (user/monat/jahr/kategorie)
    - create: Neues Budget anlegen
    - save: Bestehendes Budget aktualisieren
    - list_by_user: Alle Budgets eines Users laden
    - delete: Budget loeschen
    """

    def __init__(self, session: Session):
        """Initialisiert das Repository mit einer offenen Datenbank-Session.

        Args:
            session: Offene SQLModel-Session (aktive DB-Verbindung).
        """
        self.session = session

    def get_by_id(self, budget_id: int) -> Budget | None:
        """Laedt ein Budget anhand seiner Datenbank-ID.

        AUFRUF-KETTE:
            budget_service.update_budget(budget_id, ...)
            → BudgetRepository.get_by_id(budget_id)
            → SQL: SELECT * FROM budgets WHERE budget_id = :budget_id

        Args:
            budget_id: Primaerschluessel des Budgets.

        Returns:
            Budget-Objekt wenn gefunden, None wenn nicht existent.
        """
        return self.session.get(Budget, budget_id)

    def get_by_scope(
        self,
        user_id: int,
        month: int,
        year: int,
        category_id: int | None,
    ) -> Budget | None:
        """Laedt ein Budget anhand seines fachlichen Schluessel (User + Monat + Jahr + Kategorie).

        AUFRUF-KETTE:
            budget_service.set_budget() (Upsert-Pruefung: existiert schon ein Budget?)
            → BudgetRepository.get_by_scope(user_id, month, year, category_id)
            → SQL: SELECT * FROM budgets WHERE user_id=? AND month=? AND year=? AND category_id=?

        WAS IST "SCOPE"?
            Der "Scope" ist der fachliche Schluessel eines Budgets: User + Monat + Jahr + Kategorie.
            Da pro Scope nur ein Budget existieren darf, kann man damit pruefen:
            "Gibt es schon ein Budget fuer diesen Nutzer, Monat, Kategorie?"
            Falls ja → aktualisieren. Falls nein → neu anlegen.

        WARUM category_id = None erlaubt?
            None bedeutet "globales Budget" (gilt fuer alle Ausgaben, nicht nur eine Kategorie).
            Auch None ist ein gueltiger Wert fuer die WHERE-Bedingung in SQL.

        Args:
            user_id: ID des Users.
            month: Monat (1-12).
            year: Jahr (z.B. 2026).
            category_id: Kategorie-ID oder None fuer globales Budget.

        Returns:
            Gefundenes Budget oder None wenn noch keins existiert.
        """
        # SELECT * FROM budgets WHERE user_id=? AND month=? AND year=? AND category_id IS ? / =?
        statement = select(Budget).where(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year,
            Budget.category_id == category_id,
        )
        return self.session.exec(statement).first()

    def create(self, budget: Budget) -> Budget:
        """Legt ein neues Budget in der Datenbank an.

        AUFRUF-KETTE:
            budget_service.set_budget() (wenn noch kein Budget fuer diesen Scope existiert)
            → BudgetRepository.create(budget)
            → SQL: INSERT INTO budgets (user_id, month, year, limit_amount, ...) VALUES (...)

        WAS PASSIERT INTERN:
            1. session.add(budget):    Budget zur Session hinzufuegen
            2. session.commit():       INSERT wird ausgefuehrt
            3. session.refresh(budget): budget_id aus DB ins Objekt laden

        Args:
            budget: Neues Budget-Objekt (budget_id noch nicht gesetzt).

        Returns:
            Gespeichertes Budget-Objekt mit der neuen budget_id.
        """
        self.session.add(budget)
        self.session.commit()
        self.session.refresh(budget)
        return budget

    def save(self, budget: Budget) -> Budget:
        """Speichert Aenderungen an einem bestehenden Budget.

        AUFRUF-KETTE:
            budget_service.set_budget() (wenn Budget fuer diesen Scope schon existiert)
            → BudgetRepository.save(budget)
            → SQL: UPDATE budgets SET limit_amount=... WHERE budget_id=...

        WAS PASSIERT INTERN:
            Hat das budget-Objekt eine budget_id → session.add() fuehrt ein UPDATE aus.
            1. session.add(budget):    UPDATE vorbereiten
            2. session.commit():       UPDATE ausfuehren
            3. session.refresh(budget): Aktuelle Werte aus DB laden

        Args:
            budget: Budget-Objekt mit geaenderten Feldern.

        Returns:
            Aktualisiertes Budget-Objekt nach dem Update.
        """
        self.session.add(budget)
        self.session.commit()
        self.session.refresh(budget)
        return budget

    def list_by_user(
        self,
        user_id: int,
        month: int | None = None,
        year: int | None = None,
    ) -> list[Budget]:
        """Laedt alle Budgets eines Users, optional gefiltert nach Monat/Jahr.

        AUFRUF-KETTE:
            budget_service.list_budgets(user_id)
            → BudgetRepository.list_by_user(user_id)
            → SQL: SELECT * FROM budgets WHERE user_id = :user_id [AND month=? AND year=?]

        PARAMETER-FLEXIBILITAET:
            Alle Parameter ausser user_id sind optional (None = kein Filter).
            Beispiele:
            - list_by_user(5)          → Alle Budgets von User 5
            - list_by_user(5, month=5) → Alle Budgets von User 5 im Mai
            - list_by_user(5, 5, 2026) → Alle Budgets von User 5 im Mai 2026

        Args:
            user_id: ID des Users, dessen Budgets geladen werden sollen.
            month: Optional: nur Budgets dieses Monats (1-12).
            year: Optional: nur Budgets dieses Jahres.

        Returns:
            Liste von Budget-Objekten (kann leer sein).
        """
        # Basis-Query: alle Budgets dieses Users
        statement = select(Budget).where(Budget.user_id == user_id)
        if month is not None:
            # Optional: Monats-Filter hinzufuegen
            statement = statement.where(Budget.month == month)
        if year is not None:
            # Optional: Jahres-Filter hinzufuegen
            statement = statement.where(Budget.year == year)
        return list(self.session.exec(statement).all())

    def delete(self, budget_id: int) -> None:
        """Loescht ein Budget dauerhaft aus der Datenbank.

        AUFRUF-KETTE:
            budget_service.delete_budget(budget_id)
            → BudgetRepository.delete(budget_id)
            → SQL: DELETE FROM budgets WHERE budget_id = :budget_id

        SICHERHEIT:
            Wenn kein Budget mit dieser ID existiert, passiert nichts (kein Fehler).
            Das ist safe - ein "Doppeltes Loeschen" ist kein Problem.

        Args:
            budget_id: ID des zu loeschenden Budgets.
        """
        budget = self.get_by_id(budget_id)
        if budget is None:
            return  # Budget existiert nicht mehr → kein Fehler, nichts zu tun
        self.session.delete(budget)  # Fuer Loeschung markieren
        self.session.commit()        # DELETE ausfuehren
