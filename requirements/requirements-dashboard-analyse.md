# Requirements-Dokument: Dashboard & Analyse

## Quelle User Stories
- US5: Dashboard mit Charts
- US6: Aktuelle Gesamtbilanz anzeigen
- US7: Summen für Zeiträume abrufen
- US8 (optional): Vier grösste Aktienticker auf Startseite

## Erhebung
- Bedürfnis 1: Nutzer brauchen eine schnelle visuelle Übersicht über Finanzdaten.
- Bedürfnis 2: Nutzer brauchen jederzeit eine klare Aussage zur verfügbaren Gesamtbilanz.
- Bedürfnis 3: Nutzer brauchen periodische Auswertungen zur Entwicklung ihrer Finanzen.
- Bedürfnis 4 (optional): Nutzer möchten Marktindikatoren auf der Startseite sehen.

## Analyse
### Bedürfnis 1: Visuelles Dashboard
- Begründung: Diagramme reduzieren Interpretationsaufwand gegenüber Rohlisten.
- Edge Cases: Keine Transaktionen vorhanden, sehr große Datenmengen.
- Abhängigkeiten: Aggregationslogik, Chart-Komponenten.

### Bedürfnis 2: Gesamtbilanz
- Begründung: Die Bilanz ist zentrale Steuergröße für Entscheidungen.
- Edge Cases: Negative Bilanz, Rundungsfragen bei Währung.
- Abhängigkeiten: Konsistente Berechnung aus allen relevanten Kontoständen/Transaktionen.

### Bedürfnis 3: Zeitraum-Summen
- Begründung: Trends sind nur über Zeitfenster erkennbar.
- Edge Cases: Leere Zeiträume, überlappende Intervalle, ungültige Datumsgrenzen.
- Abhängigkeiten: Datumsfilter, Aggregation pro Zeitraum.

### Bedürfnis 4: Aktienticker (optional)
- Begründung: Zusatznutzen für interessierte Nutzer, aber nicht kritisch für Kernziel.
- Edge Cases: Datenquelle nicht erreichbar, verzögerte Kurse.
- Abhängigkeiten: Externe API oder statischer Demo-Datensatz.

## Dokumentierte Anforderungen
1. FR-DASH-01
   - Herleitung: Bedürfnis 1 verlangt eine sofort erfassbare Übersicht.
   - Anforderung: Das System muss auf der Startseite ein Dashboard mit mindestens einer grafischen Darstellung von Einnahmen und Ausgaben bereitstellen.

2. FR-DASH-02
   - Herleitung: Bedürfnis 2 verlangt eine laufend aktuelle Bilanzanzeige.
   - Anforderung: Das System muss die aktuelle Gesamtbilanz prominent anzeigen und nach jeder relevanten Datenänderung aktualisieren.

3. FR-DASH-03
   - Herleitung: Bedürfnis 3 verlangt flexible Zeitraum-Analysen.
   - Anforderung: Das System muss Summen für auswählbare Zeiträume (z. B. aktueller Monat) berechnen und anzeigen.

4. FR-DASH-04 (optional)
   - Herleitung: Bedürfnis 4 ist ein optionales Informationsfeature.
   - Anforderung: Das System kann die vier grössten Aktienticker auf der Startseite anzeigen; bei fehlender Datenquelle darf die App-Kernfunktion nicht beeinträchtigt werden.

## Offene Punkte für Stakeholder
- Welche Diagrammtypen werden bevorzugt (Balken, Linie, Kreis)?
- Soll US8 im MVP enthalten sein oder auf eine spätere Version verschoben werden?