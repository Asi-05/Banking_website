# Requirements-Dokument: Konten- & Kartenmanagement

## Quelle User Stories
- US7: Konten eröffnen und schließen
- US8: Karten verwalten

## Erhebung
- Bedürfnis 1: Nutzer brauchen Selbstservice für Kontoeröffnung und -schließung.
- Bedürfnis 2: Nutzer brauchen schnelle Kartenverwaltung, insbesondere im Notfall.

## Analyse
### Bedürfnis 1: Kontoverwaltung
- Begründung: Kontoaktionen sollen ohne manuelle Bankkontakte möglich sein.
- Edge Cases: Schließung mit Restguthaben, Schließung von Referenzkonten.
- Abhängigkeiten: Kontenmodell, Statusverwaltung (aktiv/geschlossen).

### Bedürfnis 2: Kartenverwaltung
- Begründung: Kartenverlust ist zeitkritisch, Sperrprozess muss sofort greifen.
- Edge Cases: Mehrere Karten pro Konto, wiederholte Sperranfragen.
- Abhängigkeiten: Kartenmodell, Statushistorie, Ersatzprozess.

## Dokumentierte Anforderungen
1. FR-ACC-01
   - Herleitung: Bedürfnis 1 verlangt einen vollständigen Self-Service-Prozess.
   - Anforderung: Das System muss das Eröffnen und Schließen von Privat- und Sparkonten inklusive Statusanzeige ermöglichen.

2. FR-ACC-02
   - Herleitung: Bedürfnis 1 verlangt sichere Schließregeln.
   - Anforderung: Das System muss eine Kontoschließung nur zulassen, wenn definierte Vorbedingungen erfüllt sind (z. B. kein negatives Saldo).

3. FR-CARD-01
   - Herleitung: Bedürfnis 2 verlangt zeitnahe Sicherheitsmaßnahmen.
   - Anforderung: Das System muss Karten sofort sperren können und den Sperrstatus direkt sichtbar machen.

4. FR-CARD-02
   - Herleitung: Bedürfnis 2 verlangt einen Anschlussprozess nach Sperrung.
   - Anforderung: Das System muss die Bestellung einer Ersatzkarte aus einem gesperrten Kartenkontext heraus unterstützen.

## Offene Punkte für Stakeholder
- Welche fachlichen Vorbedingungen gelten für Kontoeröffnung/-schließung?
- Sollen Karten direkt einem Konto verpflichtend zugeordnet sein oder optional kontounabhängig geführt werden?