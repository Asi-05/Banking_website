# Requirements-Dokument: Konten- & Kartenmanagement

## Quelle User Stories
- US7: Konten eröffnen und schliessen
- US8: Karten verwalten
- US9: Unabhängige Kreditkarten verwalten

## Erhebung
- Bedürfnis 1: Nutzer brauchen Selbstservice für Kontoeröffnung und -schließung.
- Bedürfnis 2: Nutzer brauchen schnelle Kartenverwaltung, insbesondere im Notfall.
- Bedürfnis 3: Nutzer brauchen eine eigenständige Kreditkarte mit eigenem Kreditrahmen.

## Analyse
### Bedürfnis 1: Kontoverwaltung
- Begründung: Kontoaktionen sollen ohne manuelle Bankkontakte möglich sein.
- Edge Cases: Schliessung mit Restguthaben, Schließung von Referenzkonten.
- Abhängigkeiten: Kontenmodell, Statusverwaltung (aktiv/geschlossen).

### Bedürfnis 2: Kartenverwaltung
- Begründung: Kartenverlust ist zeitkritisch, Sperrprozess muss sofort greifen.
- Edge Cases: Kartenbestellung für Sparkonto, wiederholte Sperranfragen.
- Abhängigkeiten: Kartenmodell, Statushistorie, Ersatzprozess.

### Bedürfnis 3: Unabhängige Kreditkarte
- Begründung: Kreditkartenzahlungen sollen unabhängig vom Kontostand möglich sein.
- Edge Cases: Gewünschtes Limit außerhalb erlaubter Grenzen, Überschreitung des Kreditrahmens.
- Abhängigkeiten: Kreditkartenmodell mit Kreditrahmen und genutztem Saldo.

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

6. FR-CC-01
   - Herleitung: Bedürfnis 3 verlangt eine eigenständige Kreditkartenfunktion.
   - Anforderung: Das System muss die Bestellung einer unabhängigen Kreditkarte pro User ermöglichen und ein Kreditkarten-Objekt mit festgelegtem Kreditrahmen anlegen.

7. FR-CC-02
   - Herleitung: Bedürfnis 3 verlangt nachvollziehbare Nutzung des Kreditrahmens.
   - Anforderung: Das System muss eine Kreditkartenbuchung als normales Transaction-Objekt speichern (nicht als separates Buchungsobjekt). Für Kreditkartenbuchungen müssen die Felder transaction_id, creditcard_id, amount, type, date, category_id und note gespeichert werden; account_id und card_id müssen dabei leer sein. Vor dem Buchen muss gelten: available_limit = credit_limit - used_balance. Eine Ausgabenbuchung darf nur ausgeführt werden, wenn amount <= available_limit. Nach erfolgreicher Buchung muss used_balance aktualisiert werden (bei Ausgabe: used_balance_neu = used_balance_alt + amount) und das verfügbare Limit neu berechnet werden.

8. FR-CC-03
   - Herleitung: Bedürfnis 3 verlangt Notfall- und Ersatzprozesse auch für unabhängige Kreditkarten.
   - Anforderung: Das System muss unabhängige Kreditkarten sperren und ersetzen können, inklusive sofort sichtbarem Kartenstatus.

## Entscheidungen der Stakeholder
- Karten sind verpflichtend direkt einem Konto zugeordnet.
- Karten können nur für Privatkonten geführt und bestellt werden.
- Kontoschließung ist nur bei Kontostand 0 zulässig.
- Für Kontoeröffnung gelten keine zusätzlichen Vorbedingungen außer gültigen Login-Daten.
- Unabhängige Kreditkarten sind zusätzlich zulässig und werden pro User mit eigenem Kreditrahmen geführt.

