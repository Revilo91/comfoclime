#!/usr/bin/env python3
"""Test script for ComfoClime API integration."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

# Mock Home Assistant modules
import sys
from unittest.mock import MagicMock

# Create mock modules
mock_homeassistant = MagicMock()
mock_homeassistant.components.climate = MagicMock()
mock_homeassistant.config_entries = MagicMock()
mock_homeassistant.const = MagicMock()
mock_homeassistant.core = MagicMock()
mock_homeassistant.helpers = MagicMock()
mock_homeassistant.helpers.entity_platform = MagicMock()
mock_homeassistant.helpers.update_coordinator = MagicMock()

# Add mock constants
mock_homeassistant.const.ATTR_TEMPERATURE = "temperature"
mock_homeassistant.const.UnitOfTemperature = MagicMock()
mock_homeassistant.const.UnitOfTemperature.CELSIUS = "°C"

# Climate constants
mock_homeassistant.components.climate.ClimateEntity = MagicMock
mock_homeassistant.components.climate.ClimateEntityFeature = MagicMock()
mock_homeassistant.components.climate.ClimateEntityFeature.TARGET_TEMPERATURE = 1
mock_homeassistant.components.climate.ClimateEntityFeature.PRESET_MODE = 2
mock_homeassistant.components.climate.HVACMode = MagicMock()
mock_homeassistant.components.climate.HVACMode.OFF = "off"
mock_homeassistant.components.climate.HVACMode.HEAT = "heat"
mock_homeassistant.components.climate.HVACMode.COOL = "cool"
mock_homeassistant.components.climate.HVACMode.FAN_ONLY = "fan_only"

# Update coordinator
mock_homeassistant.helpers.update_coordinator.CoordinatorEntity = MagicMock

# Add to sys.modules
sys.modules['homeassistant'] = mock_homeassistant
sys.modules['homeassistant.components'] = mock_homeassistant.components
sys.modules['homeassistant.components.climate'] = mock_homeassistant.components.climate
sys.modules['homeassistant.config_entries'] = mock_homeassistant.config_entries
sys.modules['homeassistant.const'] = mock_homeassistant.const
sys.modules['homeassistant.core'] = mock_homeassistant.core
sys.modules['homeassistant.helpers'] = mock_homeassistant.helpers
sys.modules['homeassistant.helpers.entity_platform'] = mock_homeassistant.helpers.entity_platform
sys.modules['homeassistant.helpers.update_coordinator'] = mock_homeassistant.helpers.update_coordinator


async def test_climate_functionality():
    """Test the ComfoClime climate entity functionality."""

    # Mock the API and coordinator
    mock_api = AsyncMock()
    mock_api.uuid = "test-device-uuid"
    mock_api.set_property = AsyncMock()

    mock_coordinator = MagicMock()
    mock_coordinator.data = {
        "sensors": {
            "Temperature": {"value": 21.5},
            "Target Temperature": {"value": 22.0},
            "Season": {"value": "Heating"},
        }
    }

    # Mock Home Assistant and entry
    mock_hass = MagicMock()
    mock_hass.data = {
        "comfoclime": {
            "test_entry": {
                "main_device": {"uuid": "test-device-uuid"}
            }
        }
    }

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"

    # Import the climate module after mocking
    from custom_components.comfoclime.climate import ComfoClimeClimate

    # Create climate entity
    climate_entity = ComfoClimeClimate(
        hass=mock_hass,
        entry=mock_entry,
        api=mock_api,
        coordinator=mock_coordinator,
        device_info={"name": "Test ComfoClime"}
    )

    print("✓ ComfoClime Climate Entity created successfully")

    # Test properties
    assert climate_entity.name == "Test ComfoClime"
    assert climate_entity.temperature_unit == "°C"
    assert climate_entity.target_temperature_step == 0.1
    print(f"✓ Current temperature: {climate_entity.current_temperature}")
    print(f"✓ Target temperature: {climate_entity.target_temperature}")
    print(f"✓ HVAC mode: {climate_entity.hvac_mode}")
    print(f"✓ Preset mode: {climate_entity.preset_mode}")

    # Test temperature setting
    print("\n--- Testing Temperature Setting ---")
    await climate_entity.async_set_temperature(temperature=23.5)

    # Check API calls
    assert mock_api.set_property.called
    call_args = mock_api.set_property.call_args_list
    print(f"✓ API calls made: {len(call_args)}")

    for i, call in enumerate(call_args):
        args, kwargs = call
        print(f"  Call {i+1}: device={args[0]}, property={args[1]}, value={args[2]}")

    # Test HVAC mode setting
    print("\n--- Testing HVAC Mode Setting ---")
    mock_api.set_property.reset_mock()
    await climate_entity.async_set_hvac_mode("heat")

    call_args = mock_api.set_property.call_args_list
    print(f"✓ API calls made: {len(call_args)}")

    for i, call in enumerate(call_args):
        args, kwargs = call
        print(f"  Call {i+1}: device={args[0]}, property={args[1]}, value={args[2]}")

    # Test preset mode setting
    print("\n--- Testing Preset Mode Setting ---")
    mock_api.set_property.reset_mock()
    await climate_entity.async_set_preset_mode("eco")

    call_args = mock_api.set_property.call_args_list
    print(f"✓ API calls made: {len(call_args)}")

    for i, call in enumerate(call_args):
        args, kwargs = call
        print(f"  Call {i+1}: device={args[0]}, property={args[1]}, value={args[2]}")

    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_climate_functionality())
