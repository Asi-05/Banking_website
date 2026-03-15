
# Anforderungen an die E-Banking-Budget-Tracker-Anwendung

## 1. Einleitung und Zweck

Die E-Banking-Budget-Tracker-Anwendung ist eine lokale Web-App zur Verwaltung privater Finanzen. Sie bietet eine zentrale Plattform für das Erfassen, Analysieren und Planen von Einnahmen, Ausgaben, Budgets und Bankgeschäften. Ziel ist es, Nutzern eine übersichtliche, sichere und effiziente Lösung für den Alltag zu bieten – ohne Anbindung an echte Bankensysteme.


## 2. Funktionale Anforderungen

### 2.1 Finanzverwaltung
- Einnahmen und Ausgaben manuell erfassen (US1)
- Transaktionen kategorisieren (US2)
- Einträge bearbeiten und löschen (US3)
- Filter nach Datum und Kategorie (US4)

### 2.2 Dashboard & Analyse
- Dashboard mit Diagrammen (US5)
- Aktuelle Gesamtbilanz anzeigen (US6)
- Summen für Zeiträume abrufen (US7)
- (Optional) Aktienticker auf Startseite (US8)

### 2.3 Budgetierung & Planung
- Monatliche Limits setzen, automatische Warnung bei Überschreitung (US9)
- Wiederkehrende Zahlungen für Kategorien (US10)

### 2.4 Konten- & Kartenmanagement
- Privat- und Sparkonten eröffnen/schließen (US11)
- Karten bestellen, sperren, ersetzen (US12)
- 3a-Konto eröffnen, Beratungstermin vereinbaren (US13)

### 2.5 Zahlungsverkehr & Dokumente
- Inlandzahlungen per IBAN oder PDF-Upload (US14)
- Umbuchung zwischen eigenen Konten (US15)
- Kontoauszüge für Zeiträume generieren/einsehen (US16)

### 2.6 Sicherheit & Onboarding
- Anmeldung mit Vertragsnummer & Passwort (US17)
- Neues Benutzerkonto registrieren (US18)

### 2.7 Technische Vorgaben
- Die Anwendung wird mit Python, NiceGUI (UI), SQLite, SQLModel oder SQLAlchemy (ORM) und Pydantic (Validierung) umgesetzt.
- Alle Daten werden lokal in einer SQLite-Datenbank gespeichert.
- Keine Anbindung an echte Bankensysteme, alle Bankfunktionen sind simuliert.


## 3. Nicht-funktionale Anforderungen

| Kategorie        | Anforderung                                                                 |
|------------------|------------------------------------------------------------------------------|
| Sicherheit       | Lokale Speicherung, Passwort-Hashing, keine externen Bankverbindungen         |
| Performance      | Ladezeiten < 2 Sekunden für Hauptfunktionen                                  |
| Usability        | Intuitive, barrierefreie UI, Responsive Design für Desktop & Mobile           |
| Zuverlässigkeit  | 99,5% Verfügbarkeit, automatische Backups                                     |
| Wartbarkeit      | Modularer Aufbau, dokumentierter Quellcode, automatisierte Tests              |
| Kompatibilität   | Aktuelle Browser (Chrome, Firefox, Safari, Edge)                             |

## 4. Glossar
- **3a-Konto**: Schweizer Vorsorgekonto für die private Altersvorsorge
- **IBAN**: International Bank Account Number

---

Diese Spezifikation basiert direkt auf den User Stories und dient als Grundlage für Architektur, Entwicklung und Test der Anwendung.