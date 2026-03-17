# Requirements-Dokument: Sicherheit & Onboarding

## Quelle User Stories
- US17: Anmeldung mit Vertragsnummer und Passwort
- US18: Neues Benutzerkonto erstellen

## Erhebung
- Bedürfnis 1: Nutzer brauchen einen verlässlichen Login mit Vertragsnummer und Passwort.
- Bedürfnis 2: Nutzer brauchen einen klaren Registrierungsprozess für neue Konten.
- Bedürfnis 3: Nutzer brauchen Schutz ihrer Zugangsdaten und nachvollziehbare Fehlermeldungen.

## Analyse
### Bedürfnis 1: Login
- Begründung: Ohne sichere Authentifizierung sind alle weiteren Funktionen nicht vertrauenswürdig.
- Edge Cases: Falsche Zugangsdaten, gesperrte Konten, mehrfach fehlgeschlagene Anmeldungen.
- Abhängigkeiten: Benutzerverwaltung, Passwort-Hashing.

### Bedürfnis 2: Registrierung
- Begründung: Der Einstieg in die App muss ohne Supportaufwand möglich sein.
- Edge Cases: Doppelte Vertragsnummer, schwaches Passwort, unvollständige Eingaben.
- Abhängigkeiten: Eindeutigkeitsprüfung, Validierungsregeln.

### Bedürfnis 3: Sicherheitsfeedback
- Begründung: Fehlermeldungen sollen helfen, dürfen aber keine sensiblen Informationen preisgeben.
- Edge Cases: Unterschiedliche Meldungen für unbekannte Nutzer vs. falsches Passwort.
- Abhängigkeiten: Security-Richtlinien für Fehlermeldungen.

## Dokumentierte Anforderungen
1. FR-AUTH-01
   - Herleitung: Bedürfnis 1 verlangt standardisierte Zugangsdaten.
   - Anforderung: Das System muss eine Anmeldung mit Vertragsnummer und Passwort bereitstellen.

2. FR-AUTH-02
   - Herleitung: Bedürfnis 1 und 3 verlangen sicheren Umgang mit Credentials.
   - Anforderung: Das System muss Passwörter gehasht speichern und darf niemals Klartext-Passwörter persistieren oder anzeigen.

3. FR-AUTH-03
   - Herleitung: Bedürfnis 1 verlangt Schutz vor Missbrauch.
   - Anforderung: Das System muss nach wiederholten Fehlversuchen eine Schutzmaßnahme auslösen (z. B. temporäre Sperre oder Verzögerung).

4. FR-REG-01
   - Herleitung: Bedürfnis 2 verlangt einen vollständigen Self-Service-Registrierungsprozess.
   - Anforderung: Das System muss die Erstellung eines neuen Benutzerkontos mit Vertragsnummer, Passwort und Pflichtprofilfeldern ermöglichen.

5. FR-REG-02
   - Herleitung: Bedürfnis 2 und 3 verlangen datenkonsistente Registrierung.
   - Anforderung: Das System muss Vertragsnummern auf Eindeutigkeit prüfen und bei Konflikten eine neutrale, verständliche Fehlermeldung anzeigen.

## Offene Punkte für Stakeholder
- Soll für den MVP bereits 2-Faktor-Authentifizierung vorgesehen werden?
- Welche Passwortregeln gelten verbindlich (Länge, Sonderzeichen, Rotation)?