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

### PDO Datentypen (CN_*)

> Quelle: [aiocomfoconnect PROTOCOL-PDO.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md)

| Typ-ID | Name | Bytes | Beschreibung |
|---|---|---|---|
| 0 | CN_BOOL | 1 | Boolean: 0=false, 1=true |
| 1 | CN_UINT8 | 1 | Vorzeichenlos, 0–255 |
| 2 | CN_UINT16 | 2 | Vorzeichenlos, Little-Endian |
| 3 | CN_UINT32 | 4 | Vorzeichenlos, Little-Endian |
| 5 | CN_INT8 | 1 | Vorzeichenbehaftet, −128–127 |
| 6 | CN_INT16 | 2 | Vorzeichenbehaftet, Little-Endian |
| 8 | CN_INT64 | 8 | Vorzeichenbehaftet, Little-Endian |
| 9 | CN_STRING | var | Nullterminierter String |
| 10 | CN_TIME | var | Zeitstempel |
| 11 | CN_VERSION | 4 | Versions-Blob (UINT32, Little-Endian) |

> **Faustregel:** Temperaturen = CN_INT16 × 0.1 | Prozentwerte = CN_UINT8 | Drehzahl/Leistung = CN_UINT16

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

#### Weitere PDO-Sensor-IDs ComfoAirQ (aus aiocomfoconnect-Dokumentation)

> Quelle: [aiocomfoconnect PROTOCOL-PDO.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md)

| ID | Typ | Beschreibung | Werte / Einheit |
|---|---|---|---|
| 16 | CN_UINT8 | Gerätestatus | 0=Init, 1=Normal, 2=Filterwechsel, 6=Standby, 7=Abwesend |
| 65 | CN_UINT8 | Lüfterstufen-Einstellung | 0=Abwesend, 1=Niedrig, 2=Mittel, 3=Hoch |
| 66 | CN_UINT8 | Bypass-Aktivierungsmodus | 0=Auto, 1=Voll offen, 2=Keine |
| 67 | CN_UINT8 | Temperaturprofil | 0=Normal, 1=Kalt, 2=Warm |
| 119 | CN_UINT16 | Abluft-Volumenstrom | m³/h |
| 120 | CN_UINT16 | Zuluft-Volumenstrom | m³/h |
| 192 | CN_UINT16 | Verbleibende Filtertage | Tage |
| 208 | CN_UINT8 | Temperatureinheit | 0=Celsius, 1=Fahrenheit |
| 210 | CN_BOOL | Heizperiode aktiv | 0=inaktiv, 1=aktiv |
| 211 | CN_BOOL | Kühlperiode aktiv | 0=inaktiv, 1=aktiv |
| 212 | CN_UINT8 | Temperaturprofil-Sollwert | °C × 0.1 |
| 213 | CN_UINT16 | Vermiedene Heizleistung (aktuell) | W × 0.01 |
| 214 | CN_UINT16 | Vermiedene Heizenergie (Jahr) | kWh |
| 215 | CN_UINT16 | Vermiedene Heizenergie (gesamt) | kWh |
| 216 | CN_UINT16 | Vermiedene Kühlleistung (aktuell) | W × 0.01 |
| 217 | CN_UINT16 | Vermiedene Kühlenergie (Jahr) | kWh |
| 218 | CN_UINT16 | Vermiedene Kühlenergie (gesamt) | kWh |
| 220 | CN_INT16 | Außenluft nach Vorheizer | °C × 0.1 |
| 221 | CN_INT16 | Zuluft nach Nachheizer | °C × 0.1 |
| 224 | CN_UINT8 | Luftmengen-Einheit | 1=kg/h, 2=l/s, 3=m³/h |
| 225 | CN_UINT8 | Sensorbasierter Lüftungsmodus | 0=Deaktiviert, 1=Aktiv, 2=Übersteuernd |
| 226 | CN_UINT16 | Lüfter-Drehzahl (moduliert) | 0–300 |
| 274 | CN_INT16 | Abluft-Temperatur (Extract) | °C × 0.1 |
| 276 | CN_INT16 | Außenluft-Temperatur | °C × 0.1 |
| 338 | CN_UINT32 | Bypass-Überschreibung | 0=Auto, 2=Überschrieben |
| 784 | CN_UINT8 | ComfoCool-Status | 0=Aus, 1=Ein |
| 802 | CN_INT16 | ComfoCool Kondensator-Temperatur | °C × 0.1 |

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

### RMI-Protokoll Hintergrund (ComfoAirQ)

> Quelle: [aiocomfoconnect PROTOCOL-RMI.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md)

#### Nodes

| Hex | Dezimal | Beschreibung |
|---|---|---|
| 0x01 | 1 | Lüftungsgerät (ComfoAirQ) |
| 0x30 | 48 | ComfoConnect LAN C |

#### Units im ComfoAirQ (Ventilation Unit)

| Hex | Dez. | Name | Beschreibung |
|---|---|---|---|
| 0x01 | 1 | NODE | Gerätekennzeichnung (Seriennummer, Firmware, Name) |
| 0x02 | 2 | COMFOBUS | ComfoNet-Bus-Kommunikation |
| 0x03 | 3 | ERROR | Fehlerspeicher, Fehler zurücksetzen |
| 0x15 | 21 | SCHEDULE | Zeitpläne, Timer, Lüfterstufe, Bypass |
| 0x16 | 22 | VALVE | Bypass-Vorheizer-Ventile |
| 0x17 | 23 | FAN | Zuluft- und Abluftventilatoren |
| 0x18 | 24 | POWERSENSOR | Leistungsmessung, Energie-Zähler |
| 0x19 | 25 | PREHEATER | Optionaler Vorheizer |
| 0x1A | 26 | HMI | Display + Tasten |
| 0x1B | 27 | RFCOMMUNICATION | Funk-Kommunikation |
| 0x1C | 28 | FILTER | Filterwechsel-Zähler |
| 0x1D | 29 | TEMPHUMCONTROL | Temperatur-/Feuchtesteuerung |
| 0x1E | 30 | VENTILATIONCONFIG | Lüftungskonfiguration |
| 0x20 | 32 | NODECONFIGURATION | Gerätekonfiguration, Wartungspasswort |
| 0x21 | 33 | TEMPERATURESENSOR | 6 Temperatursensoren |
| 0x22 | 34 | HUMIDITYSENSOR | 6 Feuchtigkeitssensoren |
| 0x23 | 35 | PRESSURESENSOR | 2 Drucksensoren |
| 0x24 | 36 | PERIPHERALS | Externe Geräte (ComfoCool) |
| 0x25 | 37 | ANALOGINPUT | Analoge Eingänge (0–10 V) |
| 0x26 | 38 | COOKERHOOD | ComfoHood |
| 0x27 | 39 | POSTHEATER | Optionaler Nachheizer |
| 0x28 | 40 | COMFOFOND | Erdwärmetauscher |

#### RMI-Befehle

| Befehl | Syntax | Beschreibung |
|---|---|---|
| `0x01` | `01 Unit SubUnit Type Property` | Einzelne Property lesen |
| `0x02` | `02 Unit SubUnit 01 Type+Count Prop1 Prop2 ...` | Mehrere Properties in einem Aufruf lesen |
| `0x03` | `03 Unit SubUnit Property Value` | Property schreiben |

**Type beim Lesen:** `0x10` = Aktueller Wert · `0x20` = Wertebereich · `0x40` = Schrittweite (OR-kombinierbar)

**RMI-Fehlercodes:**

| Code | Bedeutung |
|---|---|
| 11 | Unbekannter Befehl |
| 12 | Unbekannte Unit |
| 13 | Unbekannte SubUnit |
| 14 | Unbekannte Property |
| 30 | Wert außerhalb des Bereichs |
| 32 | Property nicht les-/schreibbar |
| 40/41 | Interner Fehler |

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

### Bekannte CAQ-Properties aus upstream Dokumentation

> Quelle: [aiocomfoconnect PROTOCOL-RMI.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md) – Direkte RMI-Property-Adressen für die ComfoAirQ-Ventilationseinheit.

#### TEMPHUMCONTROL (`0x1D` / Unit 29) – Temperatur-/Feuchtesteuerung

| Pfad | Typ | Zugriff | Beispielwert | Bedeutung |
|---|---|---|---|---|
| `29/1/1` | UINT8 | r | 1 | Aktiv-Flag |
| `29/1/2` | INT16 | rw | 180 → 18.0°C | RMOT Heizperiode (×0.1) |
| `29/1/3` | INT16 | rw | 200 → 20.0°C | RMOT Kühlperiode (×0.1) |
| `29/1/4` | UINT8 | rw | 0 | Temperaturpassivregelung (0=Aus, 1=NurAuto, 2=Ein) |
| `29/1/5` | UINT8 | rw | 0 | Unbekannt |
| `29/1/6` | UINT8 | rw | 0 | Feuchtekomfortregelung (0=Aus, 1=NurAuto, 2=Ein) |
| `29/1/7` | UINT8 | rw | 0 | Feuchteschutzregelung (0=Aus, 1=NurAuto, 2=Ein) |
| `29/1/8` | UINT8 | rw | 0 | Unbekannt |
| `29/1/10` | INT16 | rw | 230 → 23.0°C | Solltemperatur Heizprofil: Warm |
| `29/1/11` | INT16 | rw | 210 → 21.0°C | Solltemperatur Heizprofil: Normal |
| `29/1/12` | INT16 | rw | 190 → 19.0°C | Solltemperatur Heizprofil: Kalt |
| `29/1/13` | UINT8 | – | 0 | Unbekannt |

#### VENTILATIONCONFIG (`0x1E` / Unit 30) – Lüftungskonfiguration

| Pfad | Typ | Zugriff | Beispielwert | Bedeutung |
|---|---|---|---|---|
| `30/1/1` | UINT8 | – | 1 | Aktiv-Flag |
| `30/1/2` | UINT8 | – | 15 | Interne Lüfterstufe |
| `30/1/3` | INT16 | rw | 75 | Lüftungsgeschwindigkeit Abwesend (m³/h) |
| `30/1/4` | INT16 | rw | 110 | Lüftungsgeschwindigkeit Stufe 1/Niedrig (m³/h) |
| `30/1/5` | INT16 | rw | 180 | Lüftungsgeschwindigkeit Stufe 2/Mittel (m³/h) |
| `30/1/6` | INT16 | rw | 370 | Lüftungsgeschwindigkeit Stufe 3/Hoch (m³/h) |
| `30/1/7` | UINT8 | – | 0 | Höhe ü. NN (0=0–500m, 1=500–1000m, 2=1000–1500m, 3=1500–2000m) |
| `30/1/9` | UINT8 | – | 0 | Lüftungsregelungsart (0=Volumenstromregelung, 1=Konstantdruck) |
| `30/1/11` | INT16 | – | – | Badezimmerschalter Einschaltverzögerung (s) |
| `30/1/12` | UINT8 | – | – | Badezimmerschalter Ausschaltverzögerung (min) |
| `30/1/13` | UINT8 | – | – | Badezimmerschalter Modus (0=fest, 1=gespiegelt) |
| `30/1/18` | INT16 | – | – | Unbalance-Einstellung (×0.1) |

#### NODECONFIGURATION (`0x20` / Unit 32)

| Pfad | Typ | Zugriff | Bedeutung |
|---|---|---|---|
| `32/1/3` | STRING | – | Wartungspasswort (DE=4210, BE=2468) |
| `32/1/4` | UINT8 | – | Einbaulage (0=Links, 1=Rechts) |

#### SCHEDULE-Befehle (Unit 0x15=21, Raw-RMI)

Diese Hex-Befehle werden direkt über den ComfoConnect LAN C gesendet (nicht über HTTP API).

| Hex-Befehl | Beschreibung |
|---|---|
| `84 15 01 01 00000000 01000000 00` | Lüftungsstufe: Abwesend |
| `84 15 01 01 00000000 01000000 01` | Lüftungsstufe: 1 (Niedrig) |
| `84 15 01 01 00000000 01000000 02` | Lüftungsstufe: 2 (Mittel) |
| `84 15 01 01 00000000 01000000 03` | Lüftungsstufe: 3 (Hoch) |
| `84 15 01 06 00000000 58020000 03` | Boost: 10 Minuten (600s = 0x0258) |
| `85 15 01 06` | Boost: Beenden |
| `85 15 08 01` | Lüftungsmodus: Automatisch |
| `84 15 08 01 00000000 01000000 01` | Lüftungsmodus: Manuell |
| `84 15 02 01 00000000 100e0000 01` | Bypass: 1 Stunde öffnen |
| `84 15 02 01 00000000 100e0000 02` | Bypass: 1 Stunde schließen |
| `85 15 02 01` | Bypass: Automatisch |
| `84 15 03 01 00000000 ffffffff 00` | Temperaturprofil: Normal |
| `84 15 03 01 00000000 ffffffff 01` | Temperaturprofil: Kalt |
| `84 15 03 01 00000000 ffffffff 02` | Temperaturprofil: Warm |
| `84 15 06 01 00000000 100e0000 01` | Lüftungsmodus: Nur Zuluft (1h) |
| `85 15 06 01` | Lüftungsmodus: Balanced (zurücksetzen) |

> **Hinweis:** Der SCHEDULE-Unit-Befehl `0x84` aktiviert einen Eintrag mit Startzeitstempel und Dauer. `0x85` deaktiviert/beendet ihn. Die HTTP-API umhüllt diese Befehle für Lüfterstufe/Boost/Szenario-Modi.

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
| [aiocomfoconnect PROTOCOL-RMI.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md) | Vollständige RMI-Protokoll-Dokumentation (Nodes, Units, Befehle, Fehler) |
| [aiocomfoconnect PROTOCOL-PDO.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md) | Vollständige PDO-Telemetrie-ID-Liste mit Datentypen |

---

## 16. Gerätefehler-Codes (ComfoAirQ)

> Quelle: [aiocomfoconnect PROTOCOL-RMI.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md) – Fehler werden per `ERROR`-Unit (0x03) über `0x80 GETACTIVEERRORS` abgefragt und mit `0x82 RESETALLERRORS` zurückgesetzt.

### Kritische Fehler

| Code | Beschreibung |
|---|---|
| 21 | **ÜBERHITZUNG!** Mehrere Sensoren melden fehlerhafte Temperatur – Lüftung gestoppt |
| 22 | Temperatur zu hoch für ComfoAir Q |
| 33 | Gerät nicht in Betrieb genommen (INIT ERROR) |
| 34 | Fronttür ist offen |

### Sensor-Fehler

| Code | Sensor | Beschreibung |
|---|---|---|
| 23 | ETA | Abluft-Temperatursensor – Ausfall |
| 24 | ETA | Abluft-Temperatursensor – Falscher Wert |
| 25 | EHA | Fortluft-Temperatursensor – Ausfall |
| 26 | EHA | Fortluft-Temperatursensor – Falscher Wert |
| 27 | ODA | Außenluft-Temperatursensor – Ausfall |
| 28 | ODA | Außenluft-Temperatursensor – Falscher Wert |
| 31 | SUP | Zuluft-Temperatursensor – Ausfall |
| 32 | SUP | Zuluft-Temperatursensor – Falscher Wert |
| 39 | ETA | Abluft-Feuchtigkeitssensor – Ausfall |
| 41 | EHA | Fortluft-Feuchtigkeitssensor – Ausfall |
| 43 | ODA | Außenluft-Feuchtigkeitssensor – Ausfall |
| 47 | SUP | Zuluft-Feuchtigkeitssensor – Ausfall |

### Lüfter & Luftstrom-Fehler

| Code | Beschreibung |
|---|---|
| 49 | Abluftstrom-Sensor – Ausfall |
| 50 | Zuluftstrom-Sensor – Ausfall |
| 51 | Ablüfter – Ausfall |
| 52 | Zulüfter – Ausfall |
| 53 | Abluftdruck zu hoch (Filter/Kanäle prüfen) |
| 54 | Zuluftdruck zu hoch (Filter/Kanäle prüfen) |
| 57 | Abluftstrom erreicht Sollwert nicht |
| 58 | Zuluftstrom erreicht Sollwert nicht |
| 62 | Unbalance zu oft außerhalb Toleranz |

### Wartungs-Meldungen

| Code | Beschreibung |
|---|---|
| 77 | **Filter muss jetzt getauscht werden** |
| 78 | Externen Filter reinigen/tauschen |
| 79 | Neue Filter bestellen (Restlaufzeit begrenzt) |
| 80 | **Service-Modus aktiv** |
| 89 | Bypass im manuellen Modus |

### Verbindungsfehler (Firmware ≥ 1.4.0)

| Code | Beschreibung |
|---|---|
| 70 | Analogeingang 1 nicht mehr erkannt |
| 71 | Analogeingang 2 nicht mehr erkannt |
| 72 | Analogeingang 3 nicht mehr erkannt |
| 73 | Analogeingang 4 nicht mehr erkannt |
| 74 | ComfoHood nicht mehr erkannt |
| 75 | ComfoCool nicht mehr erkannt |
| 76 | ComfoFond nicht mehr erkannt |
| 101 | ComfoNet-Fehler |
| 102 | Anzahl CO₂-Sensoren verringert |
| 103 | Mehr als 8 Sensoren in einer Zone erkannt |
