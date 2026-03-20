# Requirements-Dokument: Konten- & Kartenmanagement

## Quelle User Stories
- US7: Konten eröffnen und schliessen
- US8: Karten verwalten

## Erhebung
- Bedürfnis 1: Nutzer brauchen Selbstservice für Kontoeröffnung und -schließung.
- Bedürfnis 2: Nutzer brauchen schnelle Kartenverwaltung, insbesondere im Notfall.

## Analyse
### Bedürfnis 1: Kontoverwaltung
- Begründung: Kontoaktionen sollen ohne manuelle Bankkontakte möglich sein.
- Edge Cases: Schliessung mit Restguthaben, Schließung von Referenzkonten.
- Abhängigkeiten: Kontenmodell, Statusverwaltung (aktiv/geschlossen).

### Bedürfnis 2: Kartenverwaltung
- Begründung: Kartenverlust ist zeitkritisch, Sperrprozess muss sofort greifen.
- Edge Cases: Kartenbestellung für Sparkonto, wiederholte Sperranfragen.
- Abhängigkeiten: Kartenmodell, Statushistorie, Ersatzprozess.

## Dokumentierte Anforderungen
1. FR-ACC-01
   - Herleitung: Bedürfnis 1 verlangt einen vollständigen Self-Service-Prozess.
   - Anforderung: Das System muss das Eröffnen und Schließen von Privat- und Sparkonten inklusive Statusanzeige ermöglichen; für die Kontoeröffnung gelten keine weiteren fachlichen Vorbedingungen außer gültigen Login-Daten.

2. FR-ACC-02
   - Herleitung: Bedürfnis 1 verlangt sichere Schließregeln.
   - Anforderung: Das System muss eine Kontoschließung nur zulassen, wenn der Kontostand exakt 0 ist.

3. FR-CARD-01
   - Herleitung: Bedürfnis 2 verlangt zeitnahe Sicherheitsmaßnahmen.
   - Anforderung: Das System muss Karten sofort sperren können und den Sperrstatus direkt sichtbar machen.

4. FR-CARD-02
   - Herleitung: Bedürfnis 2 verlangt einen Anschlussprozess nach Sperrung.
   - Anforderung: Das System muss die Bestellung einer Ersatzkarte aus einem gesperrten Kartenkontext heraus unterstützen.

5. FR-CARD-03
   - Herleitung: Bedürfnis 2 verlangt eine eindeutige Kontozuordnung und fachliche Einschränkung.
   - Anforderung: Das System muss jede Karte verpflichtend genau einem Konto zuordnen und Kartenbestellungen ausschließlich für Privatkonten erlauben.

## Entscheidungen der Stakeholder
- Karten sind verpflichtend direkt einem Konto zugeordnet.
- Karten können nur für Privatkonten geführt und bestellt werden.
- Kontoschließung ist nur bei Kontostand 0 zulässig.
- Für Kontoeröffnung gelten keine zusätzlichen Vorbedingungen außer gültigen Login-Daten.

## Offene Punkte für Stakeholder
- Keine.