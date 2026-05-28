# Requirements-Dokument: Budgetierung & Planung

## Quelle User Stories
- US5: Monatliche Limits setzen mit Warnung bei Überschreitung
- US6: Wiederkehrende Zahlungen für Kategorien erfassen

## Erhebung
- Bedürfnis 1: Nutzer brauchen monatliche Budgetgrenzen pro Kategorie oder gesamt.
- Bedürfnis 2: Nutzer brauchen frühzeitige Warnungen bei Budgetüberschreitung.
- Bedürfnis 3: Nutzer brauchen die Möglichkeit, Fixkosten als wiederkehrende Zahlungen abzubilden.

## Analyse
### Bedürfnis 1: Budgetgrenzen
- Begründung: Klare Limits sind Voraussetzung für aktives Finanzverhalten.
- Edge Cases: Budget = 0, negative Budgetwerte, mehrere Budgets in einer Kategorie.
- Abhängigkeiten: Budgetdatenmodell, Zuordnung zu Kategorien und Zeiträumen.

### Bedürfnis 2: Warnungen
- Begründung: Warnungen müssen rechtzeitig erfolgen, sonst verlieren sie ihren Nutzen.
- Edge Cases: Wiederholte Warnungen im selben Zeitraum, Grenzwerte exakt erreicht.
- Abhängigkeiten: Triggerlogik bei neuer/aktualisierter Transaktion.

### Bedürfnis 3: Wiederkehrende Zahlungen
- Begründung: Fixkosten müssen nicht jedes Mal manuell erfasst werden.
- Edge Cases: Monatsende bei kurzen Monaten, Pausieren einzelner Serien.
- Abhängigkeiten: Scheduler-Logik oder periodische Generierung beim Login, IBAN-Validierung für den Zahlungsempfänger.

## Dokumentierte Anforderungen
1. FR-BUD-01
   - Herleitung: Bedürfnis 1 verlangt konfigurierbare Monatsbudgets.
   - Anforderung: Das System muss das Anlegen und Ändern monatlicher Budgetlimits pro Kategorie ermöglichen.

2. FR-BUD-01a
   - Herleitung: Das Budget-Objekt muss für ORM und Validierung klar definiert sein.
   - Anforderung: Das System muss ein Budget-Objekt mit folgenden Feldern speichern: budget_id as int, user_id as int, limit_amount as float, current_spending as float, month as int, year as int, category_id as int (optional – falls leer gilt das Budget global). Ein User darf pro Monat und Jahr und Kategorie nur ein aktives Budget haben.

3. FR-BUD-02
   - Herleitung: Bedürfnis 2 verlangt automatische Überwachung der Limits.
   - Anforderung: Das System muss bei Erreichen oder Überschreiten eines Limits eine sichtbare Warnung erzeugen.

4. FR-BUD-03
   - Herleitung: Bedürfnis 2 verlangt nachvollziehbare Warnbedingungen.
   - Anforderung: Das System muss den Auslöser jeder Budgetwarnung mit Kategorie, Zeitraum und Betrag anzeigen.

5. FR-BUD-04
   - Herleitung: Bedürfnis 3 verlangt planbare Erfassung von Fixkosten.
   - Anforderung: Das System muss wiederkehrende Zahlungen mit amount, category_id, account_id, target_iban, interval (monthly/yearly) und start_date speichern und automatisch in Transaktionen überführen können. Das System muss beim Login des Users automatisch prüfen, ob fällige Daueraufträge vorhanden sind, und diese sofort als reguläre Transaktionen in die Datenbank buchen. Vor dem Speichern und vor der Ausführung muss target_iban im zulässigen IBAN-Format validiert werden.

## Entscheidungen der Stakeholder
- Bei 80 Prozent Budgetverbrauch wird keine Warnung ausgelöst.
- Für wiederkehrende Zahlungen werden die Intervalle monatlich und jährlich benötigt.
- Fällige Daueraufträge werden beim Login des Users automatisch gebucht (keine externe Scheduler-Infrastruktur notwendig).