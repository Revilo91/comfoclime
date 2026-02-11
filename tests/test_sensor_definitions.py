"""Tests for sensor definitions in entities/sensor_definitions.py"""

from custom_components.comfoclime.entities.sensor_definitions import (
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    THERMALPROFILE_SENSORS,
)
from custom_components.comfoclime.models import DashboardData, ThermalProfileData


class TestTelemetrySensorDefinitions:
    """Test TelemetrySensor definitions for correctness."""

    def test_all_temperature_sensors_are_signed(self):
        """Test that all temperature telemetry sensors have signed=True.

        This is critical for correctly displaying negative temperatures.
        Temperatures can go below 0°C and must be interpreted as signed integers.
        """
        for model_id, sensor_defs in CONNECTED_DEVICE_SENSORS.items():
            for sensor_def in sensor_defs:
                # Check if this is a temperature sensor
                if (
                    sensor_def.device_class == "temperature"
                    or sensor_def.unit == "°C"
                    or "temperature" in sensor_def.translation_key.lower()
                    or "temp" in sensor_def.translation_key.lower()
                ):
                    assert sensor_def.signed is True, (
                        f"Temperature sensor '{sensor_def.name}' (telemetry_id={sensor_def.telemetry_id}) "
                        f"in model {model_id} must have signed=True to correctly handle negative temperatures"
                    )

    def test_temperature_sensors_have_proper_scaling(self):
        """Test that temperature sensors have proper faktor and byte_count."""
        for _model_id, sensor_defs in CONNECTED_DEVICE_SENSORS.items():
            for sensor_def in sensor_defs:
                # Check if this is a temperature sensor
                if sensor_def.device_class == "temperature" or sensor_def.unit == "°C":
                    # Most temperature sensors use faktor=0.1
                    assert sensor_def.faktor == 0.1, f"Temperature sensor '{sensor_def.name}' should use faktor=0.1"
                    # Temperature sensors should use 2 bytes for proper range
                    assert sensor_def.byte_count == 2, f"Temperature sensor '{sensor_def.name}' should use byte_count=2"

    def test_tpma_temperature_sensor_configuration(self):
        """Test that tpma_temperature sensor is correctly configured.

        This is the specific sensor mentioned in the issue.
        """
        # tpma_temperature is in model 20
        model_20_sensors = CONNECTED_DEVICE_SENSORS.get(20)
        assert model_20_sensors is not None, "Model 20 sensors should exist"

        # Find tpma_temperature sensor
        tpma_sensor = None
        for sensor_def in model_20_sensors:
            if sensor_def.translation_key == "tpma_temperature":
                tpma_sensor = sensor_def
                break

        assert tpma_sensor is not None, "tpma_temperature sensor should exist in model 20"
        assert tpma_sensor.telemetry_id == 4145, "tpma_temperature should have telemetry_id 4145"
        assert tpma_sensor.signed is True, "tpma_temperature must be signed"
        assert tpma_sensor.faktor == 0.1, "tpma_temperature should use faktor 0.1"
        assert tpma_sensor.byte_count == 2, "tpma_temperature should use byte_count 2"
        assert tpma_sensor.device_class == "temperature", "tpma_temperature should have device_class temperature"
        assert tpma_sensor.unit == "°C", "tpma_temperature should use °C unit"


class TestDashboardSensorDefinitions:
    """Test Dashboard sensor definitions for correctness and consistency with model."""

    def test_dashboard_sensors_count(self):
        """Test that we have the expected number of dashboard sensors."""
        # We now have 17 sensors (added 3 new ones)
        assert len(DASHBOARD_SENSORS) == 17, "Dashboard should have 17 sensor definitions"

    def test_dashboard_sensors_match_model_fields(self):
        """Test that all dashboard sensor keys correspond to DashboardData model fields."""
        # Get all field names/aliases from DashboardData model
        model_fields = set()
        for field_name, field_info in DashboardData.model_fields.items():
            # Add the alias if it exists (camelCase from API)
            if hasattr(field_info, "alias") and field_info.alias:
                model_fields.add(field_info.alias)
            else:
                model_fields.add(field_name)

        # Check that all sensor keys exist in the model
        for sensor_def in DASHBOARD_SENSORS:
            assert sensor_def.key in model_fields, (
                f"Sensor key '{sensor_def.key}' not found in DashboardData model. "
                f"Available fields: {sorted(model_fields)}"
            )

    def test_new_dashboard_sensors_added(self):
        """Test that the 3 previously missing sensors are now defined."""
        sensor_keys = {s.key for s in DASHBOARD_SENSORS}

        # setPointTemperature - manual mode target temperature
        assert "setPointTemperature" in sensor_keys, "setPointTemperature sensor should be defined"

        # seasonProfile - season profile selection
        assert "seasonProfile" in sensor_keys, "seasonProfile sensor should be defined"

        # caqFreeCoolingAvailable - ComfoAirQ free cooling availability
        assert "caqFreeCoolingAvailable" in sensor_keys, "caqFreeCoolingAvailable sensor should be defined"

    def test_dashboard_sensors_have_required_metadata(self):
        """Test that all dashboard sensors have required metadata fields."""
        for sensor_def in DASHBOARD_SENSORS:
            # All sensors must have these basic fields
            assert sensor_def.key, f"Sensor must have a key"
            assert sensor_def.name, f"Sensor {sensor_def.key} must have a name"
            assert sensor_def.translation_key, f"Sensor {sensor_def.key} must have a translation_key"

            # Temperature sensors should have proper metadata
            if sensor_def.unit == "°C":
                assert (
                    sensor_def.device_class == "temperature"
                ), f"Temperature sensor {sensor_def.key} should have device_class='temperature'"
                assert (
                    sensor_def.state_class == "measurement"
                ), f"Temperature sensor {sensor_def.key} should have state_class='measurement'"


class TestThermalProfileSensorDefinitions:
    """Test Thermal Profile sensor definitions for correctness and consistency with model."""

    def test_thermalprofile_sensors_count(self):
        """Test that we have the expected number of thermal profile sensors."""
        # 12 sensors defined
        assert len(THERMALPROFILE_SENSORS) == 12, "Thermal profile should have 12 sensor definitions"

    def test_thermalprofile_sensors_have_valid_keys(self):
        """Test that all thermal profile sensor keys use valid nested notation."""
        for sensor_def in THERMALPROFILE_SENSORS:
            # Thermal profile sensors use nested keys like "season.status"
            assert "." in sensor_def.key or sensor_def.key == "temperatureProfile", (
                f"Thermal profile sensor {sensor_def.key} should use nested notation "
                f"(e.g., 'season.status') or be 'temperatureProfile'"
            )

    def test_thermalprofile_temperature_sensors_have_proper_metadata(self):
        """Test that temperature sensors in thermal profile have proper metadata."""
        for sensor_def in THERMALPROFILE_SENSORS:
            if sensor_def.unit == "°C":
                assert (
                    sensor_def.device_class == "temperature"
                ), f"Temperature sensor {sensor_def.key} should have device_class='temperature'"
                assert (
                    sensor_def.state_class == "measurement"
                ), f"Temperature sensor {sensor_def.key} should have state_class='measurement'"
