"""Tests for ComfoClime coordinators."""

from unittest.mock import AsyncMock

import aiohttp
import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.comfoclime.coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from custom_components.comfoclime.models import (
    DashboardData,
    DeviceDefinitionData,
    MonitoringPing,
    PropertyReading,
    TelemetryReading,
    ThermalProfileData,
)


@pytest.mark.asyncio
async def test_telemetry_coordinator_concurrent_registration(hass_with_frame_helper, mock_api):
    """Test that TelemetryCoordinator handles concurrent registrations during update."""
    coordinator = ComfoClimeTelemetryCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Register initial telemetry
    await coordinator.register_telemetry(
        device_uuid="device1",
        telemetry_id="123",
        faktor=0.1,
        signed=False,
        byte_count=2,
    )

    # Mock API to register another telemetry during the update
    async def mock_read_telemetry(*args, **kwargs):
        # Simulate concurrent registration while update is running
        await coordinator.register_telemetry(
            device_uuid="device2",
            telemetry_id="456",
            faktor=1.0,
            signed=True,
            byte_count=2,
        )
        # Return a TelemetryReading model
        return TelemetryReading(
            device_uuid=args[0] if args else kwargs["device_uuid"],
            telemetry_id=args[1] if len(args) > 1 else kwargs["telemetry_id"],
            raw_value=255,
            faktor=kwargs.get("faktor", 0.1),
            signed=kwargs.get("signed", False),
            byte_count=kwargs.get("byte_count", 2),
        )

    mock_api.async_read_telemetry_for_device = AsyncMock(side_effect=mock_read_telemetry)

    # This should not raise RuntimeError: dictionary changed size during iteration
    result = await coordinator._async_update_data()

    assert result is not None
    assert "device1" in result
    assert result["device1"]["123"] == 25.5  # 255 * 0.1 = 25.5


@pytest.mark.asyncio
async def test_property_coordinator_concurrent_registration(hass_with_frame_helper, mock_api):
    """Test that PropertyCoordinator handles concurrent registrations during update."""
    coordinator = ComfoClimePropertyCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Register initial property
    await coordinator.register_property(
        device_uuid="device1",
        property_path="29/1/10",
        faktor=1.0,
        signed=True,
        byte_count=2,
    )

    # Mock API to register another property during the update
    async def mock_read_property(*args, **kwargs):
        # Simulate concurrent registration while update is running
        await coordinator.register_property(
            device_uuid="device2",
            property_path="29/1/6",
            faktor=1.0,
            signed=True,
            byte_count=2,
        )
        # Return a PropertyReading model
        return PropertyReading(
            device_uuid=args[0] if args else kwargs["device_uuid"],
            path=args[1] if len(args) > 1 else kwargs["property_path"],
            raw_value=100,
            faktor=kwargs.get("faktor", 1.0),
            signed=kwargs.get("signed", True),
            byte_count=kwargs.get("byte_count", 2),
        )

    mock_api.async_read_property_for_device = AsyncMock(side_effect=mock_read_property)

    # This should not raise RuntimeError: dictionary changed size during iteration
    result = await coordinator._async_update_data()

    assert result is not None
    assert "device1" in result
    assert result["device1"]["29/1/10"] == 100.0


@pytest.mark.asyncio
async def test_telemetry_coordinator_multiple_devices(hass_with_frame_helper, mock_api):
    """Test TelemetryCoordinator with multiple devices and telemetry values."""
    coordinator = ComfoClimeTelemetryCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Register multiple telemetries for multiple devices
    await coordinator.register_telemetry(
        device_uuid="device1", telemetry_id="123", faktor=1.0, signed=False, byte_count=2
    )
    await coordinator.register_telemetry(
        device_uuid="device1", telemetry_id="456", faktor=2.0, signed=False, byte_count=2
    )
    await coordinator.register_telemetry(
        device_uuid="device2",
        telemetry_id="100",
        faktor=1.0,
        signed=False,
        byte_count=1,
    )

    # Mock API responses - return values that fit within the byte count
    async def mock_read_telemetry(device_uuid, telemetry_id, **kwargs):
        # Return a TelemetryReading model with realistic raw values
        raw_values = {"123": 123, "456": 456, "100": 100}
        return TelemetryReading(
            device_uuid=device_uuid,
            telemetry_id=telemetry_id,
            raw_value=raw_values.get(telemetry_id, 0),
            faktor=kwargs.get("faktor", 1.0),
            signed=kwargs.get("signed", False),
            byte_count=kwargs.get("byte_count", 2),
        )

    mock_api.async_read_telemetry_for_device = AsyncMock(side_effect=mock_read_telemetry)

    result = await coordinator._async_update_data()

    assert result is not None
    assert "device1" in result
    assert "device2" in result
    # Values are scaled by faktor (1.0 and 2.0 respectively)
    assert result["device1"]["123"] == 123.0  # 123 * 1.0
    assert result["device1"]["456"] == 912.0  # 456 * 2.0
    assert result["device2"]["100"] == 100.0  # 100 * 1.0 (fits in 1 byte)


@pytest.mark.asyncio
async def test_property_coordinator_multiple_devices(hass_with_frame_helper, mock_api):
    """Test PropertyCoordinator with multiple devices and property values."""
    coordinator = ComfoClimePropertyCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Register multiple properties for multiple devices
    await coordinator.register_property(
        device_uuid="device1",
        property_path="29/1/10",
        faktor=1.0,
        signed=True,
        byte_count=2,
    )
    await coordinator.register_property(
        device_uuid="device1",
        property_path="29/1/6",
        faktor=1.0,
        signed=True,
        byte_count=1,
    )
    await coordinator.register_property(
        device_uuid="device2",
        property_path="30/2/5",
        faktor=0.1,
        signed=False,
        byte_count=2,
    )

    # Mock API responses
    async def mock_read_property(device_uuid, property_path, **kwargs):
        # Return a PropertyReading model
        return PropertyReading(
            device_uuid=device_uuid,
            path=property_path,
            raw_value=len(property_path) * 10,
            faktor=kwargs.get("faktor", 1.0),
            signed=kwargs.get("signed", True),
            byte_count=kwargs.get("byte_count", 2),
        )

    mock_api.async_read_property_for_device = AsyncMock(side_effect=mock_read_property)

    result = await coordinator._async_update_data()

    assert result is not None
    assert "device1" in result
    assert "device2" in result
    # len("29/1/10") * 10 * 1.0 = 7 * 10 * 1.0 = 70.0
    assert result["device1"]["29/1/10"] == 70.0
    # len("29/1/6") * 10 * 1.0 = 6 * 10 * 1.0 = 60.0
    assert result["device1"]["29/1/6"] == 60.0
    # len("30/2/5") * 10 * 0.1 = 6 * 10 * 0.1 = 6.0
    assert result["device2"]["30/2/5"] == 6.0


@pytest.mark.asyncio
async def test_telemetry_coordinator_error_handling(hass_with_frame_helper, mock_api):
    """Test TelemetryCoordinator handles errors gracefully."""
    coordinator = ComfoClimeTelemetryCoordinator(hass_with_frame_helper, mock_api, devices=[])

    await coordinator.register_telemetry(
        device_uuid="device1", telemetry_id="123", faktor=1.0, signed=True, byte_count=2
    )
    await coordinator.register_telemetry(
        device_uuid="device1", telemetry_id="456", faktor=1.0, signed=True, byte_count=2
    )

    # Mock API to fail for specific telemetry
    async def mock_read_telemetry(device_uuid, telemetry_id, **kwargs):
        if telemetry_id == "456":
            raise aiohttp.ClientError("Test error")
        # Return a TelemetryReading model
        return TelemetryReading(
            device_uuid=device_uuid,
            telemetry_id=telemetry_id,
            raw_value=255,
            faktor=kwargs.get("faktor", 1.0),
            signed=kwargs.get("signed", False),
            byte_count=kwargs.get("byte_count", 2),
        )

    mock_api.async_read_telemetry_for_device = AsyncMock(side_effect=mock_read_telemetry)

    result = await coordinator._async_update_data()

    assert result is not None
    assert "device1" in result
    assert result["device1"]["123"] == 255.0
    assert result["device1"]["456"] is None


@pytest.mark.asyncio
async def test_property_coordinator_error_handling(hass_with_frame_helper, mock_api):
    """Test PropertyCoordinator handles errors gracefully."""
    coordinator = ComfoClimePropertyCoordinator(hass_with_frame_helper, mock_api, devices=[])

    await coordinator.register_property(
        device_uuid="device1",
        property_path="29/1/10",
        faktor=1.0,
        signed=True,
        byte_count=2,
    )
    await coordinator.register_property(
        device_uuid="device1",
        property_path="29/1/6",
        faktor=1.0,
        signed=True,
        byte_count=1,
    )

    # Mock API to fail for specific property
    async def mock_read_property(device_uuid, property_path, **kwargs):
        if property_path == "29/1/6":
            raise aiohttp.ClientError("Test error")
        # Return a PropertyReading model
        return PropertyReading(
            device_uuid=device_uuid,
            path=property_path,
            raw_value=100,
            faktor=kwargs.get("faktor", 1.0),
            signed=kwargs.get("signed", True),
            byte_count=kwargs.get("byte_count", 2),
        )

    mock_api.async_read_property_for_device = AsyncMock(side_effect=mock_read_property)

    result = await coordinator._async_update_data()

    assert result is not None
    assert "device1" in result
    assert result["device1"]["29/1/10"] == 100.0
    assert result["device1"]["29/1/6"] is None


@pytest.mark.asyncio
async def test_telemetry_coordinator_get_value(hass_with_frame_helper, mock_api):
    """Test TelemetryCoordinator get_telemetry_value method."""
    coordinator = ComfoClimeTelemetryCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Test with no data
    assert coordinator.get_telemetry_value("device1", "123") is None

    # Set data
    coordinator.data = {
        "device1": {"123": 25.5, "456": 30.0},
        "device2": {"789": 15.0},
    }

    # Test retrieval
    assert coordinator.get_telemetry_value("device1", "123") == 25.5
    assert coordinator.get_telemetry_value("device1", 456) == 30.0  # Test int conversion
    assert coordinator.get_telemetry_value("device2", "789") == 15.0
    assert coordinator.get_telemetry_value("device1", "999") is None
    assert coordinator.get_telemetry_value("device3", "123") is None


@pytest.mark.asyncio
async def test_property_coordinator_get_value(hass_with_frame_helper, mock_api):
    """Test PropertyCoordinator get_property_value method."""
    coordinator = ComfoClimePropertyCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Test with no data
    assert coordinator.get_property_value("device1", "29/1/10") is None

    # Set data
    coordinator.data = {
        "device1": {"29/1/10": 100, "29/1/6": 1},
        "device2": {"30/2/5": 50},
    }

    # Test retrieval
    assert coordinator.get_property_value("device1", "29/1/10") == 100
    assert coordinator.get_property_value("device1", "29/1/6") == 1
    assert coordinator.get_property_value("device2", "30/2/5") == 50
    assert coordinator.get_property_value("device1", "99/9/9") is None
    assert coordinator.get_property_value("device3", "29/1/10") is None


@pytest.mark.asyncio
async def test_dashboard_coordinator(hass_with_frame_helper, mock_api):
    """Test DashboardCoordinator basic functionality."""

    coordinator = ComfoClimeDashboardCoordinator(hass_with_frame_helper, mock_api)

    mock_dashboard_data = DashboardData(
        indoor_temperature=22.5,
        outdoor_temperature=15.0,
        fan_speed=2,
    )
    mock_api.async_get_dashboard_data = AsyncMock(return_value=mock_dashboard_data)

    result = await coordinator._async_update_data()

    assert result == mock_dashboard_data
    mock_api.async_get_dashboard_data.assert_called_once()


@pytest.mark.asyncio
async def test_dashboard_coordinator_error(hass_with_frame_helper, mock_api):
    """Test DashboardCoordinator error handling."""
    coordinator = ComfoClimeDashboardCoordinator(hass_with_frame_helper, mock_api)

    mock_api.async_get_dashboard_data = AsyncMock(side_effect=aiohttp.ClientError("Test error"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_thermalprofile_coordinator(hass_with_frame_helper, mock_api):
    """Test ThermalprofileCoordinator basic functionality."""
    coordinator = ComfoClimeThermalprofileCoordinator(hass_with_frame_helper, mock_api)

    mock_thermal_data = ThermalProfileData(
        temperature={"status": 0, "manualTemperature": 22.0},
        season={"status": 0},
    )
    mock_api.async_get_thermal_profile = AsyncMock(return_value=mock_thermal_data)

    result = await coordinator._async_update_data()

    assert result == mock_thermal_data
    mock_api.async_get_thermal_profile.assert_called_once()


@pytest.mark.asyncio
async def test_thermalprofile_coordinator_error(hass_with_frame_helper, mock_api):
    """Test ThermalprofileCoordinator error handling."""
    coordinator = ComfoClimeThermalprofileCoordinator(hass_with_frame_helper, mock_api)

    mock_api.async_get_thermal_profile = AsyncMock(side_effect=aiohttp.ClientError("Test error"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_definition_coordinator(hass_with_frame_helper, mock_api):
    """Test DefinitionCoordinator basic functionality."""
    devices = [
        {"uuid": "device1", "modelTypeId": 1},  # ComfoAirQ - should fetch
        {"uuid": "device2", "modelTypeId": 20},  # ComfoClime - should skip
    ]
    coordinator = ComfoClimeDefinitionCoordinator(hass_with_frame_helper, mock_api, devices=devices)

    mock_definition_data = DeviceDefinitionData(name="ComfoAir Q350", version="2.0")
    mock_api.async_get_device_definition = AsyncMock(return_value=mock_definition_data)

    result = await coordinator._async_update_data()

    # Should only fetch for ComfoAirQ device
    assert "device1" in result
    assert result["device1"] == mock_definition_data
    assert "device2" not in result
    mock_api.async_get_device_definition.assert_called_once_with(device_uuid="device1")


@pytest.mark.asyncio
async def test_definition_coordinator_get_value(hass_with_frame_helper, mock_api):
    """Test DefinitionCoordinator get_definition_data method."""
    coordinator = ComfoClimeDefinitionCoordinator(hass_with_frame_helper, mock_api, devices=[])

    # Test with no data
    assert coordinator.get_definition_data("device1") is None

    # Set data
    coordinator.data = {
        "device1": DeviceDefinitionData(name="Device 1"),
        "device2": None,
    }

    # Test retrieval
    assert coordinator.get_definition_data("device1").name == "Device 1"
    assert coordinator.get_definition_data("device2") is None
    assert coordinator.get_definition_data("device3") is None


@pytest.mark.asyncio
async def test_dashboard_coordinator_custom_interval(hass_with_frame_helper, mock_api):
    """Test dashboard coordinator with custom polling interval."""
    custom_interval = 120
    coordinator = ComfoClimeDashboardCoordinator(hass_with_frame_helper, mock_api, polling_interval=custom_interval)

    assert coordinator.update_interval.total_seconds() == custom_interval
    assert coordinator.api == mock_api


@pytest.mark.asyncio
async def test_thermalprofile_coordinator_custom_interval(hass_with_frame_helper, mock_api):
    """Test thermal profile coordinator with custom polling interval."""
    custom_interval = 90
    coordinator = ComfoClimeThermalprofileCoordinator(
        hass_with_frame_helper, mock_api, polling_interval=custom_interval
    )

    assert coordinator.update_interval.total_seconds() == custom_interval
    assert coordinator.api == mock_api


@pytest.mark.asyncio
async def test_telemetry_coordinator_custom_interval(hass_with_frame_helper, mock_api):
    """Test telemetry coordinator with custom polling interval."""
    custom_interval = 45
    devices = [{"uuid": "device-1", "modelTypeId": 20}]
    coordinator = ComfoClimeTelemetryCoordinator(
        hass_with_frame_helper, mock_api, devices, polling_interval=custom_interval
    )

    assert coordinator.update_interval.total_seconds() == custom_interval
    assert coordinator.api == mock_api
    assert coordinator.devices == devices


@pytest.mark.asyncio
async def test_property_coordinator_custom_interval(hass_with_frame_helper, mock_api):
    """Test property coordinator with custom polling interval."""
    custom_interval = 75
    devices = [{"uuid": "device-1", "modelTypeId": 20}]
    coordinator = ComfoClimePropertyCoordinator(
        hass_with_frame_helper, mock_api, devices, polling_interval=custom_interval
    )

    assert coordinator.update_interval.total_seconds() == custom_interval
    assert coordinator.api == mock_api
    assert coordinator.devices == devices


@pytest.mark.asyncio
async def test_definition_coordinator_custom_interval(hass_with_frame_helper, mock_api):
    """Test definition coordinator with custom polling interval."""
    custom_interval = 150
    devices = [{"uuid": "device-1", "modelTypeId": 1}]
    coordinator = ComfoClimeDefinitionCoordinator(
        hass_with_frame_helper, mock_api, devices, polling_interval=custom_interval
    )

    assert coordinator.update_interval.total_seconds() == custom_interval
    assert coordinator.api == mock_api
    assert coordinator.devices == devices


@pytest.mark.asyncio
async def test_monitoring_coordinator_success(hass_with_frame_helper, mock_api):
    """Test monitoring coordinator successful data fetch."""
    mock_api.async_get_monitoring_ping = AsyncMock(
        return_value=MonitoringPing(
            uuid="test-uuid",
            up_time_seconds=123456,
            timestamp=1705314600,
        )
    )

    coordinator = ComfoClimeMonitoringCoordinator(hass_with_frame_helper, mock_api)
    result = await coordinator._async_update_data()

    assert result.uuid == "test-uuid"
    assert result.up_time_seconds == 123456
    assert result.timestamp == 1705314600
    mock_api.async_get_monitoring_ping.assert_called_once()


@pytest.mark.asyncio
async def test_monitoring_coordinator_failure(hass_with_frame_helper, mock_api):
    """Test monitoring coordinator handles API errors."""
    mock_api.async_get_monitoring_ping = AsyncMock(side_effect=aiohttp.ClientError("Connection error"))

    coordinator = ComfoClimeMonitoringCoordinator(hass_with_frame_helper, mock_api)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_monitoring_coordinator_custom_interval(hass_with_frame_helper, mock_api):
    """Test monitoring coordinator with custom polling interval."""
    custom_interval = 120
    coordinator = ComfoClimeMonitoringCoordinator(hass_with_frame_helper, mock_api, polling_interval=custom_interval)

    assert coordinator.update_interval.total_seconds() == custom_interval
    assert coordinator.api == mock_api
