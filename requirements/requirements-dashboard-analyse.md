# Requirements-Dokument: Dashboard & Analyse

## Quelle User Stories
- US4: Dashboard und Bilanz anzeigen

## Erhebung
- Bedürfnis 1: Nutzer brauchen eine schnelle visuelle Übersicht über Finanzdaten.
- Bedürfnis 2: Nutzer brauchen jederzeit eine klare Aussage zur verfügbaren Gesamtbilanz.
- Bedürfnis 3: Nutzer brauchen periodische Auswertungen zur Entwicklung ihrer Finanzen.

## Analyse
### Bedürfnis 1: Visuelles Dashboard
- Begründung: Diagramme reduzieren Interpretationsaufwand gegenüber Rohlisten.
- Edge Cases: Keine Transaktionen vorhanden, sehr grosse Datenmengen.
- Abhängigkeiten: Aggregationslogik, Chart-Komponenten.

### Bedürfnis 2: Gesamtbilanz
- Begründung: Die Bilanz ist zentrale Steuergröße für Entscheidungen.
- Edge Cases: Negative Bilanz, Rundungsfragen bei Währung.
- Abhängigkeiten: Konsistente Berechnung aus allen relevanten Kontoständen/Transaktionen.

### Bedürfnis 3: Zeitraum-Summen
- Begründung: Trends sind nur über Zeitfenster erkennbar.
- Edge Cases: Leere Zeiträume, überlappende Intervalle, ungültige Datumsgrenzen.
- Abhängigkeiten: Datumsfilter, Aggregation pro Zeitraum.

## Dokumentierte Anforderungen
1. FR-DASH-01
   - Herleitung: Bedürfnis 1 verlangt eine sofort erfassbare Übersicht.
   - Anforderung: Das System muss auf der Startseite ein Dashboard mit mindestens einer grafischen Darstellung von Einnahmen und Ausgaben bereitstellen.

2. FR-DASH-01a
   - Herleitung: Das ChartData-Objekt muss für die Diagrammdarstellung klar definiert sein.
   - Anforderung: Das System muss für die Diagrammdarstellung ein ChartData-Objekt mit folgenden Feldern bereitstellen: label as str (z.B. Monatsname oder Kategorie), income as float, expenses as float. Die Liste der ChartData-Objekte wird nach Zeitraum aggregiert und an die UI-Komponente übergeben.

3. FR-DASH-02
   - Herleitung: Bedürfnis 2 verlangt eine laufend aktuelle Bilanzanzeige.
   - Anforderung: Das System muss die aktuelle Gesamtbilanz prominent anzeigen und nach jeder relevanten Datenänderung aktualisieren.

4. FR-DASH-03
   - Herleitung: Bedürfnis 3 verlangt flexible Zeitraum-Analysen.
   - Anforderung: Das System muss Summen für auswählbare Zeiträume (z. B. aktueller Monat) berechnen und anzeigen.

## Entscheidungen der Stakeholder
- Für die Darstellung der Bilanzen werden Kreisdiagramm verwendet.

## Offene Punkte für Stakeholder
- Keine.
