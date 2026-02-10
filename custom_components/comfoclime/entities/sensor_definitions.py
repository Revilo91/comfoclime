"""Entity definitions for ComfoClime sensors using Pydantic models."""

from __future__ import annotations

from enum import Enum, auto

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from pydantic import BaseModel, Field


class SensorCategory(Enum):
    """Categories of sensors in the integration."""

    DASHBOARD = auto()
    THERMALPROFILE = auto()
    MONITORING = auto()
    TELEMETRY = auto()
    PROPERTY = auto()
    DEFINITION = auto()
    ACCESS_TRACKING = auto()


class SensorDefinition(BaseModel):
    """Definition of a sensor entity.

    Attributes:
        key: Unique identifier for the sensor in API responses or dict key.
        translation_key: Key for i18n translations.
        name: Display name for the sensor (fallback if translation missing).
        unit: Unit of measurement (e.g., "°C", "m³/h").
        device_class: Home Assistant device class.
        state_class: Home Assistant state class.
        entity_category: Entity category (None, diagnostic, config).
        icon: MDI icon name.
        suggested_display_precision: Decimal places for display.
    """

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    key: str = Field(..., description="Unique identifier for the sensor in API responses or dict key")
    translation_key: str = Field(..., description="Key for i18n translations")
    name: str = Field(..., description="Display name for the sensor (fallback if translation missing)")
    unit: str | None = Field(default=None, description="Unit of measurement (e.g., '°C', 'm³/h')")
    device_class: SensorDeviceClass | str | None = Field(default=None, description="Home Assistant device class")
    state_class: SensorStateClass | str | None = Field(default=None, description="Home Assistant state class")
    entity_category: EntityCategory | str | None = Field(
        default=None, description="Entity category (None, diagnostic, config)"
    )
    icon: str | None = Field(default=None, description="MDI icon name")
    suggested_display_precision: int | None = Field(default=None, description="Decimal places for display")


class TelemetrySensorDefinition(BaseModel):
    """Definition for telemetry-based sensors.

    Attributes:
        telemetry_id: ID for telemetry endpoint.
        name: Display name for the sensor (fallback if translation missing).
        translation_key: Key for i18n translations.
        faktor: Multiplication factor for the raw value.
        signed: Whether the value is signed.
        byte_count: Number of bytes to read from telemetry.
        unit: Unit of measurement (e.g., "°C", "m³/h").
        device_class: Home Assistant device class.
        state_class: Home Assistant state class.
        entity_category: Entity category (None, diagnostic, config).
        icon: MDI icon name.
        suggested_display_precision: Decimal places for display.
        diagnose: Whether this is a diagnostic sensor (experimental/unknown).
    """

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    telemetry_id: int = Field(..., description="ID for telemetry endpoint")
    name: str = Field(..., description="Display name for the sensor (fallback if translation missing)")
    translation_key: str = Field(..., description="Key for i18n translations")
    faktor: float = Field(default=1.0, description="Multiplication factor for the raw value")
    signed: bool = Field(default=False, description="Whether the value is signed")
    byte_count: int = Field(default=1, description="Number of bytes to read from telemetry")
    unit: str | None = Field(default=None, description="Unit of measurement (e.g., '°C', 'm³/h')")
    device_class: SensorDeviceClass | str | None = Field(default=None, description="Home Assistant device class")
    state_class: SensorStateClass | str | None = Field(default=None, description="Home Assistant state class")
    entity_category: EntityCategory | str | None = Field(
        default=None, description="Entity category (None, diagnostic, config)"
    )
    icon: str | None = Field(default=None, description="MDI icon name")
    suggested_display_precision: int | None = Field(default=None, description="Decimal places for display")
    diagnose: bool = Field(
        default=False,
        description="Whether this is a diagnostic sensor (experimental/unknown)",
    )


class PropertySensorDefinition(BaseModel):
    """Definition for property-based sensors.

    Attributes:
        path: Property path in format "X/Y/Z".
        name: Display name for the sensor (fallback if translation missing).
        translation_key: Key for i18n translations.
        faktor: Multiplication factor for the raw value.
        signed: Whether the value is signed.
        byte_count: Number of bytes to read from property.
        unit: Unit of measurement (e.g., "°C", "m³/h").
        device_class: Home Assistant device class.
        state_class: Home Assistant state class.
        entity_category: Entity category (None, diagnostic, config).
        icon: MDI icon name.
        suggested_display_precision: Decimal places for display.
    """

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    path: str = Field(..., description="Property path in format 'X/Y/Z'")
    name: str = Field(..., description="Display name for the sensor (fallback if translation missing)")
    translation_key: str = Field(..., description="Key for i18n translations")
    faktor: float = Field(default=1.0, description="Multiplication factor for the raw value")
    signed: bool = Field(default=False, description="Whether the value is signed")
    byte_count: int = Field(default=1, description="Number of bytes to read from property")
    unit: str | None = Field(default=None, description="Unit of measurement (e.g., '°C', 'm³/h')")
    device_class: SensorDeviceClass | str | None = Field(default=None, description="Home Assistant device class")
    state_class: SensorStateClass | str | None = Field(default=None, description="Home Assistant state class")
    entity_category: EntityCategory | str | None = Field(
        default=None, description="Entity category (None, diagnostic, config)"
    )
    icon: str | None = Field(default=None, description="MDI icon name")
    suggested_display_precision: int | None = Field(default=None, description="Decimal places for display")


class AccessTrackingSensorDefinition(BaseModel):
    """Definition for access tracking sensors.

    Attributes:
        coordinator: Name of the coordinator to track (None for total).
        metric: Metric type (per_minute, per_hour, total_per_minute, total_per_hour).
        name: Display name for the sensor (fallback if translation missing).
        translation_key: Key for i18n translations.
        state_class: Home Assistant state class.
        entity_category: Entity category (None, diagnostic, config).
        unit: Unit of measurement (e.g., "°C", "m³/h").
        device_class: Home Assistant device class.
        icon: MDI icon name.
        suggested_display_precision: Decimal places for display.
    """

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    coordinator: str | None = Field(..., description="Name of the coordinator to track (None for total)")
    metric: str = Field(
        ...,
        description="Metric type (per_minute, per_hour, total_per_minute, total_per_hour)",
    )
    name: str = Field(..., description="Display name for the sensor (fallback if translation missing)")
    translation_key: str = Field(..., description="Key for i18n translations")
    state_class: SensorStateClass | str | None = Field(default=None, description="Home Assistant state class")
    entity_category: EntityCategory | str | None = Field(
        default=None, description="Entity category (None, diagnostic, config)"
    )
    unit: str | None = Field(default=None, description="Unit of measurement (e.g., '°C', 'm³/h')")
    device_class: SensorDeviceClass | str | None = Field(default=None, description="Home Assistant device class")
    icon: str | None = Field(default=None, description="MDI icon name")
    suggested_display_precision: int | None = Field(default=None, description="Decimal places for display")


# Dashboard sensor definitions using Pydantic models
DASHBOARD_SENSORS = [
    SensorDefinition(
        key="indoorTemperature",
        name="Indoor Temperature",
        translation_key="indoor_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="outdoorTemperature",
        name="Outdoor Temperature",
        translation_key="outdoor_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="exhaustAirFlow",
        name="Exhaust Air Flow",
        translation_key="exhaust_air_flow",
        unit="m³/h",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="supplyAirFlow",
        name="Supply Air Flow",
        translation_key="supply_air_flow",
        unit="m³/h",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="fanSpeed",
        name="Fan Speed",
        translation_key="fan_speed",
        device_class=SensorDeviceClass.ENUM,
    ),
    SensorDefinition(
        key="temperatureProfile",
        name="Temperature Profile Status",
        translation_key="temperature_profile_status",
        device_class=SensorDeviceClass.ENUM,
    ),
    SensorDefinition(
        key="season",
        name="Season",
        translation_key="season",
        device_class=SensorDeviceClass.ENUM,
    ),
    SensorDefinition(
        key="schedule",
        name="Schedule",
        translation_key="schedule_status",
        entity_category="diagnostic",
    ),
    SensorDefinition(
        key="status",
        name="Status",
        translation_key="dashboard_status",
        entity_category="diagnostic",
    ),
    SensorDefinition(
        key="heatPumpStatus",
        name="Heat Pump Status",
        translation_key="heat_pump_status",
    ),
    SensorDefinition(
        key="hpStandby",
        name="Device Power Status",
        translation_key="device_power_status",
        entity_category="diagnostic",
    ),
    SensorDefinition(
        key="freeCoolingEnabled",
        name="Free Cooling Status",
        translation_key="free_cooling_status",
        entity_category="diagnostic",
    ),
    SensorDefinition(
        key="scenarioTimeLeft",
        name="Scenario Time Left",
        translation_key="scenario_time_left",
        unit="s",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="scenario",
        name="Scenario",
        translation_key="scenario",
        entity_category="diagnostic",
    ),
]

MONITORING_SENSORS = [
    SensorDefinition(
        key="uptime",
        name="Uptime",
        translation_key="uptime",
        unit="s",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
    ),
]

THERMALPROFILE_SENSORS = [
    SensorDefinition(
        key="season.status",
        name="Season Status",
        translation_key="thermal_season_status",
        entity_category="diagnostic",
    ),
    SensorDefinition(
        key="season.season",
        name="Season Mode",
        translation_key="thermal_season_mode",
        device_class=SensorDeviceClass.ENUM,
    ),
    SensorDefinition(
        key="season.heatingThresholdTemperature",
        name="Heating Threshold Temperature",
        translation_key="heating_threshold_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="season.coolingThresholdTemperature",
        name="Cooling Threshold Temperature",
        translation_key="cooling_threshold_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="temperature.status",
        name="Temperature Control Status",
        translation_key="thermal_temperature_status",
        entity_category="diagnostic",
    ),
    SensorDefinition(
        key="temperature.manualTemperature",
        name="Manual Temperature",
        translation_key="thermal_manual_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="temperatureProfile",
        name="Temperature Profile",
        translation_key="thermal_temperature_profile",
        device_class=SensorDeviceClass.ENUM,
    ),
    SensorDefinition(
        key="heatingThermalProfileSeasonData.comfortTemperature",
        name="Heating Comfort Temperature",
        translation_key="heating_comfort_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="heatingThermalProfileSeasonData.kneePointTemperature",
        name="Heating Knee Point Temperature",
        translation_key="heating_knee_point_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="heatingThermalProfileSeasonData.reductionDeltaTemperature",
        name="Heating Reduction Delta Temperature",
        translation_key="heating_reduction_delta_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="coolingThermalProfileSeasonData.comfortTemperature",
        name="Cooling Comfort Temperature",
        translation_key="cooling_comfort_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="coolingThermalProfileSeasonData.kneePointTemperature",
        name="Cooling Knee Point Temperature",
        translation_key="cooling_knee_point_temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDefinition(
        key="coolingThermalProfileSeasonData.temperatureLimit",
        name="Cooling Temperature Limit",
        translation_key="cooling_temperature_limit",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

TELEMETRY_SENSORS = []


CONNECTED_DEVICE_SENSORS = {
    20: [
        TelemetrySensorDefinition(
            name="Supply Air Temperature",
            translation_key="supply_air_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4193,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="TPMA Temperature",
            translation_key="tpma_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4145,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Device Mode",
            translation_key="device_mode_status",
            telemetry_id=4149,
            faktor=1.0,
        ),
        TelemetrySensorDefinition(
            name="Current Comfort Temperature",
            translation_key="current_comfort_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4151,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Exhaust Temperature",
            translation_key="comfoclime_exhaust_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4194,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Supply Coil Temperature",
            translation_key="supply_coil_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4195,
            faktor=0.1,
            signed=True,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Exhaust Coil Temperature",
            translation_key="exhaust_coil_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4196,
            faktor=0.1,
            signed=True,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Compressor Temperature",
            translation_key="compressor_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4197,
            faktor=0.1,
            signed=True,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Power Factor Heatpump",
            translation_key="powerfactor_heatpump",
            unit="%",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4198,
        ),
        TelemetrySensorDefinition(
            name="Power Heatpump",
            translation_key="power_heatpump",
            unit="W",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4201,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="High Pressure",
            translation_key="high_pressure",
            unit="kPa",
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4202,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Expansion Valve",
            translation_key="expansion_valve",
            unit="%",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4203,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Unknown value 4204",
            translation_key="unknown_value_4204",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4204,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Low Pressure",
            translation_key="low_pressure",
            unit="kPa",
            device_class=SensorDeviceClass.PRESSURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4205,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Unknown value 4206",
            translation_key="unknown_value_4206",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4206,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Four Way Valve Position",
            translation_key="four_way_valve_position",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4207,
            byte_count=2,
            diagnose=True,
        ),
        TelemetrySensorDefinition(
            name="Unknown value 4208",
            translation_key="unknown_value_4208",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=4208,
            byte_count=2,
            diagnose=True,
        ),
    ],
    1: [
        TelemetrySensorDefinition(
            name="Exhaust Fan Duty",
            translation_key="exhaust_fan_duty",
            unit="%",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=117,
        ),
        TelemetrySensorDefinition(
            name="Supply Fan Duty",
            translation_key="supply_fan_duty",
            unit="%",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=118,
        ),
        TelemetrySensorDefinition(
            name="Exhaust Fan Speed",
            translation_key="exhaust_fan_speed",
            unit="rpm",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=121,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Supply Fan Speed",
            translation_key="supply_fan_speed",
            unit="rpm",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=122,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Power Ventilation",
            translation_key="power_ventilation",
            unit="W",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=128,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Energy YTD",
            translation_key="energy_ytd",
            unit="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            telemetry_id=129,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Energy Total",
            translation_key="energy_total",
            unit="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            telemetry_id=130,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Mean outdoor temperature (RMOT)",
            translation_key="temp_rmot",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=209,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Bypass State",
            translation_key="bypass_state",
            unit="%",
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=227,
        ),
        TelemetrySensorDefinition(
            name="Exhaust Temperature",
            translation_key="exhaust_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=275,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Supply Temperature",
            translation_key="supply_air_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=278,
            faktor=0.1,
            signed=True,
            byte_count=2,
        ),
        TelemetrySensorDefinition(
            name="Extract Humidity",
            translation_key="extract_humidity",
            unit="%",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=290,
        ),
        TelemetrySensorDefinition(
            name="Exhaust Humidity",
            translation_key="exhaust_humidity",
            unit="%",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=291,
        ),
        TelemetrySensorDefinition(
            name="Outdoor Humidity",
            translation_key="outdoor_humidity",
            unit="%",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=292,
        ),
        TelemetrySensorDefinition(
            name="Supply Humidity",
            translation_key="supply_humidity",
            unit="%",
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            telemetry_id=294,
        ),
    ],
}

CONNECTED_DEVICE_PROPERTIES = {
    1: [
        PropertySensorDefinition(
            name="Ventilation Disbalance",
            translation_key="ventilation_disbalance",
            unit="%",
            path="30/1/18",
            faktor=0.1,
            byte_count=2,
        ),
    ],
}

# Definition-based sensors for ComfoAirQ devices (modelTypeId = 1)
# These are fetched from /device/{UUID}/definition endpoint
CONNECTED_DEVICE_DEFINITION_SENSORS = {
    1: [
        SensorDefinition(
            key="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SensorDefinition(
            key="outdoorTemperature",
            name="Outdoor Temperature",
            translation_key="outdoor_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SensorDefinition(
            key="extractTemperature",
            name="Extract Temperature",
            translation_key="extract_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SensorDefinition(
            key="supplyTemperature",
            name="Supply Temperature",
            translation_key="supply_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SensorDefinition(
            key="exhaustTemperature",
            name="Exhaust Temperature",
            translation_key="exhaust_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
    ],
}

# Access tracking sensors for monitoring API access patterns
# These sensors expose per-coordinator access counts
ACCESS_TRACKING_SENSORS = [
    # Per-coordinator per-minute sensors
    AccessTrackingSensorDefinition(
        name="Dashboard Accesses per Minute",
        translation_key="dashboard_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Dashboard",
        metric="per_minute",
    ),
    AccessTrackingSensorDefinition(
        name="Thermalprofile Accesses per Minute",
        translation_key="thermalprofile_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Thermalprofile",
        metric="per_minute",
    ),
    AccessTrackingSensorDefinition(
        name="Telemetry Accesses per Minute",
        translation_key="telemetry_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Telemetry",
        metric="per_minute",
    ),
    AccessTrackingSensorDefinition(
        name="Property Accesses per Minute",
        translation_key="property_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Property",
        metric="per_minute",
    ),
    AccessTrackingSensorDefinition(
        name="Definition Accesses per Minute",
        translation_key="definition_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Definition",
        metric="per_minute",
    ),
    AccessTrackingSensorDefinition(
        name="Monitoring Accesses per Minute",
        translation_key="monitoring_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Monitoring",
        metric="per_minute",
    ),
    # Per-coordinator per-hour sensors
    AccessTrackingSensorDefinition(
        name="Dashboard Accesses per Hour",
        translation_key="dashboard_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Dashboard",
        metric="per_hour",
    ),
    AccessTrackingSensorDefinition(
        name="Thermalprofile Accesses per Hour",
        translation_key="thermalprofile_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Thermalprofile",
        metric="per_hour",
    ),
    AccessTrackingSensorDefinition(
        name="Telemetry Accesses per Hour",
        translation_key="telemetry_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Telemetry",
        metric="per_hour",
    ),
    AccessTrackingSensorDefinition(
        name="Property Accesses per Hour",
        translation_key="property_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Property",
        metric="per_hour",
    ),
    AccessTrackingSensorDefinition(
        name="Definition Accesses per Hour",
        translation_key="definition_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Definition",
        metric="per_hour",
    ),
    AccessTrackingSensorDefinition(
        name="Monitoring Accesses per Hour",
        translation_key="monitoring_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator="Monitoring",
        metric="per_hour",
    ),
    # Total access sensors
    AccessTrackingSensorDefinition(
        name="Total API Accesses per Minute",
        translation_key="total_api_accesses_per_minute",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator=None,
        metric="total_per_minute",
    ),
    AccessTrackingSensorDefinition(
        name="Total API Accesses per Hour",
        translation_key="total_api_accesses_per_hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        coordinator=None,
        metric="total_per_hour",
    ),
]
