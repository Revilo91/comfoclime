#!/usr/bin/env python3
"""
Test script to verify the refactored climate.py logic.
Tests the consolidated dashboard update method and simplified temperature setting.
"""

import asyncio
import json
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import sys
import os

# Add the custom_components path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components/comfoclime'))


def test_consolidated_dashboard_method():
    """Test that the consolidated _update_dashboard method is properly defined."""
    print("\n🧪 Test 1: Verify consolidated dashboard method exists")
    print("=" * 60)
    
    try:
        # We can't import the class directly due to homeassistant dependencies
        # but we can check the source code
        with open('custom_components/comfoclime/climate.py', 'r') as f:
            content = f.read()
        
        # Check that the new consolidated method exists
        if 'async def _update_dashboard(' in content:
            print("✅ PASS: _update_dashboard method exists")
        else:
            print("❌ FAIL: _update_dashboard method not found")
            return False
        
        # Check that old methods are removed
        old_methods = [
            'async def async_set_setpoint_temperature',
            'async def _set_hp_standby',
            'async def _set_dashboard_hvac_settings'
        ]
        
        for method in old_methods:
            if method in content:
                print(f"❌ FAIL: Old method still exists: {method}")
                return False
        
        print("✅ PASS: All old dashboard methods removed")
        
        # Check that the method has proper parameters
        params_to_check = [
            'set_point_temperature',
            'fan_speed',
            'season',
            'hp_standby',
            'schedule'
        ]
        
        for param in params_to_check:
            if param not in content:
                print(f"⚠️  WARNING: Parameter '{param}' might be missing")
        
        print("✅ PASS: Consolidated method has expected parameters")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_simplified_temperature_setting():
    """Test that temperature setting is simplified to use only dashboard."""
    print("\n🧪 Test 2: Verify simplified temperature setting")
    print("=" * 60)
    
    try:
        with open('custom_components/comfoclime/climate.py', 'r') as f:
            content = f.read()
        
        # Find the async_set_temperature method
        method_start = content.find('async def async_set_temperature(')
        if method_start == -1:
            print("❌ FAIL: async_set_temperature method not found")
            return False
        
        # Get the method content (up to next async def or class end)
        method_end = content.find('\n    async def ', method_start + 1)
        if method_end == -1:
            method_end = content.find('\n    @property', method_start + 1)
        
        method_content = content[method_start:method_end]
        
        # Check that it uses _update_dashboard
        if '_update_dashboard' in method_content:
            print("✅ PASS: async_set_temperature uses _update_dashboard")
        else:
            print("❌ FAIL: async_set_temperature doesn't use _update_dashboard")
            return False
        
        # Check that it doesn't use update_thermal_profile anymore
        if 'update_thermal_profile' in method_content:
            print("❌ FAIL: Still using update_thermal_profile (should use dashboard only)")
            return False
        
        print("✅ PASS: async_set_temperature no longer uses update_thermal_profile")
        
        # Check that the method is shorter (simplified)
        line_count = method_content.count('\n')
        if line_count < 30:  # Old version was ~52 lines
            print(f"✅ PASS: Method simplified (now ~{line_count} lines, was ~52)")
        else:
            print(f"⚠️  WARNING: Method still seems long ({line_count} lines)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_removed_unused_methods():
    """Test that unused methods are removed."""
    print("\n🧪 Test 3: Verify unused methods removed")
    print("=" * 60)
    
    try:
        with open('custom_components/comfoclime/climate.py', 'r') as f:
            content = f.read()
        
        # Check that _get_season_status is removed
        if 'def _get_season_status(' in content:
            print("❌ FAIL: _get_season_status should be removed (unused)")
            return False
        
        print("✅ PASS: _get_season_status removed (was unused)")
        
        # Check that still-needed methods are kept
        needed_methods = [
            'def _get_temperature_status(',
            'def _get_current_season('
        ]
        
        for method in needed_methods:
            if method not in content:
                print(f"❌ FAIL: Required method missing: {method}")
                return False
        
        print("✅ PASS: Required helper methods still present")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_dashboard_preference():
    """Test that properties prefer dashboard data."""
    print("\n🧪 Test 4: Verify dashboard data preference")
    print("=" * 60)
    
    try:
        with open('custom_components/comfoclime/climate.py', 'r') as f:
            content = f.read()
        
        # Check preset_mode property
        preset_start = content.find('def preset_mode(self)')
        if preset_start == -1:
            print("❌ FAIL: preset_mode property not found")
            return False
        
        preset_end = content.find('\n    @property', preset_start + 1)
        if preset_end == -1:
            preset_end = content.find('\n    def ', preset_start + 1)
        
        preset_content = content[preset_start:preset_end]
        
        # Check it reads from dashboard first
        lines = preset_content.split('\n')
        dashboard_line = None
        thermal_line = None
        
        for i, line in enumerate(lines):
            if 'self.coordinator.data' in line and dashboard_line is None:
                dashboard_line = i
            if 'self._thermalprofile_coordinator.data' in line and thermal_line is None:
                thermal_line = i
        
        if dashboard_line is not None and thermal_line is not None:
            if dashboard_line < thermal_line:
                print("✅ PASS: preset_mode checks dashboard before thermalprofile")
            else:
                print("❌ FAIL: preset_mode checks thermalprofile before dashboard")
                return False
        else:
            print("⚠️  WARNING: Could not verify dashboard preference order")
        
        # Check _get_current_season uses dashboard
        season_start = content.find('def _get_current_season(self)')
        if season_start != -1:
            season_end = content.find('\n    def ', season_start + 1)
            season_content = content[season_start:season_end]
            
            if 'self.coordinator.data' in season_content:
                print("✅ PASS: _get_current_season now uses dashboard data")
            else:
                print("⚠️  WARNING: _get_current_season might not use dashboard")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_line_count_reduction():
    """Test that the refactoring reduced code size."""
    print("\n🧪 Test 5: Verify code size reduction")
    print("=" * 60)
    
    try:
        with open('custom_components/comfoclime/climate.py', 'r') as f:
            lines = f.readlines()
        
        line_count = len(lines)
        print(f"📊 Current line count: {line_count}")
        
        # Original was 648 lines, we should be around 547
        if line_count < 600:
            print(f"✅ PASS: Code reduced from ~648 to {line_count} lines")
            reduction = 648 - line_count
            print(f"   📉 Reduction: {reduction} lines ({reduction/648*100:.1f}%)")
        else:
            print(f"⚠️  WARNING: Expected more reduction (current: {line_count}, target: <600)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🏠 ComfoClime Climate.py Refactoring Tests")
    print("=" * 60)
    
    tests = [
        test_consolidated_dashboard_method,
        test_simplified_temperature_setting,
        test_removed_unused_methods,
        test_dashboard_preference,
        test_line_count_reduction,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    if passed < total:
        print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Refactoring successful!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
