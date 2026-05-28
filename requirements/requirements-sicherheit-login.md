# Requirements-Dokument: Sicherheit & Login

## Quelle User Stories
- US13: Login mit Vertragsnummer und Passwort

## Erhebung
- Bedürfnis 1: Nutzer brauchen einen verlässlichen Login mit Vertragsnummer und Passwort.
- Bedürfnis 2: Nutzer brauchen Schutz ihrer Zugangsdaten und nachvollziehbare Fehlermeldungen.
- Bedürfnis 3: Das System soll mit vordefinierten Usern arbeiten und keine Selbstregistrierung anbieten.

## Analyse
### Bedürfnis 1: Login
- Begründung: Ohne sichere Authentifizierung sind alle weiteren Funktionen nicht vertrauenswürdig.
- Edge Cases: Falsche Zugangsdaten.
- Abhängigkeiten: Benutzerverwaltung, Passwort-Hashing.

### Bedürfnis 2: Sicherheitsfeedback
- Begründung: Fehlermeldungen sollen helfen, dürfen aber keine sensiblen Informationen preisgeben.
- Edge Cases: Unterschiedliche Meldungen für unbekannte Nutzer vs. falsches Passwort.
- Abhängigkeiten: Security-Richtlinien für Fehlermeldungen.

### Bedürfnis 3: Vordefinierte User
- Begründung: Der Projektumfang sieht keinen Registrierungsprozess vor.
- Edge Cases: Login mit nicht existierender Vertragsnummer, deaktivierter vordefinierter User.
- Abhängigkeiten: Benutzerverwaltung mit vorab angelegten Accounts.

## Dokumentierte Anforderungen
1. FR-AUTH-01
   - Herleitung: Bedürfnis 1 verlangt standardisierte Zugangsdaten.
   - Anforderung: Das System muss eine Anmeldung mit Vertragsnummer und Passwort bereitstellen.

2. FR-AUTH-02
   - Herleitung: Bedürfnis 1 und 2 verlangen sicheren Umgang mit Credentials.
   - Anforderung: Das System muss Passwörter gehasht speichern und darf niemals Klartext-Passwörter persistieren oder anzeigen.

3. FR-AUTH-04
   - Herleitung: Bedürfnis 1 und 2 verlangen klar definierte Passwortregeln.
   - Anforderung: Das System muss Passwörter mit mindestens 8 Zeichen und mindestens einem Sonderzeichen verlangen; eine Passwort-Rotationspflicht besteht nicht.

4. FR-AUTH-05
   - Herleitung: Bedürfnis 3 verlangt einen klaren Ausschluss der Selbstregistrierung.
   - Anforderung: Das System darf keine Selbstregistrierung anbieten und muss Login ausschließlich für vordefinierte Benutzerkonten erlauben.

5. FR-AUTH-06
   - Herleitung: Bedürfnis 3 verlangt persistente Verwaltung der vordefinierten User.
   - Anforderung: Das System muss vordefinierte Benutzer in einer zentralen Benutzerliste (Datenbanktabelle) mit eindeutiger User-ID, Vertragsnummer und Profildaten speichern.

## Entscheidungen der Stakeholder
- Für den MVP ist keine 2-Faktor-Authentifizierung vorgesehen.
- Passwortregeln: mindestens 8 Zeichen, mindestens ein Sonderzeichen, keine Rotationspflicht.

