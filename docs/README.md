# ComfoClime Documentation Index

Willkommen zur vollständigen technischen Dokumentation der ComfoClime Home Assistant Integration!

## 📚 Dokumentationsübersicht

Diese Dokumentation wurde automatisch generiert und bietet eine umfassende Übersicht über die Systemarchitektur, Klassen, Methoden und Abhängigkeiten.

### Hauptdokumente

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[ARCHITECTURE.md](../ARCHITECTURE.md)** | Vollständige Systemarchitektur-Dokumentation | Entwickler, Architekten |
| **[CLASS_METHOD_REFERENCE.md](CLASS_METHOD_REFERENCE.md)** | Detaillierte Klassen- und Methodenreferenz | Entwickler |
| **[DEPENDENCY_MATRIX.md](DEPENDENCY_MATRIX.md)** | Import- und Abhängigkeitsmatrix | Entwickler, Wartung |
| **[pydeps_graph.svg](pydeps_graph.svg)** | Visuelles Dependency-Diagramm | Alle |
| **[code_analysis.json](code_analysis.json)** | Rohdaten der Code-Analyse | Tools, Automatisierung |

## 🎯 Quick Links

### Für neue Entwickler

1. Start: [ARCHITECTURE.md - Executive Summary](../ARCHITECTURE.md#-executive-summary)
2. Architektur: [ARCHITECTURE.md - Architekturübersicht](../ARCHITECTURE.md#️-architekturübersicht)
3. Datenfluss: [ARCHITECTURE.md - Datenfluss](../ARCHITECTURE.md#datenfluss-von-der-initialisierung-bis-zur-api-kommunikation)
4. Module: [ARCHITECTURE.md - Module-Referenz](../ARCHITECTURE.md#-module-referenz)

### Für Code-Review

1. [CLASS_METHOD_REFERENCE.md](CLASS_METHOD_REFERENCE.md) - Alle Methoden und Signaturen
2. [DEPENDENCY_MATRIX.md](DEPENDENCY_MATRIX.md) - Modul-Abhängigkeiten
3. [ARCHITECTURE.md - Call Graph](../ARCHITECTURE.md#-call-graph--dependency-mapping)

### Für Maintenance & Refactoring

1. [ARCHITECTURE.md - Dead Code Analysis](../ARCHITECTURE.md#-dead-code-analysis)
2. [ARCHITECTURE.md - Verbesserungspotenziale](../ARCHITECTURE.md#-verbesserungspotenziale)
3. [ARCHITECTURE.md - Tooling](../ARCHITECTURE.md#️-tooling--automatisierung)

## 📊 Statistiken

**Codebase-Metriken (Stand 2026-02-05):**

- **Module:** 23
- **Klassen:** 48
- **Methoden:** 197
- **Funktionen:** 66
- **Koordinatoren:** 6
- **Entity-Typen:** 6

## 🏗️ Architektur-Schnellübersicht

```
Home Assistant
    ↓
__init__.py (Entry Point)
    ↓
┌─────────────┬──────────────┬──────────────┐
│             │              │              │
Coordinators  API Client     Entities
(6 types)     (aiohttp)      (6 types)
│             │              │
└─────────────┴──────────────┴──────────────┘
                    ↓
            ComfoClime Device
            (Local HTTP API)
```

### Entity-Typen

1. **Climate** - Haupt-Steuerung (HVAC, Temperatur, Szenario-Modi)
2. **Fan** - Lüftersteuerung
3. **Sensor** - Verschiedene Sensoren (Dashboard, Telemetrie, Property, etc.)
4. **Switch** - On/Off-Steuerung
5. **Number** - Numerische Einstellungen (Temperatur, Properties)
6. **Select** - Auswahl-Steuerung (Season, Properties)

### Koordinatoren

1. **Dashboard** - Real-time Dashboard-Daten
2. **Thermalprofile** - Thermal-Profile (Heizen/Kühlen)
3. **Monitoring** - System-Monitoring
4. **Telemetry** - Batch-Telemetrie (gerätespezifisch)
5. **Property** - Batch-Properties (gerätespezifisch)
6. **Definition** - Gerätedefinitionen

## 🔍 Verwendete Analyse-Tools

Diese Dokumentation wurde mit folgenden Tools erstellt:

1. **Vulture** - Dead Code Detection
   - Ergebnis: ✅ Keine ungenutzten Funktionen gefunden (Confidence > 80%)

2. **Pydeps** - Dependency Graph Visualization
   - Output: [pydeps_graph.svg](pydeps_graph.svg)

3. **Custom AST Analysis** - Python AST-basierte Code-Analyse
   - Output: [code_analysis.json](code_analysis.json)

## 📖 Weitere Dokumentation

### Im Repository

- [../README.md](../README.md) - Projekt-Übersicht, Installation
- [../ComfoClimeAPI.md](../ComfoClimeAPI.md) - API-Dokumentation
- [../SCENARIO_MODES.md](../SCENARIO_MODES.md) - Szenario-Modi
- [../PYDANTIC_MIGRATION.md](../PYDANTIC_MIGRATION.md) - Pydantic v2 Migration
- [../TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Fehlerbehebung

### External Links

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Home Assistant Integration Development](https://developers.home-assistant.io/docs/development_index)
- [Data Update Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data)

## 🔄 Dokumentation aktualisieren

Um diese Dokumentation zu aktualisieren, führe folgende Schritte aus:

```bash
# 1. Aktiviere Virtual Environment
source .venv/bin/activate

# 2. Installiere Analyse-Tools
pip install vulture pydeps graphviz

# 3. Führe Analysen aus
vulture custom_components/comfoclime --min-confidence 80
pydeps custom_components/comfoclime --max-bacon 2 -o docs/pydeps_graph.svg

# 4. Generiere Code-Analyse
python scripts/analyze_code.py  # (custom script)

# 5. Update Dokumentation
# Manuell ARCHITECTURE.md aktualisieren basierend auf neuen Erkenntnissen
```

## 🤝 Beitrag zur Dokumentation

Verbesserungsvorschläge für diese Dokumentation sind willkommen!

1. Fork das Repository
2. Erstelle einen Feature-Branch
3. Aktualisiere die Dokumentation
4. Erstelle einen Pull Request

## 📞 Kontakt & Support

- **GitHub Issues:** https://github.com/Revilo91/comfoclime/issues
- **GitHub Discussions:** https://github.com/Revilo91/comfoclime/discussions

---

**Letzte Aktualisierung:** 2026-02-05  
**Version:** 1.0  
**Maintainer:** Revilo91 / GitHub Copilot
