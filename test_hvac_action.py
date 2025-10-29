#!/usr/bin/env python3
"""
Test script for ComfoClime Climate entity hvac_action property.
Tests the new implementation that uses heatPumpStatus from dashboard data.
"""


class HVACAction:
    """Mock HVACAction class."""
    OFF = "off"
    HEATING = "heating"
    COOLING = "cooling"
    IDLE = "idle"


class MockCoordinator:
    """Mock coordinator for testing."""
    def __init__(self, data=None):
        self.data = data or {}
        self.last_update_success = True


class MockClimateEntity:
    """Mock climate entity to test hvac_action logic."""
    
    def __init__(self, dashboard_data=None):
        self.coordinator = MockCoordinator(dashboard_data)
    
    @property
    def hvac_action(self):
        """Return current HVAC action based on dashboard heatPumpStatus.
        
        According to ComfoClime API documentation, heatPumpStatus values:
        - 0: heat pump is off
        - 1: starting up
        - 3: heating
        - 5: cooling
        - Other values: transitional states (defrost, etc.)
        
        Reference: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md#heat-pump-status-codes
        """
        if not self.coordinator.data:
            return HVACAction.OFF
        
        heat_pump_status = self.coordinator.data.get("heatPumpStatus")
        
        if heat_pump_status is None:
            return HVACAction.OFF
        
        # Map heat pump status codes to HVAC actions
        if heat_pump_status == 0:
            # Heat pump is off
            return HVACAction.OFF
        elif heat_pump_status == 1:
            # Starting up - show as idle (preparing to heat/cool)
            return HVACAction.IDLE
        elif heat_pump_status == 3:
            # Actively heating
            return HVACAction.HEATING
        elif heat_pump_status == 5:
            # Actively cooling
            return HVACAction.COOLING
        else:
            # Other status codes (17, 19, 21, 67, 75, 83, etc.)
            # These are transitional states like defrost, anti-freeze, etc.
            # Show as idle since heat pump is running but not actively heating/cooling
            return HVACAction.IDLE


def test_hvac_action():
    """Test hvac_action mapping for different heatPumpStatus values."""
    
    print("Testing hvac_action based on heatPumpStatus...\n")
    
    test_cases = [
        # (heatPumpStatus, expected_action, description)
        (None, HVACAction.OFF, "No heatPumpStatus data"),
        (0, HVACAction.OFF, "Heat pump off"),
        (1, HVACAction.IDLE, "Starting up"),
        (3, HVACAction.HEATING, "Actively heating"),
        (5, HVACAction.COOLING, "Actively cooling"),
        (17, HVACAction.IDLE, "Transitional state 17"),
        (19, HVACAction.IDLE, "Transitional state 19 (defrost)"),
        (21, HVACAction.IDLE, "Transitional state 21"),
        (67, HVACAction.IDLE, "Transitional state 67"),
        (75, HVACAction.IDLE, "Transitional state 75"),
        (83, HVACAction.IDLE, "Transitional state 83"),
    ]
    
    all_passed = True
    
    for heat_pump_status, expected_action, description in test_cases:
        # Create mock data
        if heat_pump_status is None:
            dashboard_data = {}
        else:
            dashboard_data = {"heatPumpStatus": heat_pump_status}
        
        # Create entity and get action
        entity = MockClimateEntity(dashboard_data)
        actual_action = entity.hvac_action
        
        # Check result
        passed = actual_action == expected_action
        all_passed = all_passed and passed
        
        status_icon = "✓" if passed else "✗"
        print(f"{status_icon} heatPumpStatus={heat_pump_status}: {description}")
        print(f"  Expected: {expected_action}, Got: {actual_action}")
        
        if not passed:
            print(f"  ❌ FAILED!")
        print()
    
    # Test with no coordinator data
    entity = MockClimateEntity(None)
    actual_action = entity.hvac_action
    expected_action = HVACAction.OFF
    passed = actual_action == expected_action
    all_passed = all_passed and passed
    
    status_icon = "✓" if passed else "✗"
    print(f"{status_icon} No coordinator data: Expected {expected_action}, Got {actual_action}\n")
    
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
    sys.exit(test_hvac_action())

