# AI Notes

- API GET methods return Pydantic models (e.g. `DashboardData`, `ThermalProfileData`, `MonitoringPing`, `DeviceDefinitionData`).
- /system/{uuid}/devices returns `ConnectedDevicesResponse`; use `.devices` for the list.
- PUT property writes use `PropertyWriteRequest` (device_uuid, path, value, byte_count, signed, faktor).
- Coordinators now propagate Pydantic models for monitoring, thermal profile, and definition data.
- Definition payloads vary by device; `DeviceDefinitionData` allows extra fields and exposes common temperatures via snake_case fields.
