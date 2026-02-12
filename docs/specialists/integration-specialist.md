# Integrations-Spezialist

## Ziel
Stellt sicher, dass die Integration stabil mit Home Assistant und der lokalen API kommuniziert.

## Verantwortlichkeiten
- API-Kompatibilitaet und stabile Request/Response-Modelle
- Koordinatoren, Rate-Limits, Caching und Fehlerbehandlung
- Endpunkt-Abdeckung und Rueckwaertskompatibilitaet

## Fokusbereiche
- Pydantic-Modelle je Endpunkt (GET/PUT)
- Koordinator-Updatezyklen und Batch-Verhalten
- Entity-Abbildung und eindeutige IDs

## Deliverables
- Stabilitaetscheck fuer API-Aufrufe
- Verbesserungsvorschlaege fuer Datenfluss und Performance
- Dokumentationsnotizen fuer API/Koordinatoren

## Checkliste
- [ ] API-Endpunkte in `comfoclime_api.py` validiert
- [ ] Koordinatoren geben Pydantic-Modelle weiter
- [ ] Entities lesen Daten korrekt aus Modellen
- [ ] Tests fuer API/Koordinatoren aktualisiert
