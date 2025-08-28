# ComfoClime Climate Steuerung - Benutzeranleitung

## 🌡️ Temperatur einstellen

### Über Home Assistant UI:
1. Gehen Sie zu Ihrer Climate-Entität "ComfoClime Climate"
2. Klicken Sie auf die Temperatur
3. Stellen Sie die gewünschte Zieltemperatur ein

### Über Service-Call:
```yaml
service: climate.set_temperature
target:
  entity_id: climate.comfoclime_climate
data:
  temperature: 22.0
```

### Temperatur-Bereiche:
- **Heizmodus**: 15°C - 25°C
- **Kühlmodus**: 20°C - 28°C

## 🔥 HVAC Modus ändern

### Verfügbare Modi:

#### 1. Heizmodus aktivieren
```yaml
service: climate.set_hvac_mode
target:
  entity_id: climate.comfoclime_climate
data:
  hvac_mode: heat
```
**Effekt**: Setzt Season auf "heating" und aktiviert Lüfter

#### 2. Kühlmodus aktivieren
```yaml
service: climate.set_hvac_mode
target:
  entity_id: climate.comfoclime_climate
data:
  hvac_mode: cool
```
**Effekt**: Setzt Season auf "cooling" und aktiviert Lüfter

#### 3. Nur Lüftung
```yaml
service: climate.set_hvac_mode
target:
  entity_id: climate.comfoclime_climate
data:
  hvac_mode: fan_only
```
**Effekt**: Setzt Season auf "transition" und aktiviert Lüfter

#### 4. System ausschalten
```yaml
service: climate.set_hvac_mode
target:
  entity_id: climate.comfoclime_climate
data:
  hvac_mode: "off"
```
**Effekt**: Setzt Lüfter auf Standby (0)

## 🎛️ Preset Modi

### Verfügbare Presets:

#### Komfort-Modus
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.comfoclime_climate
data:
  preset_mode: comfort
```

#### Power-Modus
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.comfoclime_climate
data:
  preset_mode: power
```

#### Eco-Modus
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.comfoclime_climate
data:
  preset_mode: eco
```

## 🤖 Automatisierung Beispiele

### Heizmodus bei kaltem Wetter
```yaml
automation:
  - alias: "Winter Heating"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature
        below: 15
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.comfoclime_climate
        data:
          hvac_mode: heat
      - service: climate.set_temperature
        target:
          entity_id: climate.comfoclime_climate
        data:
          temperature: 20
```

### Eco-Modus nachts
```yaml
automation:
  - alias: "Night Eco Mode"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: climate.set_preset_mode
        target:
          entity_id: climate.comfoclime_climate
        data:
          preset_mode: eco
```

### Kühlmodus bei warmem Wetter
```yaml
automation:
  - alias: "Summer Cooling"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature
        above: 25
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.comfoclime_climate
        data:
          hvac_mode: cool
      - service: climate.set_temperature
        target:
          entity_id: climate.comfoclime_climate
        data:
          temperature: 24
```

## 📊 Status Überwachung

### Verfügbare Attribute:
- `current_temperature`: Aktuelle Innentemperatur
- `temperature`: Zieltemperatur
- `hvac_mode`: Aktueller HVAC-Modus
- `hvac_action`: Aktuelle Aktion (heating/cooling/fan/idle/off)
- `preset_mode`: Aktueller Preset-Modus

### Template-Sensoren:
```yaml
template:
  - sensor:
      - name: "ComfoClime Status"
        state: >
          {% if is_state('climate.comfoclime_climate', 'heat') %}
            Heizen auf {{ state_attr('climate.comfoclime_climate', 'temperature') }}°C
          {% elif is_state('climate.comfoclime_climate', 'cool') %}
            Kühlen auf {{ state_attr('climate.comfoclime_climate', 'temperature') }}°C
          {% elif is_state('climate.comfoclime_climate', 'fan_only') %}
            Nur Lüftung
          {% else %}
            Aus
          {% endif %}
```

## 🔧 Debugging

### Log-Level für Debugging setzen:
```yaml
logger:
  default: warning
  logs:
    custom_components.comfoclime.climate: debug
```

### Häufige Probleme:

1. **Modus ändert sich nicht**:
   - Prüfen Sie die Logs auf API-Fehler
   - Stellen Sie sicher, dass die ComfoClime-Einheit erreichbar ist

2. **Temperatur wird nicht gesetzt**:
   - Prüfen Sie, ob Sie sich im richtigen Season-Modus befinden
   - Temperatur muss im gültigen Bereich liegen

3. **Preset-Modus funktioniert nicht**:
   - Stellen Sie sicher, dass gültige Preset-Namen verwendet werden: comfort, power, eco

## 💡 Tipps

1. **Schrittweise Änderungen**: Ändern Sie erst den HVAC-Modus, dann die Temperatur
2. **Warten auf Updates**: Nach Änderungen kurz warten, bis sich der Status aktualisiert
3. **Season-abhängig**: Temperatureinstellungen sind abhängig vom aktuellen Season-Modus
4. **Logging**: Aktivieren Sie Debug-Logging für detaillierte Informationen

Die Climate-Entität bietet vollständige Kontrolle über Ihr ComfoClime-System direkt aus Home Assistant heraus!
