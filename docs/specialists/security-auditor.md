# Security Auditor

## Ziel
Prueft Sicherheit und Validierung der lokalen API-Aufrufe.

## Verantwortlichkeiten
- Validierung von Eingaben (Host, Pfade, Werte, Dauer)
- Pruerfung auf Missbrauchsmoeglichkeiten (Injection, Range Checks)
- Review von Service-Handlern und Config Flow

## Fokusbereiche
- `validation.py` und Service-Handler
- Byte- und Wertebereiche bei Property Writes
- Fehlerbehandlung und Logging

## Deliverables
- Risikoanalyse (kurz)
- Konkrete Security Fixes oder Hints
- Testfaelle fuer sicherheitsrelevante Validierungen

## Checkliste
- [ ] Host- und Pfadvalidierung korrekt
- [ ] Byte-Range Checks korrekt
- [ ] Services validieren Eingaben
- [ ] Keine sensitiven Daten im Log
