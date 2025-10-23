# ComfoClime API Dokumentation

Diese Dokumentation beschreibt die REST-API des Zehnder ComfoClime Geräts. Die API ist lokal über HTTP ohne Authentifizierung verfügbar und ermöglicht die vollständige Steuerung und Überwachung von ComfoClime sowie verbundenen Geräten wie ComfoAir Q über den ComfoNet-Bus.

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Identifikatoren](#identifikatoren)
3. [API-Endpunkte Übersicht](#api-endpunkte-übersicht)
4. [Endpunkt-Dokumentation](#endpunkt-dokumentation)
   - [/monitoring/ping](#monitoringping)
   - [/system/{UUID}/dashboard](#systemuuiddashboard)
   - [/system/{UUID}/devices](#systemuuiddevices)
   - [/system/{UUID}/thermalprofile](#systemuuidthermalprofile)
   - [/system/{UUID}/alarms](#systemuuidalarms)
   - [/device/{UUID}/property/{X}/{Y}/{Z}](#deviceuuidpropertyxyz)
   - [/device/{UUID}/telemetry/{N}](#deviceuuidtelemetryn)
   - [/device/{UUID}/method/{X}/{Y}/3](#deviceuuidmethodxy3)
   - [/system/reset](#systemreset)
5. [ComfoClime Einheiten und Properties](#comfoclime-einheiten-und-properties)
6. [ComfoClime Sensoren (Telemetrie)](#comfoclime-sensoren-telemetrie)
7. [Heat Pump Status Codes](#heat-pump-status-codes)

## Übersicht

Die ComfoClime API ist eine proprietäre JSON-basierte HTTP-API, die folgendes ermöglicht:

- **Lesezugriff**: Dashboard-Daten, Geräteinformationen, Telemetriewerte, Properties
- **Schreibzugriff**: Temperaturprofile, Lüfterstufen, Properties, System-Reset
- **Gerätesteuerung**: ComfoClime und alle verbundenen ComfoNet-Bus Geräte (z.B. ComfoAir Q)
- **Keine Authentifizierung**: Die API ist nur lokal verfügbar und erfordert keine Anmeldedaten

**Basis-URL**: `http://{IP_ADRESSE}` oder `http://comfoclime.local`

## Identifikatoren

### UUID (Universally Unique Identifier)

Die API verwendet UUIDs zur eindeutigen Identifikation von Geräten. Die UUID ist identisch mit der Seriennummer des Geräts (wie sie z.B. in der ComfoClime App angezeigt wird).

**Format**: Alphanumerische Zeichenkette (z.B. `MBE123123123`)

**Verwendung**:
- Wird beim ersten Verbindungsaufbau über `/monitoring/ping` abgerufen
- Erforderlich für alle `/system/{UUID}/*` Endpunkte
- Identifiziert das ComfoClime-Gerät eindeutig

### Device ID (modelTypeId)

Jedes Gerät am ComfoNet-Bus hat zusätzlich eine Device ID (`DEVID`, in der API als `modelTypeId` bezeichnet). Diese ID repräsentiert den Gerätetyp auf dem ComfoNet-Bus.

**Bekannte Device IDs**:
- `1`: ComfoAir Q 350/450/600
- `20`: ComfoClime 36
- `222`: ComfoHub

**Hinweis**: Einige Geräte (z.B. Option Box) haben keine Device ID; in diesem Fall ist `modelTypeId` `NULL`.

## API-Endpunkte Übersicht

| Endpunkt | Methode | Funktion | Zusätzliche Informationen |
|----------|---------|----------|---------------------------|
| `/monitoring/ping` | GET | UUID des Interfaces, Uptime, Zeitstempel | Wird beim ersten Verbindungsaufbau abgerufen |
| `/monitoring/health` | GET | Systemdaten über Speicher und RX/TX | Systemüberwachung |
| `/system/systems` | GET | Standort und Verbindung von ComfoClime | Systemkonfiguration |
| `/system/time` | GET | Aktuelle Zeit des Geräts | Zeitsynchronisation |
| `/wifi/list` | GET | WLAN-Verbindung des Geräts | Netzwerkinformationen |
| `/system/{UUID}/devices` | GET | Liste aller verbundenen Geräte | ComfoNet-Bus / CAN-Bus Geräte |
| `/system/{UUID}/dashboard` | GET/PUT | Dashboard-Daten der App | Temperaturen, Lüfterstufen, Status |
| `/system/{UUID}/alarms` | GET | Alle Fehler verbundener Geräte | Scheint Historie zu enthalten |
| `/system/{UUID}/scheduler` | GET | Liste der Zeitpläne | Programmierung |
| `/system/{UUID}/thermalprofile` | GET/PUT | Lesen/Setzen des Thermalprofils | Temperatureinstellungen |
| `/device/{UUID}/property/X/Y/Z` | GET | Lesen von Properties eines Geräts | Unit/Subunit/Property |
| `/device/{UUID}/telemetry/N` | GET | Lesen von Sensorwerten eines Geräts | N = Telemetrie-ID |
| `/device/{UUID}/definition` | GET | Grundlegende Gerätedaten | Geräteinformationen |
| `/device/{UUID}/method/X/Y/3` | PUT | Setzen von Properties eines Geräts | Schreibzugriff |
| `/system/reset` | PUT | Neustart des ComfoClime-Geräts | System-Reset |

### Endpunkt-Typen und UUIDs

**`/system/{UUID}/*` Endpunkte**: Diese Endpunkte funktionieren **nur** mit der UUID des ComfoClime-Geräts.

**`/device/{UUID}/*` Endpunkte**: Diese Endpunkte funktionieren sowohl mit der UUID des ComfoClime-Geräts als auch mit UUIDs anderer Geräte am ComfoNet-Bus (z.B. ComfoAir Q).

## Endpunkt-Dokumentation

### /monitoring/ping

Liefert die UUID des ComfoClime-Geräts sowie Uptime und Zeitstempel. Dieser Endpunkt wird beim ersten Verbindungsaufbau verwendet, um die UUID zu ermitteln.

#### Endpunkt

```http
GET /monitoring/ping
```

#### Curl-Beispiel

```bash
curl http://192.168.1.100/monitoring/ping
```

#### Beispiel-Response

```json
{
   "uuid": "MBE123123123",
   "uptime": 1234567,
   "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Felder

| Feldname | Typ | Beschreibung |
|----------|-----|--------------|
| `uuid` | String | UUID/Seriennummer des ComfoClime-Geräts |
| `uptime` | Integer | Betriebszeit in Sekunden seit letztem Neustart |
| `timestamp` | String | Aktueller Zeitstempel (ISO 8601) |

---

### /system/{UUID}/dashboard

Liest oder setzt Dashboard-Daten, die auch in der offiziellen ComfoClime App angezeigt werden. Enthält aktuelle Temperaturen, Lüfterstufen und Systemstatus.

#### Endpunkt

```http
GET /system/{UUID}/dashboard
PUT /system/{UUID}/dashboard
```

#### Curl-Beispiel (Lesen)

```bash
curl http://192.168.1.100/system/MBE123123123/dashboard
```

#### Curl-Beispiel (Schreiben)

```bash
curl -X PUT http://192.168.1.100/system/MBE123123123/dashboard \
  -H "Content-Type: application/json" \
  -d '{
    "@type": null,
    "name": null,
    "displayName": null,
    "description": null,
    "timestamp": "2024-01-15T10:30:00",
    "status": null,
    "setPointTemperature": null,
    "temperatureProfile": 0,
    "seasonProfile": null,
    "fanSpeed": 2,
    "scenario": null,
    "scenarioTimeLeft": null,
    "season": null,
    "schedule": null
  }'
```

#### Beispiel-Response (Auto-Modus)

Response von einem ComfoClime-Gerät mit Firmware-Version `1.5.5` und Temperaturwahl im `Auto`-Modus:

```json
{
   "indoorTemperature": 25.4,
   "outdoorTemperature": 27.8,
   "exhaustAirFlow": 485,
   "supplyAirFlow": 484,
   "fanSpeed": 2,
   "seasonProfile": 0,
   "temperatureProfile": 0,
   "season": 2,
   "schedule": 0,
   "status": 1,
   "heatPumpStatus": 5,
   "hpStandby": false,
   "freeCoolingEnabled": false,
   "caqFreeCoolingAvailable": true
}
```

#### Beispiel-Response (Manueller Modus)

Im manuellen Modus werden `setPointTemperature` anstelle von `seasonProfile` und `temperatureProfile` zurückgegeben:

```json
{
   "indoorTemperature": 23.5,
   "outdoorTemperature": 18.2,
   "exhaustAirFlow": 350,
   "supplyAirFlow": 345,
   "fanSpeed": 1,
   "setPointTemperature": 22.0,
   "season": 1,
   "schedule": 0,
   "status": 1,
   "heatPumpStatus": 3,
   "hpStandby": false,
   "freeCoolingEnabled": false,
   "caqFreeCoolingAvailable": false
}
```

#### Felder

| Feldname | Min. Firmware | Datentyp | Beschreibung |
|----------|---------------|----------|--------------|
| `indoorTemperature` | - | Float | Temperatur der Abluft aus dem Haus (°C) |
| `outdoorTemperature` | - | Float | Temperatur der Außenluft (°C) |
| `exhaustAirFlow` | - | Integer | Volumen der aus dem Haus ausgeblasenen Luft pro Zeiteinheit (m³/h) |
| `supplyAirFlow` | - | Integer | Volumen der ins Haus eingeblasenen Luft pro Zeiteinheit (m³/h) |
| `fanSpeed` | - | Integer | Lüfterstufe des ComfoAir-Geräts (0-3). Kann von ComfoClime überschrieben werden |
| `setPointTemperature` | - | Float | Manuell gewählte Temperatur (°C)<br/>**Hinweis**: Nur vorhanden im manuellen Modus. In diesem Fall fehlen `seasonProfile` und `temperatureProfile` |
| `seasonProfile` | - | Integer | Aktuelles Saisonprofil (nicht in ComfoClime App verfügbar)<br/>**Hinweis**: Nur vorhanden im Auto-Modus |
| `temperatureProfile` | - | Integer | Aktuelles Temperaturprofil<br/>- `0`: Comfort<br/>- `1`: Power<br/>- `2`: Eco<br/>**Hinweis**: Nur vorhanden im Auto-Modus |
| `season` | - | Integer | Aktuelle Saison<br/>- `0`: Übergang<br/>- `1`: Heizen<br/>- `2`: Kühlen |
| `schedule` | - | Integer | Aktuelle Zeitplan-ID |
| `status` | - | Integer | Status (Bedeutung unbekannt) |
| `heatPumpStatus` | - | Integer | Bitfeld mit Heat Pump Status (siehe [Heat Pump Status Codes](#heat-pump-status-codes)) |
| `hpStandby` | - | Boolean | Gerätestatus: aus (`true`) oder ein (`false`) |
| `freeCoolingEnabled` | 1.5.0 | Boolean | Aktueller "Free Cooling"-Status (Kühlung durch kalte Außenluft mit 100% Bypass statt aktiver Kühlung) |
| `caqFreeCoolingAvailable` | 1.5.5 | Boolean | Aktive (Wärmepumpen-) Kühlung wird durch "Free Cooling" unterstützt |

#### PUT-Request Hinweise

Beim Schreiben von Dashboard-Daten müssen **alle** Felder gesendet werden, nicht benötigte Felder auf `null` setzen:

- **temperatureProfile**: Setzt das Temperaturprofil (0=Comfort, 1=Power, 2=Eco)
- **fanSpeed**: Setzt die Lüfterstufe (0-3)
- **timestamp**: Aktueller Zeitstempel im ISO 8601 Format

---

### /system/{UUID}/devices

Liefert eine Liste aller am ComfoNet-Bus angeschlossenen Geräte, einschließlich ComfoClime, ComfoAir Q und anderen Komponenten.

#### Endpunkt

```http
GET /system/{UUID}/devices
```

#### Curl-Beispiel

```bash
curl http://192.168.1.100/system/MBE123123123/devices
```

#### Beispiel-Response

```json
{
   "devices": [
      {
         "uuid": "SIT123123123",
         "modelTypeId": 1,
         "variant": 3,
         "zoneId": 1,
         "@modelType": "ComfoAirQ 600",
         "name": "ComfoAirQ 600",
         "displayName": "ComfoAirQ 600",
         "fanSpeed": 2
      },
      {
         "uuid": "MBE123123123",
         "modelTypeId": 20,
         "variant": 0,
         "zoneId": 1,
         "@modelType": "ComfoClime 36",
         "name": "ComfoClime 36",
         "displayName": "ComfoClime 36",
         "version": "R1.5.0",
         "temperatureProfile": 0
      },
      {
         "uuid": "ENG123123123",
         "modelTypeId": 222,
         "variant": 0,
         "zoneId": 255,
         "@modelType": "ComfoHub",
         "name": "ComfoHub",
         "displayName": "ComfoHub"
      }
   ]
}
```

Das obige Beispiel stammt von einer Installation mit ComfoAir Q, ComfoClime und ComfoConnect Pro Geräten.

#### Felder

| Feldname | Datentyp | Beschreibung |
|----------|----------|--------------|
| `uuid` | String | UUID = Seriennummer des Geräts |
| `modelTypeId` | Integer | DEVID, repräsentiert den Gerätetyp auf dem ComfoNet-Bus |
| `variant` | Integer | Variante (Bedeutung unbekannt) |
| `zoneId` | Integer | Zonen-ID (Bedeutung unbekannt) |
| `@modelType` | String | Hersteller-Modelltyp |
| `name` | String | Hersteller-Modellname |
| `displayName` | String | Anzeigename des Modells |
| `fanSpeed` | Integer | Lüfterstufe (auch im Dashboard-Endpunkt verfügbar) |
| `version` | String | Firmware-Version (z.B. "R1.5.0") |
| `temperatureProfile` | Integer | Temperaturprofil (auch im Dashboard-Endpunkt verfügbar) |

---

### /system/{UUID}/thermalprofile

Liest oder setzt das thermische Profil des ComfoClime-Geräts. Dies umfasst Komforttemperaturen, Heizkurven-Kniepunkte und Schwellenwerte für Heiz- und Kühlbetrieb.

#### Endpunkt

```http
GET /system/{UUID}/thermalprofile
PUT /system/{UUID}/thermalprofile
```

#### Curl-Beispiel (Lesen)

```bash
curl http://192.168.1.100/system/MBE123123123/thermalprofile
```

#### Curl-Beispiel (Schreiben)

```bash
curl -X PUT http://192.168.1.100/system/MBE123123123/thermalprofile \
  -H "Content-Type: application/json" \
  -d '{
    "season": {
      "status": null,
      "season": null,
      "heatingThresholdTemperature": null,
      "coolingThresholdTemperature": null
    },
    "temperature": {
      "status": null,
      "manualTemperature": null
    },
    "temperatureProfile": null,
    "heatingThermalProfileSeasonData": {
      "comfortTemperature": 21.5,
      "kneePointTemperature": null,
      "reductionDeltaTemperature": null
    },
    "coolingThermalProfileSeasonData": {
      "comfortTemperature": null,
      "kneePointTemperature": null,
      "temperatureLimit": null
    }
  }'
```

#### Beispiel-Response

```json
{
   "season": {
      "status": 1,
      "season": 2,
      "heatingThresholdTemperature": 14.0,
      "coolingThresholdTemperature": 17.0
   },
   "temperature": {
      "status": 1,
      "manualTemperature": 26.0
   },
   "temperatureProfile": 0,
   "heatingThermalProfileSeasonData": {
      "comfortTemperature": 21.5,
      "kneePointTemperature": 12.5,
      "reductionDeltaTemperature": 1.5
   },
   "coolingThermalProfileSeasonData": {
      "comfortTemperature": 24.0,
      "kneePointTemperature": 18.0,
      "temperatureLimit": 26.0
   }
}
```

#### Felder

| Feldname | Datentyp | Beschreibung |
|----------|----------|--------------|
| `season.status` | Integer | Status (Bedeutung unbekannt) |
| `season.season` | Integer | Jahreszeit<br/>- `0`: Übergang<br/>- `1`: Heizen<br/>- `2`: Kühlen |
| `season.heatingThresholdTemperature` | Float | Heizschwelle (°C). Nicht verwendet bei automatischer Saisonwahl |
| `season.coolingThresholdTemperature` | Float | Kühlschwelle (°C). Nicht verwendet bei automatischer Saisonwahl |
| `temperature.status` | Integer | Status (Bedeutung unbekannt) |
| `temperature.manualTemperature` | Float | Manuelle Komforttemperatur (°C). Nicht verwendet bei Auto-Modus |
| `temperatureProfile` | Integer | Aktuelles Temperaturprofil (0=Comfort, 1=Power, 2=Eco) |
| `heatingThermalProfileSeasonData.comfortTemperature` | Float | Heiz-Komforttemperatur (°C) |
| `heatingThermalProfileSeasonData.kneePointTemperature` | Float | Kniepunkt der Heizkurve (°C) |
| `heatingThermalProfileSeasonData.reductionDeltaTemperature` | Float | Heiz-Reduktionsdelta (°C) |
| `coolingThermalProfileSeasonData.comfortTemperature` | Float | Kühl-Komforttemperatur (°C) |
| `coolingThermalProfileSeasonData.kneePointTemperature` | Float | Kniepunkt der Kühlkurve (°C) |
| `coolingThermalProfileSeasonData.temperatureLimit` | Float | Maximale Kühltemperatur (°C) |

#### PUT-Request Hinweise

Beim Schreiben von Thermal Profile Daten:

- Müssen **alle** Felder gesendet werden
- Nicht zu ändernde Felder auf `null` setzen
- Nur die zu ändernden Felder mit Werten füllen
- Die API führt ein Partial Update durch

---

### /system/{UUID}/alarms

Liefert eine Liste aller Fehler/Alarme/Benachrichtigungen für jedes am ComfoNet-Bus angeschlossene Gerät. Scheint eine Historie zu enthalten.

#### Endpunkt

```http
GET /system/{UUID}/alarms
```

#### Curl-Beispiel

```bash
curl http://192.168.1.100/system/MBE123123123/alarms
```

#### Beispiel-Response

```json
{
   "devices": [
      {
         "uuid": "SIT123123123",
         "modelTypeId": 1,
         "variant": 3,
         "zoneId": 1,
         "errors": [
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
         ]
      },
      {
         "uuid": "MBE123123123",
         "modelTypeId": 20,
         "variant": 0,
         "zoneId": 1,
         "errors": [
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
         ]
      }
   ]
}
```

#### Felder

Enthält eine Liste von Error-Codes für jedes Gerät. Die genaue Bedeutung der einzelnen Codes ist nicht dokumentiert.

---

### /device/{UUID}/property/{X}/{Y}/{Z}

Liest Properties (Eigenschaften) von Geräten über den ComfoNet-Bus. Die Adressierung erfolgt ähnlich zum RMI-Protokoll.

#### Endpunkt

```http
GET /device/{UUID}/property/{X}/{Y}/{Z}
```

**Parameter**:
- `X`: Unit (Einheit)
- `Y`: Subunit (Untereinheit)
- `Z`: Property (Eigenschaft)

#### Curl-Beispiel

```bash
# Seriennummer des ComfoAir-Geräts abrufen (Unit 1, Subunit 1, Property 4)
curl http://192.168.1.100/device/SIT123123123/property/1/1/4
```

#### Beispiel-Response

```json
{
   "data": [83, 73, 84, 49, 50, 51, 49, 50, 51, 49, 50, 51]
}
```

Die Daten werden als Byte-Array in dezimaler Darstellung zurückgegeben. Im obigen Beispiel repräsentiert das Array die ASCII-Codes für "SIT123123123".

#### Byte-Konvertierung

**1 Byte (UINT8)**:
- Wert: 0-255
- Signed: Bei Werten >= 128 wird 256 subtrahiert für negative Werte

**2 Bytes (UINT16)**:
- LSB (Least Significant Byte) zuerst, dann MSB (Most Significant Byte)
- Formel: `value = LSB + (MSB << 8)`
- Signed: Bei Werten >= 32768 wird 65536 subtrahiert

**String**:
- Jedes Byte repräsentiert einen ASCII-Character
- 0-Bytes werden als String-Ende interpretiert

**Faktor**:
- Viele Werte verwenden einen Faktor (z.B. 0.1 für Temperaturen)
- Der gelesene Wert muss mit dem Faktor multipliziert werden

---

### /device/{UUID}/telemetry/{N}

Liest Telemetriewerte (Sensordaten) von Geräten über den ComfoNet-Bus. Die Telemetrie-IDs entsprechen dem PDO-Protokoll.

#### Endpunkt

```http
GET /device/{UUID}/telemetry/{N}
```

**Parameter**:
- `N`: Telemetrie-ID (siehe [ComfoClime Sensoren](#comfoclime-sensoren-telemetrie))

#### Curl-Beispiel

```bash
# TPMA Temperatur abrufen (Telemetrie-ID 4145)
curl http://192.168.1.100/device/MBE123123123/telemetry/4145
```

#### Beispiel-Response

```json
{
   "data": [215, 0]
}
```

Die Daten werden als Byte-Array in dezimaler Darstellung zurückgegeben. Die Konvertierung erfolgt wie bei Properties:

```
LSB = 215, MSB = 0
Wert = 215 + (0 << 8) = 215
Mit Faktor 0.1: 215 * 0.1 = 21.5°C
```

---

### /device/{UUID}/method/{X}/{Y}/3

Schreibt Properties (Eigenschaften) zu Geräten über den ComfoNet-Bus. Unit und Subunit sind in der URL, die letzte Zahl ist immer `3` (repräsentiert eine Schreibanfrage).

#### Endpunkt

```http
PUT /device/{UUID}/method/{X}/{Y}/3
```

**Parameter**:
- `X`: Unit (Einheit)
- `Y`: Subunit (Untereinheit)
- `3`: Write Request (immer 3)

#### Curl-Beispiel

```bash
# Heizkurven-Kniepunkt auf 17°C setzen (Unit 22, Subunit 1, Property 4)
curl -X PUT http://192.168.1.100/device/MBE123123123/method/22/1/3 \
  -H "Content-Type: application/json" \
  -d '{"data": [4, 170, 0]}'
```

#### Request-Body

```json
{
   "data": [Z, LSB, MSB]
}
```

**Erklärung**:
- Erstes Byte: Property-ID (`Z`)
- Zweites Byte: LSB (Least Significant Byte) des Werts
- Drittes Byte: MSB (Most Significant Byte) des Werts (bei 2-Byte-Werten)

**Beispiel-Berechnung**:
```
Zielwert: 17°C
Property: 22/1/4 (Heizkurven-Kniepunkt)
Faktor: 0.1

Rohwert = 17 / 0.1 = 170
LSB = 170 & 0xFF = 170 (0xAA)
MSB = (170 >> 8) & 0xFF = 0

Data: [4, 170, 0]
```

---

### /system/reset

Startet das ComfoClime-Gerät neu.

#### Endpunkt

```http
PUT /system/reset
```

#### Curl-Beispiel

```bash
curl -X PUT http://192.168.1.100/system/reset
```

#### Response

```
HTTP 200 OK
```

**Hinweis**: Nach dem Reset ist das Gerät für einige Sekunden nicht erreichbar.

---

## ComfoClime Einheiten und Properties

ComfoClime-Geräte haben verschiedene Units (Einheiten) mit jeweils mehreren Subunits und Properties.

### Verfügbare Units

| DEC | HEX  | Subunit-Anzahl | Name | Verwendung |
|-----|------|----------------|------|------------|
| 1   | 0x01 | 1              | NODE | Allgemeine Geräteinformationen |
| 2   | 0x02 | 1              | COMFOBUS | Bus-Einheit |
| 3   | 0x03 | 1              | ERROROBJECT | Fehlerbehandlung |
| 21  | 0x15 | 2              | - | Unbekannt |
| 22  | 0x16 | 1              | TEMPCONFIG | Konfigurationsdaten (Saison, Temperaturwerte, etc.) |
| 23  | 0x17 | 1              | HEATPUMP | Wärmepumpen-Konfiguration |
| 25  | 0x19 | 1              | - | Unbekannt |
| 26  | 0x1A | 1              | - | Unbekannt |

### Properties der Subunits

#### NODE (Unit 1)

| Unit | Subunit | Property | Zugriff | Format | Beschreibung |
|------|---------|----------|---------|--------|--------------|
| 1    | 1       | 1        | RW      | UINT8  | Zone = 1 |
| 1    | 1       | 2        | RO      | UINT8  | ProductID = 20 (ComfoClime) |
| 1    | 1       | 3        | RO      | UINT8  | ProductVariant = 1 |
| 1    | 1       | 4        | RO      | STRING | Seriennummer (z.B. MBE...) |
| 1    | 1       | 5        | RO      | UINT8  | Hardware-Version = 1 |
| 1    | 1       | 6        | RO      | UINT8  | Firmware-Version |
| 1    | 1       | 7        | RO      | UINT32 | CNObjsVersion |
| 1    | 1       | 20       | RW      | STRING | Gerätename |

#### COMFOBUS (Unit 2)

| Unit | Subunit | Property | Zugriff | Format | Beschreibung |
|------|---------|----------|---------|--------|--------------|
| 2    | 1       | 1        | RO      | UINT8  | Zone = 1 |
| 2    | 1       | 2        | RO      | UINT8  | BusOffCount |
| 2    | 1       | 3        | RO      | UINT8  | CanReceiveErrorCount = 0 |
| 2    | 1       | 4        | RO      | UINT8  | CanTransmitErrorCount = 0 |

#### ERROROBJECT (Unit 3)

| Unit | Subunit | Property | Zugriff | Format | Beschreibung |
|------|---------|----------|---------|--------|--------------|
| 3    | 1       | 1        | RO      | UINT8  | Zone = 1 |

#### TEMPCONFIG (Unit 22)

Temperatur- und Saisonkonfiguration.

| Unit | Subunit | Property | Zugriff | Format | Faktor | Beschreibung |
|------|---------|----------|---------|--------|--------|--------------|
| 22   | 1       | 1        | RO      | UINT8  | 1      | Zone = 1 |
| 22   | 1       | 2        | RW      | UINT8  | 1      | Automatische Saisonwahl (0=Aus, 1=Ein) |
| 22   | 1       | 3        | RW      | UINT8  | 1      | Saisonwahl (0=Übergang, 1=Heizen, 2=Kühlen) |
| 22   | 1       | 4        | RW      | UINT16 | 0.1    | Heizkurven-Kniepunkt (°C) |
| 22   | 1       | 5        | RW      | UINT16 | 0.1    | Kühlkurven-Kniepunkt (°C) |
| 22   | 1       | 8        | RW      | UINT8  | 1      | Automatische Temperaturwahl (0=Aus, 1=Ein) |
| 22   | 1       | 9        | RW      | UINT16 | 0.1    | Komforttemperatur Heizen (°C) |
| 22   | 1       | 10       | RW      | UINT16 | 0.1    | Komforttemperatur Kühlen (°C) |
| 22   | 1       | 11       | RW      | UINT16 | 0.1    | Maximale Temperatur beim Kühlen (°C) |
| 22   | 1       | 12       | RW      | UINT16 | 0.1    | Heiz-Delta/Differenz (°C) |
| 22   | 1       | 13       | RW      | UINT16 | 0.1    | Zieltemperatur im manuellen Modus (°C) |
| 22   | 1       | 15       | RW      | UINT16 | 0.1    | Minimale Außentemperatur für Kühlung (°C) |
| 22   | 1       | 16       | RW      | UINT16 | 0.1    | Maximale Außentemperatur für Heizung (°C) |
| 22   | 1       | 17       | RW      | UINT16 | 0.1    | Maximale TPMA-Temperatur (°C) |
| 22   | 1       | 18       | RW      | UINT8  | 1      | Alpha TPMA = 70 |
| 22   | 1       | 29       | RW      | UINT8  | 1      | Temperaturprofil (0=Comfort, 1=Power, 2=Eco) |

#### HEATPUMP (Unit 23)

Wärmepumpen-Konfiguration.

| Unit | Subunit | Property | Zugriff | Format | Faktor | Beschreibung |
|------|---------|----------|---------|--------|--------|--------------|
| 23   | 1       | 2        | RW      | UINT16 | 0.1    | Temperatur = 30,0°C |
| 23   | 1       | 3        | RW      | UINT16 | 0.1    | Wärmepumpen-Maximaltemperatur (°C) |
| 23   | 1       | 4        | RW      | UINT16 | 0.1    | Wärmepumpen-Minimaltemperatur (°C) |
| 23   | 1       | 5        | RW      | UINT16 | 0.1    | Temperatur = 20,0°C |
| 23   | 1       | 6        | RW      | UINT16 | 0.1    | Temperatur = 5,0°C |
| 23   | 1       | 7        | RW      | UINT16 | 0.1    | Temperatur = 60,0°C |

**RO** = Read Only (Nur Lesen), **RW** = Read/Write (Lesen/Schreiben)

---

## ComfoClime Sensoren (Telemetrie)

ComfoClime-Geräte bieten verschiedene Telemetriewerte über den Telemetry-Endpunkt. Die wichtigsten sind:

### Dashboard-relevante Sensoren

| Telemetrie-ID | Format | Faktor | Beschreibung |
|---------------|--------|--------|--------------|
| 4145 | UINT16 | 0.1 | TPMA-Temperatur (°C) |
| 4148 | UINT16 | 0.1 | Zieltemperatur (°C) |
| 4149 | UINT8  | 1   | ComfoClime-Modus (0=Aus, 1=Heizen, 2=Kühlen) |
| 4151 | UINT16 | 0.1 | Aktuelle Heiz-Komforttemperatur (°C) |
| 4152 | UINT16 | 0.1 | Komforttemperatur minus Differenz (°C) |
| 4154 | UINT16 | 0.1 | Innentemperatur (°C) |

### Wärmepumpen-Sensoren

| Telemetrie-ID | Format | Faktor | Beschreibung |
|---------------|--------|--------|--------------|
| 4193 | UINT16 | 0.1 | Zuluft-Temperatur (°C) |
| 4194 | UINT16 | 0.1 | Abluft-Temperatur (°C) |
| 4195 | UINT16 | 0.1 | Zuluft-Spulen-Temperatur (°C) |
| 4196 | UINT16 | 0.1 | Abluft-Spulen-Temperatur (°C) |
| 4197 | UINT16 | 0.1 | Kompressor-Temperatur / Kompressor-Zieltemperatur (°C) |
| 4198 | UINT8  | 1   | Leistung % der Wärmepumpe (0-100) |
| 4201 | UINT16 | 1   | Aktuelle Leistung (W) |

### Druck- und Ventil-Sensoren

| Telemetrie-ID | Format | Beschreibung |
|---------------|--------|--------------|
| 4202 | UINT16 | Hochdruck / Heißseite |
| 4203 | UINT16 | Expansionsventil (Prozent: beim Start > 30%, stabilisiert sich bei 20-30%) |
| 4205 | UINT16 | Niederdruck / Kaltseite |
| 4207 | UINT16 | 4-Wege-Ventilposition |

**Hinweis**: Viele weitere Telemetrie-IDs sind verfügbar, aber noch nicht vollständig dokumentiert. Eine vollständige Liste findet sich im [Referenzdokument](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md).

---

## Heat Pump Status Codes

Das Feld `heatPumpStatus` im Dashboard-Endpunkt ist ein Bitfeld, das den Status der Wärmepumpe anzeigt.

### Beobachtete Status-Codes

| Code | Beschreibung | Binär |
|------|--------------|-------|
| 0    | Wärmepumpe ist aus | 0000 0000 |
| 1    | Startet | 0000 0001 |
| 3    | Heizen | 0000 0011 |
| 5    | Kühlen | 0000 0101 |
| 17   | Unbekannt | 0001 0001 |
| 19   | Möglicherweise Abtauen im Kühlmodus | 0001 0011 |
| 21   | Kühlen (an heißen Tagen) | 0001 0101 |
| 67   | Abtauzyklus Phase 1 | 0100 0011 |
| 75   | Abtauzyklus Phase 3 (aktives Abtauen) | 0100 1011 |
| 83   | Abtauzyklus Phase 2 | 0101 0011 |

### Bit-Interpretation (Vermutung)

Der Status-Wert scheint eine Bit-Matrix zu sein:

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|-----|---|---|---|---|---|---|---|---|
| **Wert** | 128 | 64 | 32 | 16 | 8 | 4 | 2 | 1 |
| **Bedeutung** | ? | Anti-Frost? | ? | ? | ? | Kühlen | Heizen | Läuft |

### Abtau-Zyklus

Beim Heizen im Winter wurde folgender Abtau-Zyklus beobachtet:

1. Status wechselt zu `67` für 60 Sekunden
2. Status wechselt zu `83` für 30 Sekunden
3. Status wechselt zurück zu `67` für 30 Sekunden
4. Status ist `75` für 8,5 Minuten (aktives Abtauen, Zulufttemperatur wird sehr kalt)
5. Status zurück zu `67` für 2 Minuten
6. Zurück zum Heizen für 30 Sekunden
7. Status `19` für 2 Minuten
8. Heizen wird fortgesetzt

### Hinweise

- Beim Heizen oder Kühlen startet die Wärmepumpe manchmal mit Status `1`
- Im Kühlmodus kann ein Gerät zwischen `0`, `5` und `21` wechseln
- An heißen Tagen läuft die Wärmepumpe meist im Status `21`
- Nach längerer Kühlzeit wechselt der Status kurzzeitig zu `19` (möglicherweise eine Art Abtauen, obwohl die Zuluftspule über 15°C hat)

**Hinweis**: Diese Interpretationen basieren auf Beobachtungen und sind nicht offiziell dokumentiert.

---

## Zusätzliche Hinweise

### Timeout-Einstellungen

- Standard-Timeout für API-Requests: 5 Sekunden
- Bei langsamen Netzwerken kann der Timeout erhöht werden

### Fehlerbehandlung

Die API gibt HTTP-Statuscodes zurück:

- `200 OK`: Erfolgreiche Anfrage
- `400 Bad Request`: Ungültige Anfrage (z.B. falsches JSON-Format)
- `404 Not Found`: Endpunkt oder Ressource nicht gefunden
- `500 Internal Server Error`: Interner Fehler des ComfoClime-Geräts

### Byte-Order

Alle Multi-Byte-Werte verwenden **Little-Endian** Byte-Order:
- Niederwertiges Byte (LSB) zuerst
- Höherwertiges Byte (MSB) danach

### Faktor-Konvertierung

Viele Werte (insbesondere Temperaturen) verwenden einen Faktor:

```
Angezeigter Wert = Rohwert * Faktor
Rohwert = Angezeigter Wert / Faktor
```

**Beispiel**: Temperatur 21.5°C mit Faktor 0.1
- Rohwert = 21.5 / 0.1 = 215
- Übertragung: `[215, 0]` (LSB=215, MSB=0)

### Signed vs. Unsigned

- **Unsigned**: Werte 0-255 (1 Byte) oder 0-65535 (2 Bytes)
- **Signed**: Negative Werte möglich durch Zweierkomplement
  - 1 Byte: Werte >= 128 → subtrahiere 256
  - 2 Bytes: Werte >= 32768 → subtrahiere 65536

---

## Integration in Home Assistant

Diese API wird von der [ComfoClime Custom Integration](https://github.com/Revilo91/comfoclime) für Home Assistant verwendet. Die Integration bietet:

- Automatische Geräteerkennung
- Sensor-Entities für alle Dashboard- und Telemetriewerte
- Number-Entities für Temperatureinstellungen
- Select-Entities für Temperaturprofile und Saison-Modi
- Fan-Entity für Lüftersteuerung
- Switch-Entities für verschiedene Funktionen
- Service-Calls für erweiterte Funktionen

Weitere Informationen finden Sie im [GitHub Repository der Integration](https://github.com/Revilo91/comfoclime).

---

## Weiterführende Ressourcen

- **Original API-Dokumentation** (Englisch): [ComfoClimeAPI.md](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)
- **ComfoConnect Protocol**: [aiocomfoconnect](https://github.com/michaelarnauts/aiocomfoconnect)
- **RMI Protocol**: [PROTOCOL-RMI.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md)
- **PDO Protocol**: [PROTOCOL-PDO.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md)

---

## Mitwirken

Haben Sie weitere Informationen über die API entdeckt? Beiträge sind willkommen!

- Neue Telemetrie-IDs oder Properties
- Bedeutung unbekannter Felder
- Zusätzliche Heat Pump Status Codes
- Fehlerberichte und Korrekturen

Bitte öffnen Sie ein Issue oder Pull Request im [GitHub Repository](https://github.com/Revilo91/comfoclime).

---

**Version**: 1.0  
**Stand**: Januar 2025  
**Lizenz**: MIT
