"""src.services.dashboard_service

Diese Datei gehoert zur **Service-Schicht**.

=== WAS MACHT DIESER SERVICE? ===
Der DashboardService berechnet die Kennzahlen fuer das Dashboard:

    1. TOTAL BALANCE:   Summe aller aktuellen Kontostaende des Users.
    2. TOTAL INCOME:    Summe aller Einnahmen im gewaehlten Zeitraum.
    3. TOTAL EXPENSES:  Summe aller Ausgaben im gewaehlten Zeitraum.
    4. CHART DATA:      Einnahmen und Ausgaben gruppiert pro Monat (YYYY-MM).

=== WICHTIG: UMBUCHUNGEN HERAUSFILTERN ===
Wenn ein User CHF 500 von Konto A auf Konto B umbucht, entstehen ZWEI Transaktionen:
    - Konto A: -500 (expense = "Kontoumbuchung Ausgang")
    - Konto B: +500 (income = "Kontoumbuchung Eingang")

Das Dashboard soll diese Umbuchungen NICHT zaehlen:
    - Sie erhoehen nicht das echte Einkommen.
    - Sie erhoehen nicht die echten Ausgaben.
    - Sie verschieben nur Geld innerhalb des Vermoegens.

Erkennung: Transaktionen mit "Kontoumbuchung" im Note-Feld werden herausgefiltert.
(Alternativ koennte man das Transfer-Datensatz pruefen, aber Note-Filter ist einfacher.)

=== TOTAL BALANCE vs. ZEITRAUM ===
    total_balance: Aktueller Gesamtkontostand (NICHT im Zeitraum, sondern JETZT).
                   Das ist eine Momentaufnahme, keine historische Berechnung.
    total_income / total_expenses: NUR Transaktionen IM gewaehlten Zeitraum.

=== CHART DATA - WAS IST DAS? ===
`chart_data` ist eine Liste von ChartData-Objekten, je eines pro Monat:
    ChartData(label="2026-04", income=3500.0, expenses=1200.0)
    ChartData(label="2026-05", income=3500.0, expenses=980.0)
Sortiert nach label (chronologisch = ältester Monat zuerst).
Die View verwendet diese Daten, um ein Balken- oder Liniendiagramm anzuzeigen.

=== ARCHITEKTUR-KETTE ===
    View (dashboard_view.py) → Controller (dashboard_controller.py)
    → **DashboardService (du bist hier)**
    → AccountRepository (Kontostaende laden)
    → TransactionRepository (Transaktionen filtern)

=== SINGLETON-INSTANZ ===
    Am Ende der Datei steht: `dashboard_service = DashboardService()`
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.transaction_repository import TransactionRepository
from src.domain.models import ChartData, DashboardSummary
from src.utils.validators import validate_date_range


class DashboardService:
    """Fachlogik fuer Dashboard-Aggregationen."""

    def dashboard(self, user_id: int, start_date: date, end_date: date) -> DashboardSummary:
        """Berechnet Dashboard-Kennzahlen fuer einen User und Zeitraum.

        AUFRUF-KETTE:
            dashboard_controller.get_summary(user_id, start_date, end_date)
            → DashboardService.dashboard(user_id, start_date, end_date)
            → validate_date_range(start_date, end_date)
            → AccountRepository.list_by_user(user_id)          [Kontostaende laden]
            → TransactionRepository.filter_transactions(...)   [Transaktionen filtern]
            → Umbuchungen herausfiltern (Note = "Kontoumbuchung...")
            → Einnahmen und Ausgaben summieren
            → Pro Monat gruppieren (defaultdict)
            → DashboardSummary zurueckgeben

        RUECKGABE-KETTE:
            DashboardSummary → dashboard_controller
            → View zeigt: Kontostandkarte, Einnahmen-/Ausgaben-Karte, Diagramm

        WAS IST `DashboardSummary`?
            Ein Datenmodell (dataclass/Pydantic) in `domain/models.py`:
            - total_balance:  float (aktueller Gesamtkontostand)
            - total_income:   float (Einnahmen im Zeitraum)
            - total_expenses: float (Ausgaben im Zeitraum)
            - chart_data:     list[ChartData] (pro Monat)

        UMBUCHUNGS-ERKENNUNG:
            `getattr(t, "note", None)` wird verwendet, weil einige Test-Fixtures
            keine `note`-Attribute haben. Das ist defensives Programmieren.
            In Produktion haben alle Transaction-Objekte ein `note`-Feld.

        Args:
            user_id: Datenbank-ID des Users, dessen Daten ausgewertet werden.
            start_date: Start des Auswertungszeitraums (inklusive).
            end_date: Ende des Auswertungszeitraums (inklusive).

        Returns:
            DashboardSummary mit total_balance, total_income, total_expenses, chart_data.

        Raises:
            ValueError: Wenn start_date > end_date.
        """
        validate_date_range(start_date, end_date)

        with Session(engine) as session:
            account_repository = AccountRepository(session)
            transaction_repository = TransactionRepository(session)

            # Alle Konten des Users laden.
            accounts = account_repository.list_by_user(user_id)

            # Gesamtkontostand = Summe aller aktuellen Kontostaende.
            # ACHTUNG: Das ist der Stand JETZT, nicht am Anfang des Zeitraums.
            total_balance = sum(account.balance for account in accounts)

            # Transaktionen im Zeitraum laden (gefiltert auf diesen User).
            transactions = transaction_repository.filter_transactions(
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
            )

            # Umbuchungen herausfiltern: Eine Kontoumbuchung erzeugt 2 Transaktionen
            # ("Kontoumbuchung Ausgang" und "Kontoumbuchung Eingang"). Fuer die
            # Einnahmen-/Ausgaben-Darstellung sollen diese nicht gezaehlt werden.
            non_transfer_transactions = [
                t for t in transactions
                if not (getattr(t, "note", None) and "Kontoumbuchung" in getattr(t, "note", ""))
            ]

            # Einnahmen summieren (nur Transaktionen ohne Umbuchung).
            total_income = sum(t.amount for t in non_transfer_transactions if t.type == "income")

            # Ausgaben summieren. abs() damit immer positiv (fuer Darstellung in der UI).
            total_expenses = sum(abs(t.amount) for t in non_transfer_transactions if t.type == "expense")

            # Monatliche Gruppierung fuer das Diagramm.
            # defaultdict(lambda: {"income": 0.0, "expenses": 0.0}):
            # → Wenn ein Monat noch nicht im Dict ist, wird automatisch {income:0, expenses:0} erstellt.
            grouped: dict[str, dict[str, float]] = defaultdict(
                lambda: {"income": 0.0, "expenses": 0.0}
            )
            for transaction in non_transfer_transactions:
                # label = "YYYY-MM" (z.B. "2026-05")
                label = transaction.date.strftime("%Y-%m")
                if transaction.type == "income":
                    grouped[label]["income"] += transaction.amount
                else:
                    grouped[label]["expenses"] += abs(transaction.amount)

            # Sortiert nach label (YYYY-MM = alphabetisch = chronologisch).
            chart_data = [
                ChartData(
                    label=label,
                    income=values["income"],
                    expenses=values["expenses"],
                )
                for label, values in sorted(grouped.items())
            ]

            return DashboardSummary(
                total_balance=total_balance,
                total_income=total_income,
                total_expenses=total_expenses,
                chart_data=chart_data,
            )


# Singleton-Instanz: wird ueberall im Projekt importiert.
# Import-Muster: `from src.services.dashboard_service import dashboard_service`
dashboard_service = DashboardService()
