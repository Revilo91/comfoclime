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


class TestComfoClimeTelemetryByteCount:
    """Test that ComfoClime (modelTypeId=20) telemetry sensors have correct byte_count.

    Verified against upstream API documentation:
    https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md
    """

    def _get_sensor_by_id(self, telemetry_id: int):
        """Helper to find a sensor by telemetry ID in model 20."""
        model_20_sensors = CONNECTED_DEVICE_SENSORS.get(20, [])
        for sensor in model_20_sensors:
            if sensor.telemetry_id == telemetry_id:
                return sensor
        return None

    def test_4194_exhaust_temperature(self):
        """Telemetry 4194 = exhaust temperature (INT16, 2 bytes, signed, faktor=0.1)."""
        sensor = self._get_sensor_by_id(4194)
        assert sensor is not None, "Sensor 4194 should exist"
        assert sensor.translation_key == "comfoclime_exhaust_temperature"
        assert sensor.byte_count == 2
        assert sensor.signed is True
        assert sensor.faktor == 0.1
        assert sensor.unit == "°C"
        assert sensor.diagnose is False

    def test_4197_compressor_temperature(self):
        """Telemetry 4197 = compressor temperature (INT16, 2 bytes, signed, faktor=0.1)."""
        sensor = self._get_sensor_by_id(4197)
        assert sensor is not None, "Sensor 4197 should exist"
        assert sensor.translation_key == "compressor_temperature"
        assert sensor.byte_count == 2
        assert sensor.signed is True
        assert sensor.faktor == 0.1
        assert sensor.unit == "°C"

    def test_4201_power_heatpump(self):
        """Telemetry 4201 = current power (UINT16, 2 bytes, unsigned)."""
        sensor = self._get_sensor_by_id(4201)
        assert sensor is not None, "Sensor 4201 should exist"
        assert sensor.translation_key == "power_heatpump"
        assert sensor.byte_count == 2
        assert sensor.unit == "W"

    def test_4202_high_pressure(self):
        """Telemetry 4202 = high pressure / hot side (2 bytes)."""
        sensor = self._get_sensor_by_id(4202)
        assert sensor is not None, "Sensor 4202 should exist"
        assert sensor.translation_key == "high_pressure"
        assert sensor.byte_count == 2
        assert sensor.unit == "kPa"
        assert sensor.diagnose is True

    def test_4203_expansion_valve(self):
        """Telemetry 4203 = expansion valve (2 bytes)."""
        sensor = self._get_sensor_by_id(4203)
        assert sensor is not None, "Sensor 4203 should exist"
        assert sensor.translation_key == "expansion_valve"
        assert sensor.byte_count == 2
        assert sensor.diagnose is True

    def test_4205_low_pressure(self):
        """Telemetry 4205 = low pressure / cold side (2 bytes)."""
        sensor = self._get_sensor_by_id(4205)
        assert sensor is not None, "Sensor 4205 should exist"
        assert sensor.translation_key == "low_pressure"
        assert sensor.byte_count == 2
        assert sensor.unit == "kPa"
        assert sensor.diagnose is True

    def test_4207_four_way_valve(self):
        """Telemetry 4207 = 4-way valve position (2 bytes)."""
        sensor = self._get_sensor_by_id(4207)
        assert sensor is not None, "Sensor 4207 should exist"
        assert sensor.translation_key == "four_way_valve_position"
        assert sensor.byte_count == 2
        assert sensor.diagnose is True

    def test_all_2byte_sensors_have_correct_byte_count(self):
        """Verify all sensors that should be 2 bytes are correctly set.

        Per upstream API docs, these telemetry IDs return 2-byte values:
        4145, 4148, 4151, 4154, 4193, 4194, 4195, 4196, 4197, 4201,
        4202, 4203, 4204, 4205, 4206, 4207, 4208
        """
        two_byte_ids = {
            4145,
            4148,
            4151,
            4154,
            4193,
            4194,
            4195,
            4196,
            4197,
            4201,
            4202,
            4203,
            4204,
            4205,
            4206,
            4207,
            4208,
        }
        model_20_sensors = CONNECTED_DEVICE_SENSORS.get(20, [])
        found_ids = {sensor.telemetry_id for sensor in model_20_sensors}
        missing_ids = two_byte_ids - found_ids
        assert not missing_ids, (
            f"The following expected telemetry IDs are missing from model 20 sensors: {sorted(missing_ids)}"
        )
        for sensor in model_20_sensors:
            if sensor.telemetry_id in two_byte_ids:
                assert sensor.byte_count == 2, (
                    f"Sensor '{sensor.name}' (telemetry_id={sensor.telemetry_id}) "
                    f"should have byte_count=2 per API documentation, got {sensor.byte_count}"
                )

    def test_1byte_sensors_have_correct_byte_count(self):
        """Verify 1-byte sensors are correctly set.

        Per upstream API docs, these telemetry IDs return 1-byte values:
        4149 (UINT8), 4198 (UINT8)
        """
        one_byte_ids = {4149, 4198}
        model_20_sensors = CONNECTED_DEVICE_SENSORS.get(20, [])
        for sensor in model_20_sensors:
            if sensor.telemetry_id in one_byte_ids:
                assert sensor.byte_count == 1, (
                    f"Sensor '{sensor.name}' (telemetry_id={sensor.telemetry_id}) "
                    f"should have byte_count=1 per API documentation, got {sensor.byte_count}"
                )


class TestComfoAirTelemetryByteCount:
    """Test that ComfoAir (modelTypeId=1) telemetry sensors have correct byte_count.

    Verified against PDO protocol documentation:
    https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md
    """

    def _get_sensor_by_id(self, telemetry_id: int):
        """Helper to find a sensor by telemetry ID in model 1."""
        model_1_sensors = CONNECTED_DEVICE_SENSORS.get(1, [])
        for sensor in model_1_sensors:
            if sensor.telemetry_id == telemetry_id:
                return sensor
        return None

    def test_121_exhaust_fan_speed(self):
        """PDO 121 = Exhaust fan speed (CN_UINT16, 2 bytes)."""
        sensor = self._get_sensor_by_id(121)
        assert sensor is not None, "Sensor 121 should exist"
        assert sensor.byte_count == 2
        assert sensor.unit == "rpm"

    def test_122_supply_fan_speed(self):
        """PDO 122 = Supply fan speed (CN_UINT16, 2 bytes)."""
        sensor = self._get_sensor_by_id(122)
        assert sensor is not None, "Sensor 122 should exist"
        assert sensor.byte_count == 2
        assert sensor.unit == "rpm"

    def test_128_power_ventilation(self):
        """PDO 128 = Current ventilation power (CN_UINT16, 2 bytes)."""
        sensor = self._get_sensor_by_id(128)
        assert sensor is not None, "Sensor 128 should exist"
        assert sensor.byte_count == 2
        assert sensor.unit == "W"

    def test_129_energy_ytd(self):
        """PDO 129 = Energy year-to-date (CN_UINT16, 2 bytes)."""
        sensor = self._get_sensor_by_id(129)
        assert sensor is not None, "Sensor 129 should exist"
        assert sensor.byte_count == 2
        assert sensor.unit == "kWh"

    def test_130_energy_total(self):
        """PDO 130 = Energy total (CN_UINT16, 2 bytes)."""
        sensor = self._get_sensor_by_id(130)
        assert sensor is not None, "Sensor 130 should exist"
        assert sensor.byte_count == 2
        assert sensor.unit == "kWh"

    def test_117_118_fan_duty_are_1byte(self):
        """PDO 117/118 = Fan duty (CN_UINT8, 1 byte)."""
        for tid in [117, 118]:
            sensor = self._get_sensor_by_id(tid)
            assert sensor is not None, f"Sensor {tid} should exist"
            assert sensor.byte_count == 1, f"Sensor {tid} ({sensor.name}) should be 1 byte (CN_UINT8)"

    def test_209_rmot(self):
        """PDO 209 = RMOT (CN_INT16, 2 bytes, signed, faktor=0.1)."""
        sensor = self._get_sensor_by_id(209)
        assert sensor is not None, "Sensor 209 should exist"
        assert sensor.byte_count == 2
        assert sensor.signed is True
        assert sensor.faktor == 0.1

    def test_227_bypass_state(self):
        """PDO 227 = Bypass state (CN_UINT8, 1 byte)."""
        sensor = self._get_sensor_by_id(227)
        assert sensor is not None, "Sensor 227 should exist"
        assert sensor.byte_count == 1

    def test_275_278_temperatures(self):
        """PDO 275/278 = Temperatures (CN_INT16, 2 bytes, signed, faktor=0.1)."""
        for tid in [275, 278]:
            sensor = self._get_sensor_by_id(tid)
            assert sensor is not None, f"Sensor {tid} should exist"
            assert sensor.byte_count == 2
            assert sensor.signed is True
            assert sensor.faktor == 0.1

    def test_290_294_humidity_are_1byte(self):
        """PDO 290-294 = Humidity (CN_UINT8, 1 byte)."""
        for tid in [290, 291, 292, 294]:
            sensor = self._get_sensor_by_id(tid)
            assert sensor is not None, f"Sensor {tid} should exist"
            assert sensor.byte_count == 1
            assert sensor.unit == "%"

    def test_all_2byte_sensors(self):
        """Verify all ComfoAir sensors that should be 2 bytes per PDO protocol."""
        two_byte_ids = {121, 122, 128, 129, 130, 209, 275, 278}
        model_1_sensors = CONNECTED_DEVICE_SENSORS.get(1, [])
        for sensor in model_1_sensors:
            if sensor.telemetry_id in two_byte_ids:
                assert sensor.byte_count == 2, (
                    f"Sensor '{sensor.name}' (telemetry_id={sensor.telemetry_id}) "
                    f"should have byte_count=2 per PDO protocol, got {sensor.byte_count}"
                )
