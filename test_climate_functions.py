#!/usr/bin/env python3
"""
Test script for ComfoClime Climate entity functions.
This script demonstrates how to test the key climate control functions.
"""

import asyncio
import json
import sys


# Mock Home Assistant classes for testing
class MockHass:
    def __init__(self):
        self.data = {}

    async def async_add_executor_job(self, func, *args):
        """Mock executor job - calls function directly."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args)
        else:
            return func(*args)

class MockCoordinator:
    def __init__(self, data=None):
        self.data = data or {}

    async def async_request_refresh(self):
        """Mock refresh."""
        print("🔄 Coordinator refreshed")

# Example test data
MOCK_DASHBOARD_DATA = {
    "indoorTemperature": 21.5,
    "fanSpeed": "1",
    "season": "heating",
    "temperatureProfile": 0
}

MOCK_THERMAL_DATA = {
    "heatingThermalProfileSeasonData": {
        "comfortTemperature": 20.0
    },
    "coolingThermalProfileSeasonData": {
        "comfortTemperature": 24.0
    },
    "season": {
        "season": 1,
        "status": 1
    }
}

def test_hvac_mode_logic():
    """Test HVAC mode mapping logic."""
    print("\n🧪 Testing HVAC Mode Logic")
    print("=" * 40)

    # Import the mapping from climate.py
    sys.path.append('custom_components/comfoclime')
    from climate import HVAC_MODE_MAPPING
    from homeassistant.components.climate import HVACMode

    test_cases = [
        ("heating", True, HVACMode.HEAT),
        ("cooling", True, HVACMode.COOL),
        ("transition", True, HVACMode.FAN_ONLY),
        ("heating", False, HVACMode.OFF),
        ("cooling", False, HVACMode.OFF),
        ("transition", False, HVACMode.OFF),
    ]

    for season, fan_active, expected_mode in test_cases:
        result = HVAC_MODE_MAPPING.get((season, fan_active))
        status = "✅" if result == expected_mode else "❌"
        print(f"{status} Season: {season:10} | Fan: {fan_active:5} | Expected: {expected_mode:12} | Got: {result}")

def test_preset_mapping():
    """Test preset mode mapping."""
    print("\n🎛️  Testing Preset Mode Mapping")
    print("=" * 40)

    sys.path.append('custom_components/comfoclime')
    from climate import PRESET_MAPPING, PRESET_REVERSE_MAPPING

    print("Profile to Preset mapping:")
    for profile, preset in PRESET_MAPPING.items():
        print(f"  Profile {profile} → {preset}")

    print("\nPreset to Profile mapping:")
    for preset, profile in PRESET_REVERSE_MAPPING.items():
        print(f"  {preset} → Profile {profile}")

async def test_climate_functions():
    """Test the main climate control functions."""
    print("\n🌡️  Testing Climate Control Functions")
    print("=" * 50)

    # Mock API for testing
    class MockAPI:
        def set_device_setting(self, temp_profile=None, fan_speed=None):
            print(f"📡 API: set_device_setting(temp_profile={temp_profile}, fan_speed={fan_speed})")

        def update_thermal_profile(self, updates):
            print(f"📡 API: update_thermal_profile({json.dumps(updates, indent=2)})")

    # Import climate entity
    sys.path.append('custom_components/comfoclime')
    from climate import ComfoClimeClimate
    from homeassistant.components.climate import HVACMode

    # Create mock climate entity
    mock_hass = MockHass()
    mock_coordinator = MockCoordinator(MOCK_DASHBOARD_DATA)
    mock_thermal_coordinator = MockCoordinator(MOCK_THERMAL_DATA)
    mock_api = MockAPI()

    # Create climate entity (simplified for testing)
    climate = ComfoClimeClimate(
        mock_coordinator,
        mock_thermal_coordinator,
        mock_api,
        "test_entry"
    )
    climate.hass = mock_hass

    # Test temperature setting
    print("\n1️⃣ Testing Temperature Setting")
    print("-" * 30)
    await climate.async_set_temperature(temperature=22.0)

    # Test HVAC mode changes
    print("\n2️⃣ Testing HVAC Mode Changes")
    print("-" * 30)

    modes_to_test = [HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY, HVACMode.OFF]
    for mode in modes_to_test:
        print(f"\nSetting HVAC mode to {mode}:")
        await climate.async_set_hvac_mode(mode)

    # Test preset modes
    print("\n3️⃣ Testing Preset Mode Changes")
    print("-" * 30)

    presets_to_test = ["comfort", "power", "eco"]
    for preset in presets_to_test:
        print(f"\nSetting preset mode to {preset}:")
        await climate.async_set_preset_mode(preset)

def main():
    """Run all tests."""
    print("🏠 ComfoClime Climate Entity Test Suite")
    print("=" * 50)

    try:
        # Test static functions
        test_hvac_mode_logic()
        test_preset_mapping()

        # Test async functions
        asyncio.run(test_climate_functions())

        print("\n🎉 All tests completed successfully!")
        print("\n💡 Usage Instructions:")
        print("=" * 30)
        print("1. Set HVAC Mode:")
        print("   - Use climate.set_hvac_mode service with modes: heat, cool, fan_only, off")
        print("2. Set Temperature:")
        print("   - Use climate.set_temperature service with target temperature")
        print("3. Set Preset:")
        print("   - Use climate.set_preset_mode service with presets: comfort, power, eco")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the comfoclime directory")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
