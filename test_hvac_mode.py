#!/usr/bin/env python3
"""
Test script for ComfoClime Climate entity hvac_mode property.
Tests the new implementation that uses dashboard data.
"""


class HVACMode:
    """Mock HVACMode class."""
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    FAN_ONLY = "fan_only"


class MockCoordinator:
    """Mock coordinator for testing."""
    def __init__(self, data=None):
        self.data = data or {}
        self.last_update_success = True


class MockClimateEntity:
    """Mock climate entity to test hvac_mode logic."""
    
    def __init__(self, dashboard_data=None):
        self.coordinator = MockCoordinator(dashboard_data)
    
    @property
    def hvac_mode(self):
        """Return current HVAC mode from dashboard data.
        
        Maps the season field from dashboard to HVAC mode:
        - season 0 (transitional) → FAN_ONLY
        - season 1 (heating) → HEAT
        - season 2 (cooling) → COOL
        - hpStandby true → OFF (device powered off)
        """
        if not self.coordinator.data:
            return HVACMode.OFF
        
        # Check if device is in standby (powered off)
        hp_standby = self.coordinator.data.get("hpStandby")
        if hp_standby is True:
            return HVACMode.OFF
        
        # Map season from dashboard to HVAC mode
        season = self.coordinator.data.get("season")
        
        if season == 0:  # transitional
            return HVACMode.FAN_ONLY
        elif season == 1:  # heating
            return HVACMode.HEAT
        elif season == 2:  # cooling
            return HVACMode.COOL
        
        return HVACMode.OFF


def test_hvac_mode():
    """Test hvac_mode mapping for different dashboard values."""
    
    print("Testing hvac_mode based on dashboard data...\n")
    
    test_cases = [
        # (dashboard_data, expected_mode, description)
        ({}, HVACMode.OFF, "No data"),
        ({"season": None}, HVACMode.OFF, "Season is None"),
        ({"season": 0, "hpStandby": False}, HVACMode.FAN_ONLY, "Transitional season"),
        ({"season": 1, "hpStandby": False}, HVACMode.HEAT, "Heating season"),
        ({"season": 2, "hpStandby": False}, HVACMode.COOL, "Cooling season"),
        ({"season": 1, "hpStandby": True}, HVACMode.OFF, "Device in standby (powered off)"),
        ({"season": 2, "hpStandby": True}, HVACMode.OFF, "Cooling season but device in standby"),
    ]
    
    all_passed = True
    
    for dashboard_data, expected_mode, description in test_cases:
        # Create entity and get mode
        entity = MockClimateEntity(dashboard_data)
        actual_mode = entity.hvac_mode
        
        # Check result
        passed = actual_mode == expected_mode
        all_passed = all_passed and passed
        
        status_icon = "✓" if passed else "✗"
        print(f"{status_icon} {description}")
        print(f"  Dashboard: {dashboard_data}")
        print(f"  Expected: {expected_mode}, Got: {actual_mode}")
        
        if not passed:
            print(f"  ❌ FAILED!")
        print()
    
    # Test with no coordinator data
    entity = MockClimateEntity(None)
    actual_mode = entity.hvac_mode
    expected_mode = HVACMode.OFF
    passed = actual_mode == expected_mode
    all_passed = all_passed and passed
    
    status_icon = "✓" if passed else "✗"
    print(f"{status_icon} No coordinator data: Expected {expected_mode}, Got {actual_mode}\n")
    
    if all_passed:
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("❌ Some tests failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(test_hvac_mode())
