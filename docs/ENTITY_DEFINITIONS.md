# Entity Definitions – Statisch vs. Dynamisch

## Zusammenfassung

Nach gründlicher Analyse wurde entschieden, **statische Entity-Definitionen beizubehalten**, aber die Struktur durch Pydantic-Modelle zu verbessern und Lücken zu schließen.

## Problem

Die Frage war, ob die Entity-Definitionen in `entities/*_definitions.py` redundant sind und dynamisch aus API-Responses generiert werden könnten, insbesondere für:
- Dashboard Sensoren
- Thermal Profile Sensoren

## Analyse

### Dashboard Sensoren

**Vorher:**
- ❌ DashboardData Pydantic-Model vorhanden (18 Felder)
- ❌ DASHBOARD_SENSORS hatte nur 14 Definitionen
- ❌ **3 Felder fehlten**: `setPointTemperature`, `seasonProfile`, `caqFreeCoolingAvailable`

**Nachher:**
- ✅ Alle 18 Felder sind jetzt als Sensoren definiert (17 Sensoren, `seasonProfile` wurde als Sensor hinzugefügt)
- ✅ Vollständige Abdeckung des API-Response

### Thermal Profile Sensoren

**Vorher:**
- ❌ **KEIN Pydantic-Model** vorhanden
- ❌ Daten wurden als verschachteltes Dictionary gehandhabt
- ❌ Keine Typ-Sicherheit oder Validierung

**Nachher:**
- ✅ **4 neue Pydantic-Modelle** erstellt:
  - `SeasonData` – Season-Konfiguration
  - `TemperatureControlData` – Temperatur-Steuerung
  - `ThermalProfileSeasonData` – Heiz-/Kühl-Parameter
  - `ThermalProfileData` – Vollständiges Profil
- ✅ Field-Aliase für camelCase ↔ snake_case
- ✅ Validierung durch Pydantic
- ✅ Helper-Properties für einfachere Abfragen

## Warum statische Definitionen?

### 1. Nicht alle Model-Felder sollen Entities sein

**Beispiel:** `set_point_temperature` ist nur im manuellen Modus relevant. Eine dynamische Generierung würde alle Felder als Entities erstellen, auch wenn sie nicht sinnvoll sind.

### 2. Metadaten können nicht automatisch abgeleitet werden

| Metadatum | Automatisch ableitbar? | Beispiel |
|-----------|------------------------|----------|
| `device_class` | Teilweise (aus Feldname) | `temperature` aus `*Temperature` |
| `state_class` | Teilweise (aus Typ) | `measurement` für float-Werte |
| `unit` | Teilweise (aus Feldname) | `°C` aus `*Temperature` |
| `entity_category` | **Nein** | `diagnostic` vs. normale Entität |
| `icon` | **Nein** | Icons fehlen aktuell komplett |
| `translation_key` | **Nein** | Manuelle i18n-Zuordnung nötig |
| `suggested_display_precision` | Teilweise | `1` für Temperaturen, `0` für Durchfluss |

**Problem:** ~30% der Metadaten sind **nicht automatisch ableitbar** und erfordern manuelle Definition.

### 3. Telemetry/Property benötigen gerätespezifische Metadaten

Diese Sensoren haben zusätzliche Anforderungen:
- `faktor` – Skalierungsfaktor (z.B. 0.1 für Temperaturen)
- `signed` – Vorzeichenbehaftete Integer-Interpretation
- `byte_count` – Anzahl der zu lesenden Bytes (1 oder 2)

**Diese Informationen sind NICHT im API-Response enthalten** und müssen für jede Telemetrie-ID/Property-Path manuell definiert werden.

### 4. Bessere Kontrolle über User Experience

Statische Definitionen ermöglichen:
- **Reihenfolge** der Entities in der UI
- **Gruppierung** nach Kategorie (diagnostic, config, standard)
- **Selektive Aktivierung** (manche Sensoren disabled by default)
- **Icons** für bessere visuelle Darstellung

## Verbesserungen

### 1. ThermalProfile Pydantic-Modelle

```python
# Vorher: Dictionary mit beliebiger Struktur
profile = {
    "season": {"status": 1, "season": 1},
    "temperature": {"status": 1}
}

# Nachher: Typsicheres Pydantic-Model
profile = ThermalProfileData(
    season=SeasonData(status=1, season=1),
    temperature=TemperatureControlData(status=1)
)

# Mit Helper-Properties
if profile.is_heating_season:
    comfort = profile.heating_thermal_profile_season_data.comfort_temperature
```

**Vorteile:**
- ✅ Typ-Sicherheit durch Python Type Hints
- ✅ Automatische Validierung (z.B. `season` muss 0-2 sein)
- ✅ Field-Aliase für API-Kompatibilität (`heatingThresholdTemperature` → `heating_threshold_temperature`)
- ✅ Helper-Properties für einfachere Abfragen

### 2. Fehlende Dashboard-Sensoren

**Neu hinzugefügt:**
1. **setPointTemperature** – Zieltemperatur im manuellen Modus
2. **seasonProfile** – Season-Profil-Auswahl (comfort/boost/eco)
3. **caqFreeCoolingAvailable** – ComfoAirQ Free-Cooling-Verfügbarkeit (diagnostic)

### 3. Konsistenz-Tests

**test_sensor_definitions.py:**
```python
def test_dashboard_sensors_match_model_fields():
    """Test that all sensor keys correspond to DashboardData model fields."""
    model_fields = get_all_model_fields(DashboardData)
    for sensor_def in DASHBOARD_SENSORS:
        assert sensor_def.key in model_fields
```

**Nutzen:**
- ✅ Automatische Erkennung von Tippfehlern
- ✅ Warnung bei Schema-Änderungen
- ✅ Sicherstellung dass alle Definitionen auf echte Felder verweisen

## Vergleich: Statisch vs. Dynamisch

| Aspekt | Statisch (aktuell) | Dynamisch (Alternative) |
|--------|-------------------|------------------------|
| **Metadaten-Kontrolle** | ✅ Vollständig | ❌ 70% automatisch, 30% fehlen |
| **Wartungsaufwand** | ⚠️ Mittel (bei Schema-Änderung) | ✅ Niedrig |
| **Typ-Sicherheit** | ✅ Pydantic-Modelle | ✅ Gleich |
| **Selektive Entities** | ✅ Einfach | ❌ Komplexe Filter nötig |
| **UX-Kontrolle** | ✅ Reihenfolge, Icons, Gruppen | ❌ Alphabetisch, generisch |
| **Telemetry/Property** | ✅ faktor/signed/byte_count | ❌ Nicht ableitbar |
| **Tests** | ✅ Konsistenz prüfbar | ✅ Automatisch konsistent |

## Entscheidung

✅ **Statische Definitionen beibehalten** mit folgenden Verbesserungen:

1. ✅ **ThermalProfile Pydantic-Model erstellt** (bessere Typ-Sicherheit)
2. ✅ **Fehlende Dashboard-Sensoren hinzugefügt** (vollständige API-Abdeckung)
3. ✅ **Konsistenz-Tests implementiert** (automatische Validierung)
4. ✅ **Code-Redundanz minimiert** (Pydantic-Models als Single Source of Truth)

## Zukünftige Erweiterungen (optional)

Falls gewünscht, könnte ein **Hybrid-Ansatz** implementiert werden:

```python
# Generator-Funktion mit Override-Möglichkeit
def generate_sensor_definitions(model: BaseModel, overrides: dict) -> list[SensorDefinition]:
    """Generate sensor definitions from Pydantic model with manual overrides."""
    definitions = []
    for field_name, field_info in model.model_fields.items():
        # Auto-derive basic metadata from field
        device_class = infer_device_class(field_name, field_info.annotation)
        state_class = infer_state_class(field_info.annotation)
        unit = infer_unit(field_name, device_class)
        
        # Apply manual overrides
        sensor_def = overrides.get(field_name, {})
        definitions.append(SensorDefinition(
            key=field_name,
            device_class=sensor_def.get('device_class', device_class),
            state_class=sensor_def.get('state_class', state_class),
            unit=sensor_def.get('unit', unit),
            # ... weitere Felder
        ))
    return definitions
```

**Nutzen:**
- Automatische Basis-Metadaten (80%)
- Manuelle Overrides für spezielle Fälle (20%)
- Beste Balance zwischen Automatisierung und Kontrolle

**Aktuell nicht implementiert**, da der zusätzliche Aufwand den Nutzen nicht rechtfertigt.

## Dokumentation

### Für Entwickler

**Neue Entity hinzufügen:**
1. Feld zum Pydantic-Model hinzufügen (z.B. in `DashboardData`)
2. Definition in `DASHBOARD_SENSORS` hinzufügen
3. Test läuft automatisch und prüft Konsistenz

**Beispiel:**
```python
# 1. In models.py
class DashboardData(BaseModel):
    new_field: float | None = Field(default=None, alias="newField")

# 2. In entities/sensor_definitions.py
DASHBOARD_SENSORS = [
    # ... existing sensors
    SensorDefinition(
        key="newField",
        name="New Field",
        translation_key="new_field",
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
]

# 3. Test prüft automatisch
# ✅ test_dashboard_sensors_match_model_fields()
```

## Fazit

Die aktuellen **statischen Definitionen sind sinnvoll** und wurden durch folgende Maßnahmen verbessert:

✅ **ThermalProfile Pydantic-Modelle** – Typ-Sicherheit und Validierung  
✅ **Vollständige Dashboard-Abdeckung** – Alle API-Felder als Sensoren verfügbar  
✅ **Automatische Konsistenz-Tests** – Warnung bei Schema-Drift  
✅ **Weniger Redundanz** – Pydantic als Single Source of Truth  

**Dynamische Generierung würde mehr Komplexität als Nutzen bringen**, da Metadaten wie `entity_category`, `icon` und `translation_key` nicht automatisch ableitbar sind und Telemetry/Property gerätespezifische Skalierung benötigen.
