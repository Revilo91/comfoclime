"""Tests for sensor definitions in entities/sensor_definitions.py"""

from custom_components.comfoclime.entities.sensor_definitions import (
    CONNECTED_DEVICE_SENSORS,
)


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
        for model_id, sensor_defs in CONNECTED_DEVICE_SENSORS.items():
            for sensor_def in sensor_defs:
                # Check if this is a temperature sensor
                if sensor_def.device_class == "temperature" or sensor_def.unit == "°C":
                    # Most temperature sensors use faktor=0.1
                    assert sensor_def.faktor == 0.1, (
                        f"Temperature sensor '{sensor_def.name}' should use faktor=0.1"
                    )
                    # Temperature sensors should use 2 bytes for proper range
                    assert sensor_def.byte_count == 2, (
                        f"Temperature sensor '{sensor_def.name}' should use byte_count=2"
                    )

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

        assert tpma_sensor is not None, (
            "tpma_temperature sensor should exist in model 20"
        )
        assert tpma_sensor.telemetry_id == 4145, (
            "tpma_temperature should have telemetry_id 4145"
        )
        assert tpma_sensor.signed is True, "tpma_temperature must be signed"
        assert tpma_sensor.faktor == 0.1, "tpma_temperature should use faktor 0.1"
        assert tpma_sensor.byte_count == 2, "tpma_temperature should use byte_count 2"
        assert tpma_sensor.device_class == "temperature", (
            "tpma_temperature should have device_class temperature"
        )
        assert tpma_sensor.unit == "°C", "tpma_temperature should use °C unit"
