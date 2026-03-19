# Requirements-Dokument: Finanzverwaltung (Core Features)

## Quelle User Stories
- US1: Transaktion manuell erfassen inkl. Kategorie
- US2: Transaktion bearbeiten oder löschen
- US3: Transaktionen nach Datum und Kategorie filtern

## Erhebung
- Bedürfnis 1: Nutzer brauchen eine schnelle, manuelle Erfassung von Einnahmen und Ausgaben.
- Bedürfnis 2: Nutzer brauchen eine einheitliche Kategorisierung, um Ausgabestrukturen zu erkennen.
- Bedürfnis 3: Nutzer brauchen Korrekturmöglichkeiten bei Fehleingaben.
- Bedürfnis 4: Nutzer brauchen gezielte Such- und Filtermöglichkeiten für alte  Transaktionen.

## Analyse
### Bedürfnis 1: Manuelle Erfassung
- Begründung: Die App muss den Alltag unterstützen, auch wenn keine automatische Kontobuchung vorliegt.
- Edge Cases: Negative oder extrem hohe Beträge, fehlendes Datum, ungültiges Zahlenformat.
- Abhängigkeiten: Konstante Speicherung in der Datenbank.

### Bedürfnis 2: Kategorisierung
- Begründung: Nur kategorisierte Daten ermöglichen aussagekräftige Auswertungen und Budgetwarnungen.
- Edge Cases: Leere Kategorie, freie Kategoriebezeichnungen mit Tippfehlern, nachträglicher Kategorienwechsel. (Nur Sonstiges als Sonderfall zulassen?)
- Abhängigkeiten: Kategorienmodell und Referenz auf Transaktionen.

### Bedürfnis 3: Bearbeiten/Löschen
- Begründung: Nutzer müssen Datenqualität selbst korrigieren können.
- Edge Cases: Bearbeitung bereits ausgewerteter Transaktionen, versehentliches Löschen.
- Abhängigkeiten: Änderungslogik, konsistente Neuberechnung von Summen.

### Bedürfnis 4: Filtern
- Begründung: Ohne Filter sind große Datenmengen nicht nutzbar.
- Edge Cases: Leere Trefferlisten, ungültige Datumsintervalle (von > bis), kombinierte Filter.
- Abhängigkeiten: Indizierung/Query-Logik in der Datenbank.

## Dokumentierte Anforderungen
1. FR-FIN-01
   - Herleitung: Bedürfnis 1 erfordert eine vollständige manuelle Eingabe mit Pflichtfeldern.
   - Anforderung: Das System muss eine manuelle Erfassung von Einnahmen und Ausgaben mit den Feldern Betrag, Datum, Typ (Einnahme/Ausgabe) und Beschreibung bereitstellen.

2. FR-FIN-02
   - Herleitung: Bedürfnis 1 und 2 erfordern valide und strukturierte Daten.
   - Anforderung: Das System muss Eingaben validieren und fehlerhafte Werte (z. B. nicht numerischer Betrag, fehlendes Datum) mit verständlichen Fehlermeldungen ablehnen.

3. FR-FIN-03
   - Herleitung: Bedürfnis 2 erfordert eine stabile Kategorisierung je Transaktion.
   - Anforderung: Das System muss jeder Transaktion genau eine Kategorie zuweisen und eine Änderung der Kategorie nachträglich erlauben.

4. FR-FIN-04
   - Herleitung: Bedürfnis 3 erfordert Korrektur- und Löschprozesse.
   - Anforderung: Das System muss das Bearbeiten und Löschen vorhandener Transaktionen ermöglichen und alle betroffenen Summen unmittelbar neu berechnen.

5. FR-FIN-05
   - Herleitung: Bedürfnis 4 erfordert kombinierbare Suchkriterien.
   - Anforderung: Das System muss Transaktionen nach Datumsbereich und Kategorie filtern können, inklusive kombinierter Filteranfragen.

## Offene Punkte für Stakeholder
- Sollen Kategorien frei anlegbar sein oder aus einer festen Liste stammen?
- Wird für Löschvorgänge ein Soft-Delete (Wiederherstellung) benötigt?