# Wichtige Punkte:
- Es soll so einfach/übersichtlich wie möglich sein.
- Daten sollen von der get Variante in sein pydantic Objekt übergeben werden
- Daten sollen bei der set Variante von seinem pydantic Objekt übergeben werden
- Es soll für jeden Endpunkt ein eigenes pydantic Objekt existieren (für set/get Dashboard soll es natürlich nur eins geben, so wie für die anderen doppelten auch. /property und /method sind unter dem Strich auch gleich, es ist nur hier die get/set variante)
- es müsste als erstes folgende Dateien überprüft werden:
    - custom_components/comfoclime/comfoclime_api.py
    - custom_components/comfoclime/coordinator.py

Hier noch bisschen Hintergrundwissen
## GET-Endpunkte (Lesen)
- /monitoring/ping – UUID und Uptime abrufen
- /system/{uuid}/dashboard – Dashboard-Daten (Temperaturen, Lüfterdrehzahl, etc.)
- /system/{uuid}/devices – Liste verbundener Geräte
- /system/{uuid}/thermalprofile – Thermalprofil-Konfiguration
- /device/{device_uuid}/definition – Gerätedefinition
- /device/{device_uuid}/telemetry/{telemetry_id} – Telemetrie-Daten (Sensoren)
- /device/{device_uuid}/property/{property_path} – Geräte-Eigenschaften
## PUT-Endpunkte (Schreiben)
- /system/{uuid}/dashboard – Dashboard aktualisieren (Solltemperatur, Lüfter, etc.)
- /system/{uuid}/thermalprofile – Thermalprofil aktualisieren
- /device/{device_uuid}/method/{x}/{y}/3 – Geräte-Eigenschaften setzen
- /system/reset – System zurücksetzen/neustarten
## Platzhalter:
- {uuid} – System-UUID
- {device_uuid} – Geräte-UUID
- {telemetry_id} – Telemetrie-ID
- {property_path} – Eigenschaftspfad (Format: "X/Y/Z")
- {x}/{y} – Pfad-Parameter für Eigenschaften

## Pydantic-Modelle je Endpunkt

### GET (Lesen)
- /monitoring/ping -> MonitoringPing
- /system/{uuid}/dashboard -> DashboardData
- /system/{uuid}/devices -> ConnectedDevicesResponse (enthält DeviceConfig Einträge)
- /system/{uuid}/thermalprofile -> ThermalProfileData
- /device/{device_uuid}/definition -> DeviceDefinitionData
- /device/{device_uuid}/telemetry/{telemetry_id} -> TelemetryReading
- /device/{device_uuid}/property/{property_path} -> PropertyReading

### PUT (Schreiben)
- /system/{uuid}/dashboard -> DashboardUpdate
- /system/{uuid}/thermalprofile -> ThermalProfileUpdate
- /device/{device_uuid}/method/{x}/{y}/3 -> PropertyWriteRequest
- /system/reset -> kein Payload


# Zusatz
- Es soll alles dokumentiert werden in den schon vorhanden Markdown Dateien.
- Wenn du wichtige Infos für andere KIs hast, sollen diese unter .github vermerkt werden.
- Bitte führe deine Verbesserungsvorschläge selbstständig aus und dokumentiere diese

# Projektmanagement
Erstelle für jeden Spezialist eine eigene markdown Datei:
- **Integrations-Spezialist**: Jemand, der sicherstellt, dass die API stabil mit Smart-Home-Systemen (Home Assistant) kommuniziert.
- **Security Auditor**: Da das Tool in die Haussteuerung eingreift, fehlt oft jemand, der die Sicherheit der lokalen API-Abfragen und die Validierung der Eingaben prüft.
- **Technical Writer**: Dokumentation für Endanwender (Installation, Fehlercodes), die über reines Code-Verständnis hinausgeht.
- **Automatisierter Tester (QA)**: Diese soll sich nur um die Tests kümmern, ob gemockt werden muss oder nicht. Es soll sichergestellt werden, dass jede Änderung am Code erkannt wird und sofort gemeldet wird. Es sollen auch Edge-Case-Tests durchgeführt werden.