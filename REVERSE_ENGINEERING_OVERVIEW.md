# Zehnder ComfoClime – Reverse Engineering Übersicht

> **Erstellt:** 2026-04-28
> **Gerät:** `http://10.0.2.27` (ComfoClime 24, Firmware R1.5.5)
> **Methode:** Live-API-Abfragen + Projektdokumentation

---

## 1. Was ist das System?

Das Zehnder ComfoClime ist eine **lokale Wärmepumpen-Einheit**, die über HTTP direkt im Heimnetz erreichbar ist – **ohne Authentifizierung, ohne Cloud**. Sie kommuniziert mit weiteren Zehnder-Geräten über den **ComfoNet-Bus** und steuert Heizen, Kühlen und Lüftung.

### Geräte im Netzwerk (10.0.2.27)

| Gerät | UUID | modelTypeId | Firmware |
|---|---|---|---|
| **ComfoClime 24** (Wärmepumpe) | `MBE083a8d0146e1` | `20` | R1.5.5 |
| **ComfoAirQ 350** (Lüftungsgerät) | `SIT14276877` | `1` | – |
| **ComfoConnectLANC** (Gateway) | `DEM0121153000` | `5` | – |

**UUID = Seriennummer des Geräts** (z. B. `MBE083a8d0146e1`)

---

## 2. API-Grundlagen

```
Basis-URL:  http://10.0.2.27
Protokoll:  HTTP/1.1 (kein HTTPS, kein Auth)
Format:     JSON
```

### Schritt 1 – UUID holen (immer zuerst!)

```bash
curl http://10.0.2.27/monitoring/ping
```

```json
{
  "uuid": "MBE083a8d0146e1",
  "up_time_seconds": 162416,
  "timestamp": "2026-04-28T20:20:33.0Z"
}
```

---

## 3. Alle API-Endpunkte

### GET-Endpunkte (Lesen)

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| GET | `/monitoring/ping` | UUID, Uptime, Timestamp |
| GET | `/system/{UUID}/dashboard` | Temperaturen, Lüfter, Modus, Status |
| GET | `/system/{UUID}/devices` | Liste aller ComfoNet-Geräte |
| GET | `/system/{UUID}/thermalprofile` | Heiz-/Kühl-Kurven-Konfiguration |
| GET | `/device/{UUID}/definition` | Gerätedefinition (Modell, Typ, Zustand) |
| GET | `/device/{UUID}/telemetry/{ID}` | Sensorwert (PDO-Protokoll) |
| GET | `/device/{UUID}/property/{X}/{Y}/{Z}` | Geräte-Eigenschaft (RMI-Protokoll) |

### PUT-Endpunkte (Schreiben)

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| PUT | `/system/{UUID}/dashboard` | Solltemperatur, Lüfter, Modus, Szenario |
| PUT | `/system/{UUID}/thermalprofile` | Heiz-/Kühlprofil anpassen |
| PUT | `/device/{UUID}/method/{X}/{Y}/3` | Eigenschaft schreiben (RMI) |
| PUT | `/system/reset` | Gerät neu starten |

---

## 4. Live-Zustand des Geräts (28.04.2026 ~20:22 Uhr)

### Dashboard

```json
{
  "indoorTemperature": 21.2,
  "outdoorTemperature": 16.6,
  "exhaustAirFlow": 208,
  "supplyAirFlow": 209,
  "fanSpeed": 2,
  "setPointTemperature": 21.0,
  "season": 2,
  "schedule": 0,
  "status": 0,
  "heatPumpStatus": 5,
  "hpStandby": false,
  "freeCoolingEnabled": false,
  "caqFreeCoolingAvailable": true
}
```

**Interpretation:**
- `season: 2` → Kühlmodus aktiv
- `status: 0` → Manuelle Temperatursteuerung
- `heatPumpStatus: 5` → Kühlen aktiv (Bit 0=laufend, Bit 2=Kühlen)
- `fanSpeed: 2` → Lüfterstufe 2 (von 0–3)
- `caqFreeCoolingAvailable: true` → ComfoAir-Bypass-Freikühlungsverfügbar

### Thermalprofil

```json
{
  "season": { "status": 0, "season": 2, "heatingThresholdTemperature": 12.0, "coolingThresholdTemperature": 16.0 },
  "temperature": { "status": 0, "manualTemperature": 21.0 },
  "temperatureProfile": 2,
  "heatingThermalProfileSeasonData": { "comfortTemperature": 22.0, "kneePointTemperature": 10.0, "reductionDeltaTemperature": 2.0 },
  "coolingThermalProfileSeasonData": { "comfortTemperature": 20.0, "kneePointTemperature": 20.0, "temperatureLimit": 25.0 }
}
```

**Interpretation:** `temperatureProfile: 2` = Eco-Modus

---

## 5. Datendecodierung (PDO/Telemetrie)

Alle Telemetrie-Werte kommen als **Byte-Array im Little-Endian-Format**:

```json
{ "data": [216, 0] }
```

**Decodierungsformel:**

```python
# 2 Bytes, vorzeichenbehaftet (INT16), Faktor 0.1
value = 216 + (0 << 8)   # = 216
# vorzeichenbehaftet? nein (216 < 32768)
result = 216 * 0.1       # = 21.6°C  ✓
```

| Bytes | Typ | Beispiel-Bytes | Rohdec | Faktor | Ergebnis |
|---|---|---|---|---|---|
| 1 | UINT8 | `[2]` | 2 | 1.0 | Modus=2 (Kühlen) |
| 1 | UINT8 | `[100]` | 100 | 1.0 | Bypass=100% |
| 2 | INT16 | `[216, 0]` | 216 | 0.1 | 21.6°C |
| 2 | INT16 | `[234, 1]` | 490 | 0.1 | 49.0°C |
| 2 | UINT16 | `[180, 0]` | 180 | 1.0 | 180 W |

**Negativer Wert (Vorzeichen):**

```python
# [60, 255] = 0xFF3C = 65340 → 65340 - 65536 = -196 → * 0.1 = -19.6°C
value = 60 + (255 << 8)   # = 65340
if value >= 0x8000:
    value -= 0x10000       # = -196
result = -196 * 0.1        # = -19.6°C
```

---

## 6. Telemetrie-Werte (Live-Messung)

### ComfoClime 24 (`MBE083a8d0146e1`, modelTypeId=20)

| Telemetrie-ID | Beschreibung | Rohdaten | Dekodiert | Typ |
|---|---|---|---|---|
| **4145** | TPMA Temperatur | `[121, 0]` | **12.1°C** | INT16, ×0.1 |
| **4149** | Betriebsmodus | `[2]` | **2 = Kühlen** | UINT8 |
| **4151** | Komfort-Solltemperatur | `[216, 0]` | **21.6°C** | INT16, ×0.1 |
| **4154** | Innentemperatur | `[212, 0]` | **21.2°C** | INT16, ×0.1 |
| **4193** | Zulufttemperatur | `[97, 0]` | **9.7°C** | INT16, ×0.1 |
| **4194** | Fortlufttemperatur | `[208, 0]` | **20.8°C** | INT16, ×0.1 |
| **4195** | Zuluft-Gas-Temperatur (Verdampfer) | `[113, 0]` | **11.3°C** | INT16, ×0.1 |
| **4196** | Abluft-Gas-Temperatur (Verflüssiger) | `[25, 1]` | **28.1°C** | INT16, ×0.1 |
| **4197** | Kompressor-Temperatur | `[234, 1]` | **49.0°C** | INT16, ×0.1 |
| **4198** | Wärmepumpe Leistungsstufe | `[1]` | **1 (min)** | UINT8 |
| **4201** | Aktuelle elektrische Leistung | `[180, 0]` | **180 W** | UINT16 |
| **4202** | Hochdruck (Warmseite) | `[98, 1]` | **354 kPa** | UINT16 |
| **4203** | Expansionsventil-Öffnung | `[20, 0]` | **20%** | UINT16 |
| **4205** | Niederdruck (Kaltseite) | `[60, 0]` | **60 kPa** | UINT16 |
| **4207** | 4-Wege-Ventil Position | `[1, 0]` | **1 (Kühlen)** | UINT16 |

**Betriebsmodus-Codes (ID 4149):**
- `0` = Aus
- `1` = Heizen
- `2` = Kühlen

### ComfoAirQ 350 (`SIT14276877`, modelTypeId=1)

| Telemetrie-ID | Beschreibung | Rohdaten | Dekodiert | Typ |
|---|---|---|---|---|
| **117** | Abluft-Lüfter Ansteuerung | `[89]` | **89%** | UINT8 |
| **118** | Zuluft-Lüfter Ansteuerung | `[70]` | **70%** | UINT8 |
| **121** | Abluft-Lüfter Drehzahl | `[2, 12]` | **3077 rpm** | UINT16 |
| **122** | Zuluft-Lüfter Drehzahl | `[93, 10]` | **2653 rpm** | UINT16 |
| **128** | Lüftungs-Leistungsaufnahme | `[120, 0]` | **120 W** | UINT16 |
| **129** | Lüftung Energie (Jahr) | `[207, 0]` | **207 kWh** | UINT16 |
| **130** | Lüftung Energie (gesamt) | `[129, 2]` | **641 kWh** | UINT16 |
| **209** | RMOT (mittlere Außentemperatur) | `[132, 0]` | **13.2°C** | INT16, ×0.1 |
| **227** | Bypass-Klappe | `[100]` | **100%** | UINT8 |
| **275** | Fortluft-Temperatur | `[208, 0]` | **20.8°C** | INT16, ×0.1 |
| **278** | Zuluft-Temperatur | `[186, 0]` | **18.6°C** | INT16, ×0.1 |
| **290** | Abluft-Feuchtigkeit | `[39]` | **39%** | UINT8 |
| **291** | Fortluft-Feuchtigkeit | `[38]` | **38%** | UINT8 |
| **292** | Außenluft-Feuchtigkeit | `[37]` | **37%** | UINT8 |
| **294** | Zuluft-Feuchtigkeit | `[35]` | **35%** | UINT8 |

---

## 7. Properties (RMI-Protokoll)

Properties werden über `Unit/SubUnit/Property` adressiert. Sie können gelesen und geschrieben werden.

### Lesen

```bash
GET /device/{UUID}/property/{Unit}/{SubUnit}/{Property}
# Beispiel:
curl http://10.0.2.27/device/MBE083a8d0146e1/property/22/1/9
# → {"data": [220, 0]}  → 220 * 0.1 = 22.0°C
```

### Schreiben

```bash
PUT /device/{UUID}/method/{Unit}/{SubUnit}/3
Body: {"data": [PropertyID, LSB, MSB]}
# Beispiel: Heizkomfort auf 21.5°C setzen
# raw = int(21.5 / 0.1) = 215 = [215, 0]
# Payload: {"data": [9, 215, 0]}
```

### Property-Scan Ergebnis (vollständiger Brute-Force-Scan, Units 1–31, SubUnits 1–3, Props 1–35)

> Alle nicht aufgeführten Unit/SubUnit/Property-Kombinationen lieferten HTTP 500 oder Timeout.

---

### ComfoClime 24 (`MBE083a8d0146e1`) – Alle gefundenen Properties

#### Unit 1 / SubUnit 1 – Gerätekennzeichnung (NODE)

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `1/1/1` | `[1]` | u8=1 | Zonen-ID |
| `1/1/2` | `[20]` | u8=20 | modelTypeId (20=ComfoClime) |
| `1/1/3` | `[1]` | u8=1 | Produktvariante |
| `1/1/4` | `[77,66,69,48,...]` | `"MBE083a8d0146e1"` | **Seriennummer** |
| `1/1/5` | `[1]` | u8=1 | Hardware-Version |
| `1/1/6` | `[5,20,16,192]` | u32=3223302149 | Firmware-Versions-Blob |
| `1/1/7` | `[0,120,16,192]` | u32=3223275520 | Unbekannt (Timestamp?) |
| `1/1/20` | `[67,111,109,...]` | `"ComfoClime"` | Gerätename |
| `1/1/21` | `[96,150,0,0]` | u32=6000 | Unbekannt (Uptime-Counter?) |

#### Unit 2 / SubUnit 1 – Zeitplan/Modus

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `2/1/1` | `[1]` | u8=1 | Aktiv-Flag |
| `2/1/2` | `[0]` | u8=0 | Zeitplan-Modus (0=aus) |
| `2/1/3` | `[0]` | u8=0 | Unbekannt |
| `2/1/4` | `[0]` | u8=0 | Unbekannt |

#### Unit 21 / SubUnit 1 – Status/Fehler

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `21/1/1` | `[1]` | u8=1 | Status OK (1=kein Fehler) |

#### Unit 22 / SubUnit 1 – Temperaturkonfiguration (TEMPCONFIG) ⭐

Dies ist die wichtigste konfigurierbare Unit. Alle Werte korrespondieren direkt mit dem `/thermalprofile`-Endpunkt.

| Pfad | Rohdaten | Dekodiert | Bedeutung | Thermalprofile-Feld | Schreibbar |
|---|---|---|---|---|---|
| `22/1/4` | `[100,0]` | 10.0°C | Kniepunkt Heizen | `heatingKneePointTemperature` | ✅ |
| `22/1/5` | `[200,0]` | 20.0°C | Kniepunkt Kühlen | `coolingKneePointTemperature` | ✅ |
| `22/1/8` | `[0]` | u8=0 | Kühlsaison-Flag (0=inaktiv?) | – | ✅ |
| `22/1/9` | `[220,0]` | **22.0°C** | Heiz-Komforttemperatur | `heatingComfortTemperature` | ✅ |
| `22/1/10` | `[200,0]` | **20.0°C** | Manuelle Zieltemperatur | `temperature.manualTemperature` | ✅ |
| `22/1/11` | `[250,0]` | **25.0°C** | Temperaturlimit Kühlen | `coolingTemperatureLimit` | ✅ |
| `22/1/13` | `[210,0]` | 21.0°C | Manuelle Temperatur (Spiegel?) | – | ✅ |
| `22/1/15` | `[160,0]` | 16.0°C | Kühlschwelle | `coolingThresholdTemperature` | ✅ |
| `22/1/16` | `[120,0]` | 12.0°C | Heizschwelle | `heatingThresholdTemperature` | ✅ |
| `22/1/17` | `[94,1]` | 35.0°C | Max. Temperaturlimit | – | ❓ |
| `22/1/18` | `[70]` | u8=70 | Unbekannt (70%?) | – | ❓ |
| `22/1/20` | `[50,0]` | 5.0°C | Min. Außentemperatur (HP) | – | ❓ |
| `22/1/21` | `[0]` | u8=0 | Flag | – | ❓ |
| `22/1/23` | `[10]` | u8=10 | Unbekannt | – | ❓ |
| `22/1/24` | `[3,0]` | 0.3°C | Hysterese? | – | ❓ |
| `22/1/25` | `[0]` | u8=0 | Flag | – | ❓ |
| `22/1/28` | `[2]` | u8=**2** | **Temperaturprofil** (2=Eco) | `temperatureProfile` | ✅ |

**Temperaturprofil-Codes (P28):**
- `0` = Komfort
- `1` = Boost
- `2` = Eco

#### Unit 23 / SubUnit 1 – Wärmepumpen-Parameter ⭐ (NEU!)

| Pfad | Rohdaten | Dekodiert | Vermutete Bedeutung |
|---|---|---|---|
| `23/1/4` | `[100,0]` | 10.0°C | Minimale Außentemperatur für HP-Betrieb |
| `23/1/6` | `[50,0]` | 5.0°C | Min. Vorlauftemperatur (Kühlen) |
| `23/1/7` | `[88,2]` | 60.0°C | Max. Vorlauftemperatur (Heizen) |
| `23/1/9` | `[1,0]` | u16=1 | Unbekanntes Flag |
| `23/1/11` | `[0]` | u8=0 | Flag |
| `23/1/12` | `[0,0]` | u16=0 | Zähler oder Offset |
| `23/1/13` | `[1,0]` | u16=1 | Flag |
| `23/1/14` | `[180,0]` | 18.0°C | Min. Komforttemperatur (Kühlen?) |
| `23/1/16` | `[100]` | u8=100 | Max. HP Leistung (100%) |
| `23/1/18` | `[45,0]` | 4.5°C | Hysterese Heizen |
| `23/1/19` | `[2,0]` | 0.2°C | Hysterese Kühlen |

#### Unit 25 / SubUnit 1 – Modus-Setting

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `25/1/1` | `[2,0]` | u16=2 | Aktiver Modus (2=Kühlen?) |

#### Unit 26 / SubUnit 1 – Unbekannt

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `26/1/1` | `[0]` | u8=0 | Flag |

---

### ComfoAirQ 350 (`SIT14276877`) – Alle gefundenen Properties

#### Unit 1 / SubUnit 1 – Gerätekennzeichnung (NODE)

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `1/1/4` | `[83,73,84,49,...]` | `"SIT14276877"` | **Seriennummer** |
| `1/1/6` | `[0,48,16,192]` | u32=3222286336 | Firmware-Versions-Blob |
| `1/1/9` | `[1,0,0,0]` | u32=1 | Unbekannt |
| `1/1/12` | `[78,85,76,76,0]` | `"NULL"` | Leerer Name-Slot |
| `1/1/20` | `[67,111,109,...]` | `"ComfoAirQ"` | Gerätename |

#### Unit 2 / SubUnit 1 – Status

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `2/1/1` | `[1]` | u8=1 | Aktiv-Flag |
| `2/1/4` | `[0]` | u8=0 | Unbekannt |

#### Unit 22 / SubUnit 2 – Bypass-Konfiguration ⭐ (NEU!)

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `22/2/3` | `"100.0"` | 100.0% | **Bypass-Öffnung aktuell** (=T227=100%) |

> SubUnit 2 bei CAQ – ungewöhnlich! Möglicherweise Bypass-Unit.

#### Unit 23 / SubUnit 1 – Lüftungsstatus

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `23/1/1` | `[1]` | u8=1 | Aktiv-Flag |

#### Unit 25 / SubUnit 1 – Filterwarnung / CO₂

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `25/1/2` | `[0]` | u8=0 | Filteralarm (0=kein Alarm) |
| `25/1/3` | `[0]` | u8=0 | Unbekannt |
| `25/1/5` | `[0]` | u8=0 | Unbekannt |

#### Unit 26 / SubUnit 1 – Sprach-/Ländereinstellungen ⭐ (NEU!)

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `26/1/4` | `[71,69,82,77,65,78,0]` | `"GERMAN"` | **Spracheinstellung** |
| `26/1/5` | `[0]` | u8=0 | Sommerzeitoption |
| `26/1/6` | `[0]` | u8=0 | Unbekannt |

#### Unit 27 / SubUnit 1 – Alarmeinstellungen

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `27/1/4` | `[1]` | u8=1 | Alarm aktiv |
| `27/1/5` | `[0]` | u8=0 | Alarm-Typ? |

#### Unit 28 / SubUnit 1 – Komforttemperatur-Basis

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `28/1/3` | `[180,0]` | 18.0°C | Min. Komfortzuluft? |

#### Unit 29 / SubUnit 1 – Soll-Temperatur

| Pfad | Rohdaten | Dekodiert | Bedeutung |
|---|---|---|---|
| `29/1/1` | `[1]` | u8=1 | Aktiv-Flag |
| `29/1/3` | `[200,0]` | 20.0°C | Solltemperatur |
| `29/1/13` | `[0]` | u8=0 | Flag |

#### Unit 30 / SubUnit 1 – Lüftungsregelung ⭐ (NEU! Sehr interessant)

| Pfad | Rohdaten | Dekodiert | Vermutete Bedeutung |
|---|---|---|---|
| `30/1/1` | `[1]` | u8=1 | Aktiv-Flag |
| `30/1/2` | `[15]` | u8=15 | Lüfterstufe intern (0-15?) |
| `30/1/4` | `[100,0]` | 10.0°C | Außentemperatur-Grenzwert |
| `30/1/6` | `[215,0]` | 21.5°C | Raumtemperatur-Istwert |
| `30/1/7` | `[0]` | u8=0 | Betriebsflag |
| `30/1/8` | `[215,0]` | 21.5°C | Raumtemperatur (Spiegel/P6) |
| `30/1/11` | `[0,0]` | u16=0 | Zähler |
| `30/1/13` | `[0]` | u8=0 | Flag |
| `30/1/15` | `[0]` | u8=0 | Flag |
| `30/1/18` | `[0,0]` | u16=0 | Zähler |
| `30/1/20` | `[0,0]` | u16=0 | Zähler |
| `30/1/24` | `[0,0]` | u16=0 | Energie-Zähler? |
| `30/1/26` | `[48,4]` | u16=1072 | Energie oder rpm |
| `30/1/30` | `[234,8]` | u16=2282 | Energie oder Luftmenge (m³/h × 10?) |

> **Hinweis zu P30:** 2282 als Luftmenge wäre 228.2 m³/h (Faktor 0.1) – passt gut zu Dashboard `exhaustAirFlow: 208`. Oder 2282 ist ein Energie-Zähler-Wert.

---

### Property-Übersicht: Unit-Bedeutungen

| Unit | ComfoClime (CC) | ComfoAirQ (CAQ) |
|---|---|---|
| 1 | NODE (Gerätekennzeichnung) | NODE (Gerätekennzeichnung) |
| 2 | Zeitplan/Modus | Status |
| 21 | Status/Fehler | – |
| 22 | TEMPCONFIG (Temperaturkonfiguration) | Bypass-Konfiguration (SubUnit 2!) |
| 23 | Wärmepumpen-Parameter | Lüftungsstatus |
| 25 | Modus-Setting | Filterwarnung |
| 26 | Unbekannt | Sprach-/Ländereinstellungen |
| 27 | – | Alarmeinstellungen |
| 28 | – | Min. Komforttemperatur |
| 29 | – | Solltemperatur |
| 30 | – | Lüftungsregelung (viele Werte!) |

---

## 8. Dashboard steuern

### Temperatur manuell setzen (manueller Modus)

```bash
PUT http://10.0.2.27/system/MBE083a8d0146e1/dashboard
Content-Type: application/json

{
  "setPointTemperature": 22.0,
  "status": 0,
  "timestamp": "2026-04-28T20:00:00"
}
```

### Automatischer Modus mit Profil

```bash
{ "temperatureProfile": 0, "status": 1, "timestamp": "..." }
```

### Lüftungsstufe setzen

```bash
{ "fanSpeed": 3, "timestamp": "..." }
```

### Heizmodus aktivieren

```bash
{ "season": 1, "hpStandby": false, "timestamp": "..." }
```

### Wärmepumpe ausschalten (Standby)

```bash
{ "hpStandby": true, "timestamp": "..." }
```

---

## 9. Szenario-Modi

Zeitgesteuerte Aktivierung von Betriebsmodi:

| Code | Name | Beschreibung |
|---|---|---|
| `4` | Kochen | Erhöhte Lüftung, begrenzte Dauer |
| `5` | Party | Erhöhte Lüftung, begrenzte Dauer |
| `7` | Abwesend | Reduzierter Betrieb |
| `8` | Boost | Maximale Leistung |

```bash
# Beispiel: Kochen für 30 Minuten
{ "scenario": 4, "scenarioTimeLeft": 1800, "timestamp": "..." }
```

Felder im Dashboard wenn aktiv:
- `scenario`: aktiver Modus (oder `null`)
- `scenarioTimeLeft`: verbleibende Sekunden (oder `null`)
- `scenarioStartDelay`: Startverzögerung in Sekunden (optional)

---

## 10. Heat Pump Status (`heatPumpStatus`) – Bitfeld

| Wert | Bedeutung | Bits |
|---|---|---|
| `0` | Aus | – |
| `1` | Startet | Bit 0 |
| `3` | Heizen | Bit 0+1 |
| **`5`** | **Kühlen (aktuell)** | **Bit 0+2** |
| `17` | Leerlauf (Übergang) | Bit 0+4 |
| `19` | Heizen (Übergang) | Bit 0+1+4 |
| `21` | Kühlen (Übergang) | Bit 0+2+4 |
| `67` | Heizen | Bit 0+1+6 |

**Bit-Interpretation:**
- Bit 0 (`0x01`): Gerät läuft
- Bit 1 (`0x02`): Heizmodus
- Bit 2 (`0x04`): Kühlmodus
- Bit 4 (`0x10`): Übergang
- Bit 6 (`0x40`): Abtauen / Sonderbetrieb

---

## 11. Gerätedefinitionen (`/definition` Endpunkt)

### ComfoClime 24

```json
{
  "uuid": "MBE083a8d0146e1",
  "modelTypeId": 20,
  "variant": 1,
  "zoneId": 1,
  "@modelType": "ComfoClime 24",
  "name": "ComfoClime 24",
  "version": "R1.5.5",
  "setPointTemperature": 21.0,
  "indoorTemperature": 21.2,
  "supplyTemperature": 9.8,
  "heatPumpStatus": 5,
  "status": 0
}
```

### ComfoAirQ 350

```json
{
  "uuid": "SIT14276877",
  "modelTypeId": 1,
  "variant": 1,
  "zoneId": 1,
  "@modelType": "ComfoAirQ 350",
  "fanSpeed": 2,
  "indoorTemperature": 21.2,
  "outdoorTemperature": 16.7,
  "extractTemperature": 21.2,
  "supplyTemperature": 18.6,
  "exhaustTemperature": 20.9
}
```

---

## 12. Systemarchitektur (Integration)

```
                    ComfoNet-Bus
  ┌──────────────────────────────────────────┐
  │                                          │
  ▼                                          ▼
ComfoAirQ 350              ComfoClime 24
(Lüftung + Wärmetauscher)  (Wärmepumpe)
UUID: SIT14276877          UUID: MBE083a8d0146e1
modelTypeId: 1             modelTypeId: 20
                                │
                                │ HTTP REST API
                                ▼
                      http://10.0.2.27
                      (kein Auth, Port 80)
                                │
           ┌────────────────────┼────────────────────┐
           ▼                    ▼                    ▼
    GET /dashboard      GET /telemetry/{id}   PUT /dashboard
    GET /devices        GET /property/X/Y/Z   PUT /method/X/Y/3
    GET /thermalprofile GET /definition       PUT /thermalprofile
    GET /ping                                 PUT /reset
```

**Protokolle:**
- **PDO** (Process Data Object) → Telemetrie-Sensor-Rohdaten, Adressen sind nummerische IDs
- **RMI** (Remote Method Invocation) → Konfigurationseigenschaften, Adresse ist `Unit/SubUnit/Property`

---

## 13. Bekannte Fehler & Eigenheiten

| Symptom | Ursache | Lösung |
|---|---|---|
| `{"error": "Comfonet error"}` | Gerät antwortet nicht auf diese Telemetrie-ID | Nicht alle IDs werden immer geliefert – retry oder ignorieren |
| HTTP 500 bei Property | Property nicht unterstützt (z. B. `22/1/6`) | Nur dokumentierte Properties verwenden |
| `data: [1]` bei Firmware-Version | Property liefert nur 1 Byte, nicht als String | Dezimalwert = interne Versionsnummer |
| `heatPumpStatus` wechselt häufig | Kompressionszyklus, Anlauf, Abtauen | Mehrere Messungen mitteln oder Bitmaske verwenden |
| Temperaturen sporadisch `null` | Sensor noch nicht initialisiert nach Neustart | 60s nach Neustart warten |

---

## 14. Schnellstart (Python)

```python
import requests

BASE = "http://10.0.2.27"

# 1. UUID holen
uuid = requests.get(f"{BASE}/monitoring/ping").json()["uuid"]
print(f"UUID: {uuid}")

# 2. Dashboard lesen
d = requests.get(f"{BASE}/system/{uuid}/dashboard").json()
print(f"Innen: {d['indoorTemperature']}°C | Außen: {d['outdoorTemperature']}°C")
print(f"Lüfter: {d['fanSpeed']} | HP-Status: {d['heatPumpStatus']}")

# 3. Telemetrie: Kompressor-Temperatur
raw = requests.get(f"{BASE}/device/{uuid}/telemetry/4197").json()["data"]
comp_temp = (raw[0] + raw[1] * 256) * 0.1
print(f"Kompressor: {comp_temp}°C")

# 4. Lüfterstufe auf 3 setzen
import datetime
requests.put(
    f"{BASE}/system/{uuid}/dashboard",
    json={"fanSpeed": 3, "timestamp": datetime.datetime.now().isoformat()},
    headers={"Content-Type": "application/json"}
)
```

---

## 15. Referenzen

| Quelle | Beschreibung |
|---|---|
| [ComfoClimeAPI.md](ComfoClimeAPI.md) | Vollständige API-Dokumentation mit Python-Beispielen |
| [SCENARIO_MODES.md](SCENARIO_MODES.md) | Szenario-Modus-Dokumentation |
| [custom_components/comfoclime/comfoclime_api.py](custom_components/comfoclime/comfoclime_api.py) | Produktiver async API-Client (aiohttp) |
| [custom_components/comfoclime/coordinator.py](custom_components/comfoclime/coordinator.py) | Home Assistant Koordinatoren (5 Stück, 60s Intervall) |
| [custom_components/comfoclime/entities/sensor_definitions.py](custom_components/comfoclime/entities/sensor_definitions.py) | Alle Sensor-Definitionen mit byte_count/faktor |
