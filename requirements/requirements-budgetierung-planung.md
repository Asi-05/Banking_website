# Requirements-Dokument: Budgetierung & Planung

## Quelle User Stories
- US9: Monatliche Limits setzen mit Warnung bei Überschreitung
- US10: Wiederkehrende Zahlungen für Kategorien erfassen

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
- Abhängigkeiten: Scheduler-Logik oder periodische Generierung beim Login.

## Dokumentierte Anforderungen
1. FR-BUD-01
   - Herleitung: Bedürfnis 1 verlangt konfigurierbare Monatsbudgets.
   - Anforderung: Das System muss das Anlegen und Ändern monatlicher Budgetlimits pro Kategorie ermöglichen.

2. FR-BUD-02
   - Herleitung: Bedürfnis 2 verlangt automatische Überwachung der Limits.
   - Anforderung: Das System muss bei Erreichen oder Überschreiten eines Limits eine sichtbare Warnung erzeugen.

3. FR-BUD-03
   - Herleitung: Bedürfnis 2 verlangt nachvollziehbare Warnbedingungen.
   - Anforderung: Das System muss den Auslöser jeder Budgetwarnung mit Kategorie, Zeitraum und Betrag anzeigen.

4. FR-BUD-04
   - Herleitung: Bedürfnis 3 verlangt planbare Erfassung von Fixkosten.
   - Anforderung: Das System muss wiederkehrende Zahlungen mit Betrag, Kategorie, Intervall und Startdatum speichern und automatisch in Transaktionen überführen können.

## Entscheidungen der Stakeholder
- Bei 80 Prozent Budgetverbrauch wird keine Warnung ausgelöst.
- Für wiederkehrende Zahlungen werden alle drei Intervalle benötigt: monatlich, wöchentlich und jährlich.