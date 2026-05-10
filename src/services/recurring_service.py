"""src.services.recurring_service

Diese Datei gehoert zur **Service-Schicht**.

Ein "Dauerauftrag" (Recurring Transaction) ist eine wiederkehrende Ausgabe, die
in bestimmten Intervallen (z.B. monatlich oder jaehrlich) faellig wird.

Wichtiges Architekturprinzip in diesem Projekt:

- Die **Datenbankabfrage** ("welche Dauerauftraege kommen prinzipiell in Frage")
	liegt im `RecurringRepository`.
- Die **Fachlogik** ("ist der Auftrag an diesem Datum wirklich faellig?") liegt
	hier in der Service-Schicht.
- Die eigentliche **Buchung** erfolgt ueber den `TransactionService`, damit
	Saldo-Updates, Validierungen und genau-eine-Quelle-Regeln zentral bleiben.

Besonders relevant ist `process_due_recurring_on_login()`: Diese Methode wird
beim Login eines Users aufgerufen und fuehrt alle zu diesem Zeitpunkt faelligen
Dauerauftraege aus.
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlmodel import Session

from src.data_access.db import engine
from src.data_access.repositories.account_repository import AccountRepository
from src.data_access.repositories.recurring_repository import RecurringRepository
from src.domain.models import Category, RecurringTransaction, Transaction
from src.services.transaction_service import transaction_service
from src.utils.validators import (
	validate_iban,
	validate_positive_amount,
	validate_recurring_interval,
)


class RecurringService:
	"""Fachlogik fuer Dauerauftraege.

	Die Kernideen:
	- Ein Dauerauftrag enthaelt Konfiguration (Betrag, Intervall, Start/Ende).
	- `last_executed` dient als *Zustand*, um die naechste Faelligkeit zu berechnen.
	- Beim Login wird die Faelligkeit gegen das Login-Datum geprueft und ggf.
	  eine neue Transaktion erzeugt.
	"""

	# Legt einen neuen Dauerauftrag mit Startkonfiguration an.
	def create_recurring(self, payload: dict) -> RecurringTransaction:
		"""Legt einen neuen Dauerauftrag in der Datenbank an.

		Es werden zwei Dinge gespeichert:
		- eine "Template-Transaktion" (`Transaction`) als Referenz/Grunddaten
		- der eigentliche `RecurringTransaction` mit Intervall/Zeitraum/Zustand

		Die Template-Transaktion wird *nicht* als echte Buchung verstanden, sondern
		als verknuepfte Basisinformation. Die reale Ausfuehrung erzeugt spaeter
		separate Transaktionen.

		Args:
			payload: Eingabedaten aus UI/Controller. Erwartete Keys:
				- `amount`, `category_id`, `account_id`, `target_iban`, `interval`, `start_date`
				Optional: `end_date`

		Returns:
			Der gespeicherte `RecurringTransaction`.

		Raises:
			ValueError: Bei ungueltigem Betrag/IBAN/Intervall oder inaktivem Konto.
			KeyError: Wenn Konto oder Kategorie nicht existiert.
		"""
		amount = float(payload["amount"])
		category_id = int(payload["category_id"])
		account_id = int(payload["account_id"])
		target_iban = str(payload["target_iban"])
		interval = str(payload["interval"])
		start_date = payload["start_date"]
		end_date = payload.get("end_date")

		# Grundvalidierungen: schnelle Checks, bevor wir DB-Zugriffe machen.
		validate_positive_amount(amount)
		validate_iban(target_iban)
		validate_recurring_interval(interval)

		if isinstance(start_date, str):
			start_date = date.fromisoformat(start_date)
		if start_date < date.today():
			raise ValueError("Startdatum darf nicht in der Vergangenheit liegen")

		with Session(engine) as session:
			account_repository = AccountRepository(session)
			# DB-Read: Konto muss existieren und aktiv sein.
			account = account_repository.get_by_id(account_id)
			if account is None:
				raise KeyError(f"Konto {account_id} nicht gefunden")
			if account.status != "aktiv":
				raise ValueError(f"Konto {account_id} ist nicht aktiv und kann nicht verwendet werden")
			# DB-Read: Kategorie muss existieren (sonst wuerde die spaetere Buchung scheitern).
			if session.get(Category, category_id) is None:
				raise KeyError(f"Kategorie {category_id} nicht gefunden")

			# Template-Transaktion: dient als "Schablone"/Referenz fuer den Dauerauftrag.
			template_transaction = Transaction(
				amount=amount,
				date=start_date,
				type="expense",
				note="Dauerauftrag",
				category_id=category_id,
				account_id=account_id,
			)
			session.add(template_transaction)
			session.commit()
			session.refresh(template_transaction)

			# `last_executed` wird initial bewusst auf den "Vorgaengertermin" gesetzt.
			# Dadurch ergibt `_next_due_date(last_executed, interval)` genau das Startdatum,
			# und der Auftrag wird ab `start_date` faellig.
			recurring = RecurringTransaction(
				amount=amount,
				target_iban=target_iban,
				interval=interval,
				start_date=start_date,
				end_date=end_date,
				last_executed=self._previous_due_date(start_date, interval),
				account_id=account_id,
				category_id=category_id,
				transaction_id=template_transaction.transaction_id,
			)
			session.add(recurring)
			session.commit()
			session.refresh(recurring)
			return recurring

	# Verarbeitet alle faelligen Dauerauftraege eines Users beim Login.
	def process_due_recurring_on_login(self, user_id: int, login_date: date) -> int:
		"""Fuehrt faellige Dauerauftraege eines Users beim Login aus.

		Die Methode arbeitet bewusst in zwei Phasen:
		1) Kandidaten aus der DB holen (Repository kann vorfiltern, z.B. nach User und Startdatum)
		2) Pro Kandidat hier im Service pruefen, ob er *wirklich* faellig ist, und dann
		   die Buchung ueber `TransactionService` ausfuehren.

		Warum mehrere Sessions?
		- Die Kandidatenliste wird aus einer Session gelesen.
		- `TransactionService.create_transaction()` arbeitet selbst mit DB-Sessions.
		- Danach wird `last_executed` aktualisiert; dafuer laden wir den Datensatz in
		  einer frischen Session erneut, damit wir nicht mit "detach"-Objekten arbeiten.

		Args:
			user_id: Der eingeloggte User.
			login_date: Referenzdatum fuer die Faelligkeit (typischerweise `date.today()`).

		Returns:
			Anzahl erfolgreich ausgefuehrter Dauerauftraege.
		"""
		executed = 0
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			# DB-Query: Kandidaten, die *potenziell* faellig sein koennen.
			# (Die exakte Intervall-Logik ist bewusst im Service.)
			due_candidates = recurring_repository.list_due_by_user(
				user_id=user_id,
				reference_date=login_date,
			)

		for recurring in due_candidates:
			# Enddatum-Regel: Nach Ablaufdatum wird nie mehr ausgefuehrt.
			if recurring.end_date is not None and recurring.end_date < login_date:
				continue
			# Intervall-Regel: Nur ausfuehren, wenn der naechste Termin erreicht ist.
			if not self._is_due(recurring, login_date):
				continue

			try:
				# Die eigentliche Buchung passiert zentral ueber den TransactionService
				# (inkl. Saldopruefungen und Kontostands-Updates).
				transaction_service.create_transaction(
					{
						"amount": recurring.amount,
						"type": "expense",
						"date": login_date,
						"category_id": recurring.category_id,
						"account_id": recurring.account_id,
						"note": "Dauerauftrag Ausfuehrung",
					}
				)
			except (ValueError, KeyError):
				# Robustheit: Wenn eine Ausfuehrung fehlschlaegt (z.B. zu wenig Saldo),
				# sollen die anderen Dauerauftraege trotzdem noch geprueft werden.
				continue
			with Session(engine) as session:
				recurring_repository = RecurringRepository(session)
				# Reload in frischer Session, damit wir garantiert ein gemanagtes ORM-Objekt haben.
				reloaded = recurring_repository.get_by_id(recurring.recurring_id)
				if reloaded is not None:
					# Zustand fortschreiben: ab jetzt gilt dieser Termin als "zuletzt ausgefuehrt".
					reloaded.last_executed = login_date
					recurring_repository.save(reloaded)
			executed += 1

		return executed

	# Prueft, ob ein einzelner Dauerauftrag zum Referenzdatum faellig ist.
	def _is_due(self, recurring: RecurringTransaction, reference_date: date) -> bool:
		"""Interne Faelligkeitspruefung fuer einen Dauerauftrag.

		Regeln:
		- Vor dem Startdatum wird nie ausgefuehrt.
		- Ansonsten wird aus `last_executed` und `interval` das naechste Datum berechnet.
		- Faellig ist alles, was am oder vor dem Referenzdatum liegt.
		"""
		if reference_date < recurring.start_date:
			return False

		next_due = self._next_due_date(recurring.last_executed, recurring.interval)
		return next_due <= reference_date

	# Berechnet das naechste Faelligkeitsdatum aus Intervall und letzter Ausfuehrung.
	def _next_due_date(self, from_date: date, interval: str) -> date:
		"""Berechnet das naechste Faelligkeitsdatum ab `from_date`.

		Warum ist das nicht einfach `from_date + 30 Tage`?
		- Monate haben unterschiedlich viele Tage.
		- Bei "31." muss es in manchen Monaten auf den 30./28./29. fallen.

		Diese Funktion nutzt deshalb `calendar.monthrange(...)`, um den letzten Tag
		des Zielmonats zu ermitteln, und clamp't den Tag darauf.
		"""
		if interval == "monthly":
			year = from_date.year + (from_date.month // 12)
			month = (from_date.month % 12) + 1
			day = min(from_date.day, calendar.monthrange(year, month)[1])
			return date(year, month, day)
		if interval == "yearly":
			year = from_date.year + 1
			day = min(from_date.day, calendar.monthrange(year, from_date.month)[1])
			return date(year, from_date.month, day)
		# Fallback: Intervalle werden vorher validiert; der Rueckgabewert ist ein
		# defensiver Default, falls doch einmal ein unbekannter Wert ankommt.
		return from_date

	# Berechnet das direkte Vorgaengerdatum zum Intervall fuer den Initialzustand.
	def _previous_due_date(self, from_date: date, interval: str) -> date:
		"""Berechnet das direkte Vorgaengerdatum zum Intervall.

		Das wird beim Anlegen eines Dauerauftrags genutzt, um `last_executed` so zu
		initialisieren, dass der naechste Termin exakt das `start_date` ist.
		"""
		if interval == "monthly":
			year = from_date.year
			month = from_date.month - 1
			if month == 0:
				month = 12
				year -= 1
			day = min(from_date.day, calendar.monthrange(year, month)[1])
			return date(year, month, day)
		if interval == "yearly":
			year = from_date.year - 1
			day = min(from_date.day, calendar.monthrange(year, from_date.month)[1])
			return date(year, from_date.month, day)
		return from_date


	# Gibt alle Dauerauftraege eines Users zurueck.
	def list_recurring(self, user_id: int) -> list[RecurringTransaction]:
		"""Listet alle Dauerauftraege eines Users.

		Args:
			user_id: Besitzer der Dauerauftraege.

		Returns:
			Liste aller `RecurringTransaction`-Objekte des Users.
		"""
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			return recurring_repository.list_by_user(user_id)

	# Aktualisiert einen Dauerauftrag.
	def update_recurring(self, recurring_id: int, payload: dict) -> RecurringTransaction:
		"""Aktualisiert Felder eines Dauerauftrags (teilweise Updates).

		Die Methode ist so implementiert, dass nur die Keys aus `payload` geaendert
		werden. Das ist praktisch fuer Formulare, bei denen nicht immer alle Felder
		mitgesendet werden.

		Args:
			recurring_id: ID des Dauerauftrags.
			payload: Felder, die aktualisiert werden sollen.

		Returns:
			Der gespeicherte Dauerauftrag nach dem Update.

		Raises:
			KeyError: Wenn der Dauerauftrag nicht existiert.
			ValueError: Bei ungueltigen Eingaben (Betrag/IBAN/Intervall).
		"""
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			recurring = recurring_repository.get_by_id(recurring_id)
			if recurring is None:
				raise KeyError(f"Dauerauftrag {recurring_id} nicht gefunden")

			# Validiere und aktualisiere Felder
			if "amount" in payload:
				amount = float(payload["amount"])
				validate_positive_amount(amount)
				recurring.amount = amount

			if "interval" in payload:
				interval = str(payload["interval"])
				validate_recurring_interval(interval)
				recurring.interval = interval

			if "target_iban" in payload:
				target_iban = str(payload["target_iban"])
				validate_iban(target_iban)
				recurring.target_iban = target_iban

			if "end_date" in payload:
				end_date_val = payload["end_date"]
				# UI kann ISO-Strings liefern; wir normalisieren hier auf `date | None`.
				if isinstance(end_date_val, str):
					end_date_val = date.fromisoformat(end_date_val) if end_date_val else None
				recurring.end_date = end_date_val

			if "category_id" in payload and payload["category_id"] is not None:
				# Hinweis: Existenzcheck fuer die Kategorie wird hier nicht gemacht;
				# das kann je nach UI/Controller bereits sichergestellt sein.
				recurring.category_id = int(payload["category_id"])

			if "account_id" in payload and payload["account_id"] is not None:
				# Hinweis: Auch fuer Konto-Validierung verlassen wir uns auf UI/Controller
				# oder auf spaetere Buchungsfehler; je nach Bedarf koennte man hier
				# analog zu `create_recurring` validieren.
				recurring.account_id = int(payload["account_id"])

			return recurring_repository.save(recurring)

	# Liefert einen einzelnen Dauerauftrag per ID.
	def get_by_id(self, recurring_id: int) -> RecurringTransaction | None:
		"""Liefert einen Dauerauftrag per ID.

		Returns `None`, wenn kein Datensatz existiert.
		"""
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			return recurring_repository.get_by_id(recurring_id)

	# Oeffentliche Version von _next_due_date fuer die Controller-Schicht.
	def next_execution_date(self, last_executed: date, interval: str) -> date:
		"""Berechnet das naechste Ausfuehrungsdatum (oeffentliche Helper-Methode).

		Diese Methode ist fuer Controller/Views gedacht, die nur das Datum berechnen
		muessen, aber nicht die komplette Due-Logik kennen sollen.
		"""
		return self._next_due_date(last_executed, interval)

	# Loescht einen Dauerauftrag und die verknuepfte Template-Transaktion.
	def delete_recurring(self, recurring_id: int) -> None:
		"""Loescht einen Dauerauftrag und die verknuepfte Template-Transaktion.

		Warum wird auch die Template-Transaktion geloescht?
		- Sie hat in dieser App keinen Zweck mehr, wenn der Dauerauftrag nicht mehr
		  existiert.
		
		Args:
			recurring_id: ID des zu loeschenden Dauerauftrags.

		Raises:
			KeyError: Wenn der Dauerauftrag nicht existiert.
		"""
		with Session(engine) as session:
			recurring_repository = RecurringRepository(session)
			recurring = recurring_repository.get_by_id(recurring_id)
			if recurring is None:
				raise KeyError(f"Dauerauftrag {recurring_id} nicht gefunden")

			transaction_id = recurring.transaction_id

			# Zuerst Dauerauftrag löschen, dann Template-Transaktion
			recurring_repository.delete(recurring_id)

			if transaction_id:
				# Imports lokal, weil sie nur fuer diesen Pfad benoetigt werden.
				from src.data_access.repositories.transaction_repository import TransactionRepository
				from src.domain.models import Transaction
				transaction_repository = TransactionRepository(session)
				transaction = session.get(Transaction, transaction_id)
				if transaction is not None:
					transaction_repository.delete(transaction)


recurring_service = RecurringService()
