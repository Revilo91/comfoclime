# ComfoClime: API-Übersicht (alle Schnittstellen)

Written for: Entwickler:innen, die die lokale API oder die Integration nutzen.

Stand: Repo `Revilo91/comfoclime`, Integrationsversion `2.0.2b17`. Quellen: `comfoclime_api.py`, `models.py`, `services.yaml`, `services.py`, `entities/sensor_definitions.py`.

## Grundlagen

- **Basis-URL:** `http://<IP>`. Nur lokal, unauthentifiziert, Klartext-HTTP, JSON.
- **UUID vs. Device-ID:** Pfade mit `{uuid}` brauchen die **System-UUID** aus `GET /monitoring/ping`, z. B. `MBE083a8d0146e1`. `{device_uuid}` ist die UUID eines Geräts am ComfoNet-Bus.
- **Gerätetypen (`modelTypeId`):** `1` ComfoAir Q, `20` ComfoClime, `222` ComfoHub.
- **Rate-Limiting (Client):** Mindestabstand 0.5 s, Schreib-Cooldown 2.0 s, Debounce 0.3 s, Cache 30 s für Telemetrie und Properties. Timeouts: Lesen 10 s, Schreiben 30 s, bis zu 3 Wiederholungen.
- ⚠️ `CLAUDE.md` nennt 0.1 s für den Mindestabstand. Der Code hat 0.5 s.

## A. HTTP-Endpoints des Geräts

| # | Methode | Pfad | Client-Methode | Antwort / Modell | Verwendet von |
|---|---|---|---|---|---|
| 1 | GET | `/monitoring/ping` | `async_get_monitoring_ping()`, `async_get_uuid()` | `MonitoringPing` (uuid, uptime) | `coordinator.py` |
| 2 | GET | `/system/{uuid}/dashboard` | `async_get_dashboard_data()` | `DashboardData` | `coordinator.py` |
| 3 | PUT | `/system/{uuid}/dashboard` | `async_update_dashboard(DashboardUpdate)` | `DashboardUpdateResponse` | `climate.py` |
| 4 | GET | `/system/{uuid}/thermalprofile` | `async_get_thermal_profile()` | `ThermalProfileData` | `coordinator.py` |
| 5 | PUT | `/system/{uuid}/thermalprofile` | `async_update_thermal_profile(...)` | `ThermalProfileUpdateResponse` | `number.py`, `select.py`, `switch.py` |
| 6 | GET | `/system/{uuid}/devices` | `async_get_connected_devices()` | `ConnectedDevicesResponse` | `__init__.py` |
| 7 | GET | `/device/{device_uuid}/definition` | `async_get_device_definition(device_uuid)` | `DeviceDefinitionData` | `coordinator.py` |
| 8 | GET | `/device/{device_uuid}/telemetry/{id}` | `async_read_telemetry_for_device(...)` | `TelemetryReading` | `coordinator.py` |
| 9 | GET | `/device/{device_uuid}/property/{X/Y/Z}` | `async_read_property_for_device(...)` | `PropertyReading` | `coordinator.py` |
| 10 | PUT | `/device/{device_uuid}/method/{X}/{Y}/3` | `async_set_property_for_device(...)` | `PropertyWriteResponse` | `number.py`, `select.py`, `services.py` |
| 11 | PUT | `/system/reset` | `async_reset_system()` | `dict` | `services.py` |

Nicht öffentlich, aber intern genutzt: `_async_get_uuid_internal` (GET `/monitoring/ping`, ohne Lock).

## B. Payloads der PUT-Endpoints

### 3. Dashboard (`DashboardUpdate`)

Nur Felder ungleich `null` werden gesendet.

| Python | JSON | Wertebereich |
|---|---|---|
| `set_point_temperature` | `setPointTemperature` | °C |
| `fan_speed` | `fanSpeed` | 0–3 |
| `season` | `season` | 0 Übergang, 1 Heizen, 2 Kühlen |
| `hp_standby` | `hpStandby` | bool |
| `schedule` | `schedule` | int |
| `temperature_profile` | `temperatureProfile` | 0–2 |
| `season_profile` | `seasonProfile` | 0–2 |
| `status` | `status` | 0 manuell, 1 automatisch |
| `scenario` | `scenario` | 4 Kochen, 5 Party, 7 Urlaub, 8 Boost |
| `scenario_time_left` | `scenarioTimeLeft` | Sekunden |
| `scenario_start_delay` | `scenarioStartDelay` | int |

### 5. Thermalprofil (`ThermalProfileUpdate`)

Aufrufen lässt sich `async_update_thermal_profile` auf drei Arten: mit Kwargs, mit einem `ThermalProfileUpdate`-Modell oder mit einem verschachtelten Dict (Legacy).

| Kwarg | JSON-Gruppe | Bedeutung |
|---|---|---|
| `season_status` | `season.status` | 0 manuell, 1 automatisch |
| `season_value` | `season.season` | 0 Übergang, 1 Heizen, 2 Kühlen |
| `heating_threshold_temperature` | `season.heatingThresholdTemperature` | °C |
| `cooling_threshold_temperature` | `season.coolingThresholdTemperature` | °C |
| `temperature_status` | `temperature.status` | 0 manuell, 1 automatisch |
| `manual_temperature` | `temperature.manualTemperature` | °C |
| `temperature_profile` | `temperatureProfile` | 0 Komfort, 1 Boost (oder „Power“, siehe Abschnitt F), 2 Eco |
| `heating_comfort_temperature` | `heatingThermalProfileSeasonData.comfortTemperature` | °C |
| `heating_knee_point_temperature` | `heatingThermalProfileSeasonData.kneePointTemperature` | °C |
| `heating_reduction_delta_temperature` | `heatingThermalProfileSeasonData.reductionDeltaTemperature` | °C |
| `cooling_comfort_temperature` | `coolingThermalProfileSeasonData.comfortTemperature` | °C |
| `cooling_knee_point_temperature` | `coolingThermalProfileSeasonData.kneePointTemperature` | °C |
| `cooling_temperature_limit` | `coolingThermalProfileSeasonData.temperatureLimit` | °C |

Das GET-Ergebnis `ThermalProfileData` hat dieselben Gruppen: `season`, `temperature`, `temperatureProfile`, `heatingThermalProfileSeasonData`, `coolingThermalProfileSeasonData`.

**Zusammengesetzter Aufruf** `async_set_hvac_season(season, hpStandby)`:
1. Dashboard-PUT mit `hp_standby`.
2. Nur wenn `hpStandby=False`: Thermalprofil-PUT mit `season_value`.

### 10. Property schreiben

Eingabe: `device_uuid`, `property_path` (`X/Y/Z`), `value`, `byte_count` (1 oder 2), `signed`, `faktor`.

Ablauf:
1. `raw = round(value / faktor)`, z. B. `22.5 / 0.1 = 225`.
2. Wertebereich gegen `byte_count` und `signed` prüfen.
3. Bytes little-endian.
4. URL `/device/{uuid}/method/{X}/{Y}/3`, Body `{"data": [Z, *bytes]}`.

Nach dem Schreiben wird der Cache des ganzen Geräts geleert.

### 11. Reset

PUT `/system/reset` ohne Body. Das Gerät startet neu und ist kurz nicht erreichbar.

## C. Dashboard-Antwort (GET, Endpoint 2)

Alle Felder sind optional. Sie variieren zwischen AUTO und MANUAL.

| JSON | Python | Bedeutung |
|---|---|---|
| `indoorTemperature` | `indoor_temperature` | Innen, °C |
| `outdoorTemperature` | `outdoor_temperature` | Außen, °C |
| `setPointTemperature` | `set_point_temperature` | Sollwert, °C (nur MANUAL) |
| `exhaustAirFlow` | `exhaust_air_flow` | Abluft, m³/h |
| `supplyAirFlow` | `supply_air_flow` | Zuluft, m³/h |
| `fanSpeed` | `fan_speed` | Lüfterstufe 0–3 |
| `season` | `season` | 0 Übergang, 1 Heizen, 2 Kühlen |
| `seasonProfile` | `season_profile` | 0 Komfort, 1 Boost, 2 Eco |
| `temperatureProfile` | `temperature_profile` | 0 Komfort, 1 Boost, 2 Eco |
| `status` | `status` | 0 manuell, 1 automatisch |
| `schedule` | `schedule` | Zeitplan-Status |
| `heatPumpStatus` | `heat_pump_status` | Bit 0x02 Heizen, 0x04 Kühlen |
| `hpStandby` | `hp_standby` | true = Standby |
| `freeCoolingEnabled` | `free_cooling_enabled` | Free Cooling aktiv |
| `caqFreeCoolingAvailable` | `caq_free_cooling_available` | Free Cooling verfügbar |
| `scenario` | `scenario` | 4, 5, 7, 8, fehlt ohne Szenario |
| `scenarioTimeLeft` | `scenario_time_left` | Restzeit in Sekunden |

### Live-Beispiel (Gerät `10.0.2.27`, 2026-11-02 12:46)

```
GET http://10.0.2.27/monitoring/ping
→ {"uuid":"MBE083a8d0146e1","up_time_seconds":817,...}

GET http://10.0.2.27/system/MBE083a8d0146e1/dashboard
→ {"indoorTemperature":21.8,"outdoorTemperature":8.9,"exhaustAirFlow":169,
   "supplyAirFlow":170,"fanSpeed":2,"setPointTemperature":23.0,"season":1,
   "schedule":0,"status":0,"heatPumpStatus":3,"hpStandby":false,
   "freeCoolingEnabled":false,"caqFreeCoolingAvailable":false}
```

Lesart: Heizen, manuell, Sollwert 23 °C, Lüfterstufe 2, Wärmepumpe aktiv.

## D. Telemetrie und Properties (Endpoints 8 und 9)

### Telemetrie-IDs (`GET /device/{uuid}/telemetry/{id}`)

**ComfoClime (`modelTypeId=20`):** 4145 TPMA-Temperatur, 4149 Betriebsmodus, 4151 Komforttemperatur, 4154 Innentemperatur, 4193 Zulufttemperatur, 4194 Fortlufttemperatur, 4195/4196 Zu-/Abluft-Gastemperatur, 4197 Kompressortemperatur, 4198 Leistungsfaktor, 4201 Leistung (W), 4202 Hochdruck, 4203 Expansionsventil, 4204 und 4208 Diagnose, 4205 Niederdruck, 4206 WP-Status, 4207 4-Wege-Ventil.

**ComfoAir (`modelTypeId=1`):** 117 Abluft-Lüfter-Ansteuerung (%), 118 Zuluft-Lüfter-Ansteuerung (%), 121 Abluft-Drehzahl (rpm), 122 Zuluft-Drehzahl (rpm), 128 Leistung (W), 129 Energie Jahr (kWh), 130 Energie gesamt (kWh), 192 Filter-Restlaufzeit (Tage), 209 RMOT (°C), 227 Bypass, 275 Ablufttemperatur (°C), 278 Zulufttemperatur (°C), 290 Feuchte Abluft, 291 Feuchte Fortluft, 292 Feuchte Außenluft, 294 Feuchte Zuluft.

Die Byte-Anzahl und der Faktor stehen in `sensor_definitions.py`. Bei ComfoAir-Einträgen ohne `byte_count` vorher prüfen.

### Property-Pfade (`GET/PUT /device/{uuid}/property/{X/Y/Z}`)

| Pfad | Gerät | Bytes | Faktor | Vorzeichen | Bedeutung |
|---|---|---|---|---|---|
| `23/1/4` | ComfoClime | 2 | 0.1 | ja | Min. Außentemperatur WP |
| `23/1/6` | ComfoClime | 2 | 0.1 | ja | Min. Zulufttemperatur Kühlen |
| `23/1/7` | ComfoClime | 2 | 0.1 | nein | Max. Zulufttemperatur Heizen |
| `23/1/14` | ComfoClime | 2 | 0.1 | ja | Min. Komforttemperatur Kühlen |
| `23/1/16` | ComfoClime | 1 | 1.0 | nein | Max. Leistung WP |
| `23/1/18` | ComfoClime | 2 | 0.1 | nein | Hysterese Heizen |
| `23/1/19` | ComfoClime | – | – | – | Hysterese Kühlen |
| `29/1/6` | ComfoClime | – | – | – | Luftfeuchte-Komfortregelung (Select) |
| `29/1/7` | ComfoClime | – | – | – | Feuchteschutz (Select) |
| `30/1/18` | ComfoClime | – | – | – | Lüftungsungleichgewicht (Sensor) |

Bei `–` steht in den Definitionen kein Wert. Vor Nutzung prüfen.

## E. Home-Assistant-Services (Schnittstelle nach außen)

| Service | Pflichtfelder | Optional | Wirkung |
|---|---|---|---|
| `comfoclime.set_property` | `device_id`, `path`, `value`, `byte_count` (1–2) | `signed`, `faktor` (Standard 1.0) | Property schreiben, Endpoint 10 |
| `comfoclime.reset_system` | – | – | Gerät neu starten, Endpoint 11 |
| `comfoclime.set_scenario_mode` | `entity_id`, `scenario` (`cooking`, `party`, `away`, `boost`) | `duration` (1–1440 min), `start_delay` (`YYYY-MM-DD HH:MM:SS`) | Szenario über Dashboard-PUT (Endpoint 3) |

Szenario-Standarddauern: `cooking` 30 min, `party` 30 min, `away` 1440 min, `boost` 30 min.

## F. Offene Punkte

1. **`temperature_profile` 1:** Der Docstring von `async_update_thermal_profile` nennt „power“. Dashboard und Doku nennen „boost“. Bitte entscheiden.
2. **Toter Code:** `_update_thermal_profile` in `comfoclime_api.py` (Zeile 576) wird nirgends aufgerufen.
3. **Docstrings:** Einige Beispiele greifen per dict auf Modelle zu (`data['indoorTemperature']`). Die Methoden liefern aber Pydantic-Modelle.
4. **Mindestabstand:** `CLAUDE.md` 0.1 s, Code 0.5 s.
5. **`cache_ttl`:** Typ `int`, Standard `float`. Die Konvertierung verliert Nachkommastellen.

## G. Diese Datei ersetzt

Die drei Teildateien in diesem Ordner (`schnittstellen.md`, `dashboard-endpoint.md`, `comfoclime-api-schnittstellen.md`) sind damit redundant. Diese Übersicht ist die Hauptdatei.
