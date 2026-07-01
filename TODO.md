# TODO – Verbesserungen comfoclime

Sammlung offener Verbesserungspunkte aus einer Codebase-Analyse (Stand: 2026-07-01).
Noch nicht umgesetzt – als Backlog gedacht.

## 🔴 Priorität Hoch

- [ ] **Toten Code entfernen**: `custom_components/comfoclime/entities/base.py` löschen.
      Dupliziert `EntityDefinitionBase` aus `base_definitions.py`, wird nirgends importiert
      (auch in CLAUDE.md als bekannter Fallstrick vermerkt).
- [ ] **Testlücke schließen**: `tests/test_entity_base.py` erstellen für
      `custom_components/comfoclime/entity_base.py` (gemeinsames Mixin für alle Entity-Klassen,
      aktuell ungetestet, betrifft aber transitiv alle Plattformen: climate, fan, sensor, switch,
      number, select).
- [ ] **README-Badge korrigieren**: Badge verweist auf einen nicht mehr existierenden
      Workflow-Dateinamen (`tests.yml` statt `ci.yml`) – auf tatsächlichen CI-Workflow anpassen.

## 🟡 Priorität Mittel

- [ ] **Coordinator-Duplizierung reduzieren**: `ComfoClimeDashboardCoordinator`,
      `ComfoClimeMonitoringCoordinator` und `ComfoClimeThermalprofileCoordinator` in
      `custom_components/comfoclime/coordinator.py` sind fast identisch (nur der API-Call
      unterscheidet sich). Auf parametrisierte Factory/gemeinsame Basisklasse reduzieren.
- [ ] **mypy-Prüfung ergänzen**: Type Hints sind überall vorhanden, werden aber nie statisch
      validiert. `[tool.mypy]`-Block in `pyproject.toml` ergänzen + CI-Step hinzufügen
      (z. B. `uv run mypy custom_components/comfoclime`).
- [ ] **Debounce-Dictionary aufräumen**: In `custom_components/comfoclime/infrastructure/api.py`
      werden abgebrochene/abgeschlossene Einträge in der Pending-Requests-Struktur nicht
      konsequent entfernt – potenzielles langsames Memory-Wachstum im Dauerbetrieb.

## 🟢 Priorität Niedrig

- [ ] **README um Screenshots ergänzen**: Aktuell nur Tabellen, keine visuelle Vorschau der
      Climate-/Sensor-Entities.
- [ ] **Property- vs. Telemetry-Coordinator**: Ähnliche Registrierungs-/Batching-Logik –
      ggf. gemeinsame Basis extrahieren, aber Vorsicht vor Über-Abstraktion (beide haben auch
      eigenständige Komplexität).
