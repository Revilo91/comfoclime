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

        Uses bitwise operations to determine the current action:
        - Bit 0 (0x01): Device is active/running
        - Bit 1 (0x02): Heating mode flag
        - Bit 2 (0x04): Cooling mode flag
        
        Heat pump status codes (from API documentation):
        Code | Binary      | Meaning
        -----|-------------|--------
        0    | 0000 0000  | Off
        1    | 0000 0001  | Starting up (active, no mode)
        3    | 0000 0011  | Heating (active + heating flag)
        5    | 0000 0101  | Cooling (active + cooling flag)
        17   | 0001 0001  | Transitional (active + other flags)
        19   | 0001 0011  | Heating + transitional state
        21   | 0001 0101  | Cooling + transitional state
        67   | 0100 0011  | Heating + other state
        75   | 0100 1011  | Heating + cooling + other
        83   | 0101 0011  | Heating + other state

        Reference: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md#heat-pump-status-codes
        """
        if not self.coordinator.data:
            return HVACAction.OFF
        
        heat_pump_status = self.coordinator.data.get("heatPumpStatus")
        
        if heat_pump_status is None or heat_pump_status == 0:
            return HVACAction.OFF
        
        # Bitwise operation to determine heating/cooling state
        # Bit 1 (0x02) indicates heating
        # Bit 2 (0x04) indicates cooling
        # If both bits are set (e.g., status 75), heating takes priority
        # This is intentional as heating typically has higher priority for safety
        is_heating = bool(heat_pump_status & 0x02)  # Check bit 1
        is_cooling = bool(heat_pump_status & 0x04)  # Check bit 2
        
        if is_heating:
            return HVACAction.HEATING
        elif is_cooling:
            return HVACAction.COOLING
        else:
            # Device is active but not heating or cooling (starting up or idle)
            return HVACAction.IDLE


def test_hvac_action():
    """Test hvac_action mapping for different heatPumpStatus values using bitwise operations."""
    
    print("Testing hvac_action based on heatPumpStatus (bitwise operation)...\n")
    
    test_cases = [
        # (heatPumpStatus, expected_action, description)
        (None, HVACAction.OFF, "No heatPumpStatus data"),
        (0, HVACAction.OFF, "Heat pump off (0000 0000)"),
        (1, HVACAction.IDLE, "Starting up (0000 0001) - bit 0 only"),
        (3, HVACAction.HEATING, "Actively heating (0000 0011) - bits 0,1"),
        (5, HVACAction.COOLING, "Actively cooling (0000 0101) - bits 0,2"),
        (17, HVACAction.IDLE, "Transitional state 17 (0001 0001) - no heat/cool bits"),
        (19, HVACAction.HEATING, "Heating state 19 (0001 0011) - bit 1 set"),
        (21, HVACAction.COOLING, "Cooling state 21 (0001 0101) - bit 2 set"),
        (67, HVACAction.HEATING, "Heating state 67 (0100 0011) - bit 1 set"),
        (75, HVACAction.HEATING, "Heating priority 75 (0100 1011) - bits 1,2 set, heating priority"),
        (83, HVACAction.HEATING, "Heating state 83 (0101 0011) - bit 1 set"),
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
        
        # Show binary representation for non-None values
        if heat_pump_status is not None:
            binary = format(heat_pump_status, '08b')
            print(f"{status_icon} Status {heat_pump_status:3d} (0b{binary}): {description}")
        else:
            print(f"{status_icon} Status None: {description}")
        
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

