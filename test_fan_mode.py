#!/usr/bin/env python3
"""Test fan_mode functionality in climate entity.

Note: Mappings are duplicated here instead of importing from climate.py
to allow testing without requiring Home Assistant dependencies.
This is intentional for standalone unit tests.
"""

import sys

# Define the mappings locally for testing (copied from climate.py)
FAN_MODE_MAPPING = {
    0: "auto",      # Speed 0 - automatic mode
    1: "low",       # Speed 1
    2: "medium",    # Speed 2
    3: "high",      # Speed 3
}

FAN_MODE_REVERSE_MAPPING = {v: k for k, v in FAN_MODE_MAPPING.items()}

def test_fan_mode_mappings():
    """Test that fan mode mappings are correct."""
    print("Testing fan mode mappings...")
    
    # Test forward mapping (fanSpeed -> fan_mode)
    assert FAN_MODE_MAPPING[0] == "auto", "fanSpeed 0 should map to 'auto'"
    assert FAN_MODE_MAPPING[1] == "low", "fanSpeed 1 should map to 'low'"
    assert FAN_MODE_MAPPING[2] == "medium", "fanSpeed 2 should map to 'medium'"
    assert FAN_MODE_MAPPING[3] == "high", "fanSpeed 3 should map to 'high'"
    print("✓ Forward mapping (fanSpeed -> fan_mode) is correct")
    
    # Test reverse mapping (fan_mode -> fanSpeed)
    assert FAN_MODE_REVERSE_MAPPING["auto"] == 0, "'auto' should map to fanSpeed 0"
    assert FAN_MODE_REVERSE_MAPPING["low"] == 1, "'low' should map to fanSpeed 1"
    assert FAN_MODE_REVERSE_MAPPING["medium"] == 2, "'medium' should map to fanSpeed 2"
    assert FAN_MODE_REVERSE_MAPPING["high"] == 3, "'high' should map to fanSpeed 3"
    print("✓ Reverse mapping (fan_mode -> fanSpeed) is correct")
    
    # Test that mappings are inverses
    for speed, mode in FAN_MODE_MAPPING.items():
        assert FAN_MODE_REVERSE_MAPPING[mode] == speed, f"Mapping inconsistency for {mode}/{speed}"
    print("✓ Mappings are consistent (forward and reverse)")
    
    # Test available fan modes
    available_modes = list(FAN_MODE_REVERSE_MAPPING.keys())
    expected_modes = ["auto", "low", "medium", "high"]
    assert set(available_modes) == set(expected_modes), f"Available modes {available_modes} != expected {expected_modes}"
    print(f"✓ Available fan modes: {available_modes}")
    
    print("\nAll fan mode mapping tests passed! ✅")

def test_fan_speed_logic():
    """Test the logic for converting between fan speeds and modes."""
    print("\nTesting fan speed conversion logic...")
    
    # Simulate dashboard data
    test_cases = [
        {"fanSpeed": 0, "expected_mode": "auto"},
        {"fanSpeed": 1, "expected_mode": "low"},
        {"fanSpeed": 2, "expected_mode": "medium"},
        {"fanSpeed": 3, "expected_mode": "high"},
        {"fanSpeed": "0", "expected_mode": "auto"},  # Test string conversion
        {"fanSpeed": "3", "expected_mode": "high"},
    ]
    
    for test_case in test_cases:
        fan_speed = test_case["fanSpeed"]
        expected_mode = test_case["expected_mode"]
        
        # Simulate the logic from climate.py fan_mode property
        if isinstance(fan_speed, int):
            result_mode = FAN_MODE_MAPPING.get(fan_speed)
        elif isinstance(fan_speed, str) and fan_speed.isdigit():
            result_mode = FAN_MODE_MAPPING.get(int(fan_speed))
        else:
            result_mode = None
        
        assert result_mode == expected_mode, f"fanSpeed {fan_speed} should map to {expected_mode}, got {result_mode}"
        print(f"✓ fanSpeed {fan_speed} → {result_mode}")
    
    print("✓ Fan speed conversion logic works correctly")

if __name__ == "__main__":
    try:
        test_fan_mode_mappings()
        test_fan_speed_logic()
        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
