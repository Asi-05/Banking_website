"""src.data_access.repositories.budget_repository

Repository fuer Budget-Datenbankzugriffe (Data-Access-Schicht).

Dieses Repository kapselt die direkten SQLModel/SQL-Operationen fuer `Budget`.
Es enthaelt bewusst keine Fachlogik.

Hintergrund (Unique Constraint):
	In den Domain-Models existiert ein UniqueConstraint ueber
	(`user_id`, `month`, `year`, `category_id`). Pro User darf es damit fuer
	einen Monat/Jahr und eine Kategorie hoechstens ein Budget geben.
	Services koennen `get_by_scope()` nutzen, um vor dem Anlegen zu pruefen,
	ob bereits ein Budget existiert.
"""

from __future__ import annotations

from sqlmodel import Session, select

from src.domain.models import Budget


# Kapselt reine Datenbankzugriffe fuer Budgets.
class BudgetRepository:
	"""Datenbankzugriffe fuer `Budget`-Objekte.

	Hinweis:
		Die Methoden committen die Session selbst (create/save/delete). Dadurch ist
		das Repository in dieser App "selbststaendig" nutzbar, aber es bedeutet auch,
		dass Transaktionen nicht ueber mehrere Repository-Aufrufe hinweg gebuendelt
		werden.
	"""
	def __init__(self, session: Session):
		"""Initialisiert das Repository mit einer DB-Session.

		Args:
			session: Offene SQLModel-Session.
		"""
		self.session = session

	# Laedt ein Budget eindeutig nach ID.
	def get_by_id(self, budget_id: int) -> Budget | None:
		"""Lädt ein Budget anhand der ID.

		Args:
			budget_id: Primärschlüssel.

		Returns:
			Budget oder `None`.
		"""
		return self.session.get(Budget, budget_id)

	# Laedt ein Budget eindeutig nach User, Monat, Jahr und optional Kategorie.
	def get_by_scope(
		self,
		user_id: int,
		month: int,
		year: int,
		category_id: int | None,
	) -> Budget | None:
		"""Lädt ein Budget über seinen fachlichen „Scope“.

		Dieser Scope entspricht genau dem UniqueConstraint der DB.
		Damit kann der Service vor dem Anlegen prüfen, ob bereits ein Budget
		existiert, statt erst beim Commit einen DB-Fehler zu bekommen.

		Args:
			user_id: Besitzer des Budgets.
			month: Monat (1-12).
			year: Jahr.
			category_id: Kategorie-ID oder `None` für ein "Gesamtbudget".

		Returns:
			Gefundenes Budget oder `None`.
		"""
		# SELECT ... WHERE user_id AND month AND year AND category_id
		statement = select(Budget).where(
			Budget.user_id == user_id,
			Budget.month == month,
			Budget.year == year,
			Budget.category_id == category_id,
		)
		return self.session.exec(statement).first()

	# Legt ein neues Budget an und persistiert es.
	def create(self, budget: Budget) -> Budget:
		"""Speichert ein neues Budget.

		Args:
			budget: Neues Budget.

		Returns:
			Gespeichertes Budget (inkl. DB-generierter `budget_id`).
		"""
		self.session.add(budget)
		self.session.commit()
		self.session.refresh(budget)
		return budget

	# Persistiert Aenderungen eines Budgets.
	def save(self, budget: Budget) -> Budget:
		"""Speichert Änderungen an einem Budget.

		Args:
			budget: Geändertes Budget.

		Returns:
			Aktualisiertes Budget.
		"""
		self.session.add(budget)
		self.session.commit()
		self.session.refresh(budget)
		return budget

	# Gibt Budgets eines Users optional gefiltert nach Monat/Jahr zurueck.
	def list_by_user(
		self,
		user_id: int,
		month: int | None = None,
		year: int | None = None,
	) -> list[Budget]:
		"""Listet Budgets eines Users, optional gefiltert nach Monat/Jahr.

		Args:
			user_id: Besitzer.
			month: Optionaler Filter für einen Monat.
			year: Optionaler Filter für ein Jahr.

		Returns:
			Liste der passenden Budgets.
		"""
		statement = select(Budget).where(Budget.user_id == user_id)
		if month is not None:
			# Nur Budgets des Monats.
			statement = statement.where(Budget.month == month)
		if year is not None:
			# Nur Budgets des Jahres.
			statement = statement.where(Budget.year == year)
		return list(self.session.exec(statement).all())

	# Loescht ein Budget anhand der ID.
	def delete(self, budget_id: int) -> None:
		"""Löscht ein Budget, falls es existiert.

		Args:
			budget_id: ID des zu loeschenden Budgets.
		"""
		budget = self.get_by_id(budget_id)
		if budget is None:
			return
		self.session.delete(budget)
		self.session.commit()
