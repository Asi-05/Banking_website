# Requirements-Dokument: Zahlungsverkehr & Dokumente

## Quelle User Stories
- US10: Inlandzahlungen per IBAN-Eingabe erfassen
- US11: Geld zwischen eigenen Konten umbuchen
- US12: Kontoauszüge für Zeiträume generieren und einsehen

## Erhebung
- Bedürfnis 1: Nutzer brauchen einen einfachen Prozess für Inlandszahlungen.
- Bedürfnis 2: Nutzer brauchen schnelle Umbuchungen zwischen eigenen Konten.
- Bedürfnis 3: Nutzer brauchen exportierbare und einsehbare Kontoauszüge für definierte Zeiträume.

## Analyse
### Bedürfnis 1: Inlandszahlungen
- Begründung: Zahlungsverkehr ist eine Kernfunktion im Bankalltag.
- Edge Cases: Ungültige IBAN, fehlender Betrag, ungültige Empfängerangaben.
- Abhängigkeiten: Validierungslogik für Zahlungsdaten.

### Bedürfnis 2: Umbuchungen
- Begründung: Interne Transfers müssen schnell und nachvollziehbar erfolgen.
- Edge Cases: Unzureichendes Guthaben, gleiche Quelle und Zielkonto.
- Abhängigkeiten: Transaktionslogik mit atomarer Buchung auf zwei Konten.

### Bedürfnis 3: Kontoauszüge
- Begründung: Nutzer benötigen Nachweise für Kontrolle und externe Zwecke.
- Edge Cases: Leere Zeiträume, sehr große Ergebnislisten.
- Abhängigkeiten: Reporting-Abfragen, PDF-Dateigenerierung.

## Dokumentierte Anforderungen
1. FR-PAY-01
   - Herleitung: Bedürfnis 1 verlangt einen klaren, manuellen Erfassungsweg.
   - Anforderung: Das System muss Inlandzahlungen über manuelle IBAN-Eingabe erfassen können.

2. FR-PAY-02
   - Herleitung: Bedürfnis 1 verlangt Eingabesicherheit.
   - Anforderung: Das System muss target_iban, amount, source_account_id und purpose vor dem Auslösen einer Zahlung validieren und prüfen, ob ausreichend Guthaben auf dem Belastungskonto vorhanden ist.

3. FR-TRF-01
   - Herleitung: Bedürfnis 2 verlangt konsistente Doppelbuchung.
   - Anforderung: Das System muss Umbuchungen zwischen eigenen Konten als zusammenhängende Soll-/Haben-Transaktion speichern.

4. FR-TRF-02
   - Herleitung: Bedürfnis 2 verlangt Schutz vor fachlich ungültigen Transfers.
   - Anforderung: Das System muss Umbuchungen mit unzureichendem Guthaben oder identischem Quell-/Zielkonto verhindern.

5. FR-STM-01
   - Herleitung: Bedürfnis 3 verlangt zeitbasierte Dokumenterstellung.
   - Anforderung: Das System muss Kontoauszüge für frei wählbare Zeiträume als PDF generieren und in der Anwendung anzeigen können.

## Entscheidungen der Stakeholder
- Für Kontoauszüge wird genau ein einheitliches PDF-Layout verwendet.
- Für Inlandzahlungen sind keine zusätzlichen Pflichtfelder neben dem Verwendungszweck erforderlich.

## Offene Punkte für Stakeholder
- Keine.