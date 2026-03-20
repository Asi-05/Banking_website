# Requirements-Dokument: Sicherheit & Onboarding

## Quelle User Stories
- US12: Login mit Vertragsnummer und Passwort
- US13: Registrierung (Onboarding)

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
- Edge Cases: Doppelte E-Mail-Adresse, schwaches Passwort, unvollständige Eingaben.
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
   - Anforderung: Das System muss nach wiederholten Fehlversuchen eine Schutzmaßnahme auslösen (z. B. temporäre Sperre).

4. FR-AUTH-04
   - Herleitung: Bedürfnis 1 und 3 verlangen klar definierte Passwortregeln.
   - Anforderung: Das System muss Passwörter mit mindestens 8 Zeichen und mindestens einem Sonderzeichen verlangen; eine Passwort-Rotationspflicht besteht nicht.

5. FR-REG-01
   - Herleitung: Bedürfnis 2 verlangt einen vollständigen Self-Service-Registrierungsprozess.
   - Anforderung: Das System muss die Erstellung eines neuen Benutzerkontos mit Vorname, Nachname, E-Mail und Passwort ermöglichen und dabei eine neue Vertragsnummer erzeugen.

6. FR-REG-02
   - Herleitung: Bedürfnis 2 und 3 verlangen datenkonsistente Registrierung.
   - Anforderung: Das System muss E-Mail-Adressen auf Eindeutigkeit prüfen und bei Konflikten eine neutrale, verständliche Fehlermeldung anzeigen.

7. FR-REG-03
   - Herleitung: Bedürfnis 2 verlangt eine persistente und eindeutig identifizierbare Benutzerverwaltung.
   - Anforderung: Das System muss alle registrierten Benutzer in einer zentralen Benutzerliste (Datenbanktabelle) speichern, wobei jeder Benutzer eine eindeutige User-ID und die zugehörigen Profildaten besitzt.

## Entscheidungen der Stakeholder
- Für den MVP ist keine 2-Faktor-Authentifizierung vorgesehen.
- Passwortregeln: mindestens 8 Zeichen, mindestens ein Sonderzeichen, keine Rotationspflicht.

