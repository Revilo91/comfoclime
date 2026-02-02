"""Integration tests using real or recorded ComfoClime device data.

These tests use real data from a ComfoClime device, either:
- Live from the network (--real-device)
- From previously recorded responses (default, offline mode)

To record responses first:
    python tests/record_device_responses.py --ip 10.0.2.27

Or via pytest:
    pytest tests/test_real_device_integration.py --record-responses --device-ip=10.0.2.27

Then run tests offline:
    pytest tests/test_real_device_integration.py -v
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from custom_components.comfoclime.climate import ComfoClimeClimate

# Import fixtures - these are used by pytest even though they appear "unused"
from tests.conftest_real_device import (  # noqa: F401
    RESPONSES_DIR,
    real_or_recorded_api,
)


class TestRealDeviceAPI:
    """Test API calls against real or recorded device data."""

    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, real_or_recorded_api):
        """Test fetching dashboard data."""
        data = await real_or_recorded_api.async_get_dashboard_data()

        assert data is not None
        assert isinstance(data, dict)
        print(f"\n📊 Dashboard Data: {data}")

        # Check for some expected fields (may vary by device)
        possible_fields = [
            "indoorTemperature",
            "outdoorTemperature",
            "fanSpeed",
            "season",
            "hpStandby",
        ]
        found_fields = [f for f in possible_fields if f in data]
        print(f"   Found fields: {found_fields}")

    @pytest.mark.asyncio
    async def test_get_thermal_profile(self, real_or_recorded_api):
        """Test fetching thermal profile."""
        data = await real_or_recorded_api.async_get_thermal_profile()

        assert data is not None
        assert isinstance(data, dict)
        print(f"\n🌡️  Thermal Profile: {data}")

    @pytest.mark.asyncio
    async def test_get_connected_devices(self, real_or_recorded_api):
        """Test fetching connected devices."""
        devices = await real_or_recorded_api.async_get_connected_devices()

        assert devices is not None
        assert isinstance(devices, list)
        print(f"\n🔌 Connected Devices ({len(devices)}):")
        for dev in devices:
            print(
                f"   - {dev.get('displayName', 'Unknown')}: {dev.get('@modelType', 'N/A')}"
            )

    @pytest.mark.asyncio
    async def test_get_monitoring_ping(self, real_or_recorded_api):
        """Test fetching monitoring ping data."""
        data = await real_or_recorded_api.async_get_monitoring_ping()

        assert data is not None
        assert isinstance(data, dict)
        assert "uuid" in data
        print(f"\n📡 Monitoring Ping: {data}")

    @pytest.mark.asyncio
    async def test_get_device_definition(self, real_or_recorded_api):
        """Test fetching device definitions for all connected devices."""
        devices = await real_or_recorded_api.async_get_connected_devices()

        print(f"\n📋 Device Definitions:")
        for device in devices:
            dev_uuid = device.get("uuid")
            if not dev_uuid:
                continue

            definition = await real_or_recorded_api.async_get_device_definition(
                dev_uuid
            )
            print(f"   {device.get('displayName', dev_uuid)}:")
            print(f"      Keys: {list(definition.keys()) if definition else 'None'}")

    @pytest.mark.asyncio
    async def test_read_telemetry(self, real_or_recorded_api):
        """Test reading telemetry values from devices."""
        devices = await real_or_recorded_api.async_get_connected_devices()

        print("\n📈 Telemetry Readings:")
        for device in devices:
            dev_uuid = device.get("uuid")
            if not dev_uuid:
                continue

            print(f"   {device.get('displayName', dev_uuid)}:")

            # Try a few common telemetry IDs
            test_ids = [0, 1, 2, 4145, 4146, 4201]
            for tel_id in test_ids:
                value = await real_or_recorded_api.async_read_telemetry_for_device(
                    dev_uuid, tel_id, faktor=0.1, signed=True
                )
                if value is not None:
                    print(f"      Telemetry {tel_id}: {value}")

    @pytest.mark.asyncio
    async def test_read_property(self, real_or_recorded_api):
        """Test reading property values from devices."""
        devices = await real_or_recorded_api.async_get_connected_devices()

        print("\n⚙️ Property Readings:")
        for device in devices:
            dev_uuid = device.get("uuid")
            if not dev_uuid:
                continue

            print(f"   {device.get('displayName', dev_uuid)}:")

            # Try a few common property paths
            test_paths = ["1/1/1", "1/1/2", "29/1/6", "29/1/10"]
            for path in test_paths:
                value = await real_or_recorded_api.async_read_property_for_device(
                    dev_uuid, path, faktor=1.0, signed=True
                )
                if value is not None:
                    print(f"      Property {path}: {value}")


class TestRealDeviceClimateEntity:
    """Test climate entity with real device data."""

    @pytest_asyncio.fixture
    async def climate_with_real_data(self, real_or_recorded_api, mock_config_entry):
        """Create a climate entity using real/recorded data."""
        # Fetch data
        dashboard_data = await real_or_recorded_api.async_get_dashboard_data()
        thermal_data = await real_or_recorded_api.async_get_thermal_profile()

        # Create mock coordinators with real data
        dashboard_coordinator = MagicMock()
        dashboard_coordinator.data = dashboard_data
        dashboard_coordinator.last_update_success = True
        dashboard_coordinator.async_request_refresh = AsyncMock()
        dashboard_coordinator.async_add_listener = MagicMock(return_value=lambda: None)

        thermal_coordinator = MagicMock()
        thermal_coordinator.data = thermal_data
        thermal_coordinator.last_update_success = True
        thermal_coordinator.async_request_refresh = AsyncMock()
        thermal_coordinator.async_add_listener = MagicMock(return_value=lambda: None)

        # Create device info
        device = {
            "uuid": real_or_recorded_api.uuid,
            "displayName": "ComfoClime (Real Data)",
            "@modelType": "ComfoClime",
            "version": "1.0",
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=dashboard_coordinator,
            thermalprofile_coordinator=thermal_coordinator,
            api=real_or_recorded_api,
            device=device,
            entry=mock_config_entry,
        )

        return climate

    @pytest.mark.asyncio
    async def test_climate_entity_with_real_data(self, climate_with_real_data):
        """Test that climate entity works with real data."""
        climate = climate_with_real_data

        print(f"\n🏠 Climate Entity with Real Data:")
        print(f"   Current Temperature: {climate.current_temperature}")
        print(f"   Target Temperature: {climate.target_temperature}")
        print(f"   HVAC Mode: {climate.hvac_mode}")
        print(f"   HVAC Action: {climate.hvac_action}")
        print(f"   Fan Mode: {climate.fan_mode}")
        print(f"   Preset Mode: {climate.preset_mode}")
        print(f"   Available: {climate.available}")

        # Entity should be available
        assert climate.available is True

    @pytest.mark.asyncio
    async def test_climate_temperature_values(self, climate_with_real_data):
        """Test that temperature values are in reasonable range."""
        climate = climate_with_real_data

        if climate.current_temperature is not None:
            # Temperature should be in reasonable range (0-50°C)
            assert 0 <= climate.current_temperature <= 50, (
                f"Current temperature {climate.current_temperature} out of range"
            )

        if climate.target_temperature is not None:
            # Target should be in allowed range
            assert climate.min_temp <= climate.target_temperature <= climate.max_temp


class TestDataIntegrity:
    """Tests to verify data integrity between API and entities."""

    @pytest.mark.asyncio
    async def test_dashboard_data_structure(self, real_or_recorded_api):
        """Verify dashboard data has expected structure."""
        data = await real_or_recorded_api.async_get_dashboard_data()

        # Document the actual structure
        print("\n📋 Dashboard Data Structure:")
        for key, value in data.items():
            print(f"   {key}: {type(value).__name__} = {value}")

    @pytest.mark.asyncio
    async def test_thermal_profile_structure(self, real_or_recorded_api):
        """Verify thermal profile data has expected structure."""
        data = await real_or_recorded_api.async_get_thermal_profile()

        print("\n📋 Thermal Profile Structure:")
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for k, v in value.items():
                    print(f"      {k}: {type(v).__name__} = {v}")
            else:
                print(f"   {key}: {type(value).__name__} = {value}")


# ============================================================================
# Conditional Tests - Only run with real device
# ============================================================================


@pytest.mark.skipif(
    not RESPONSES_DIR.exists() or not any(RESPONSES_DIR.glob("*.json")),
    reason="No recorded responses available. Run record_device_responses.py first.",
)
class TestWithRecordedData:
    """Tests that require recorded data to be present."""

    @pytest.mark.asyncio
    async def test_recorded_data_available(self, real_or_recorded_api):
        """Verify recorded data is available and usable."""
        data = await real_or_recorded_api.async_get_dashboard_data()
        assert data, "Dashboard data should not be empty"

    @pytest.mark.asyncio
    async def test_all_api_endpoints(self, real_or_recorded_api):
        """Test all main API endpoints with recorded data."""
        results = {
            "dashboard": await real_or_recorded_api.async_get_dashboard_data(),
            "thermal_profile": await real_or_recorded_api.async_get_thermal_profile(),
            "connected_devices": await real_or_recorded_api.async_get_connected_devices(),
        }

        print("\n📊 API Endpoint Results:")
        for endpoint, data in results.items():
            status = "✅" if data else "❌"
            print(f"   {status} {endpoint}: {len(str(data))} chars")
