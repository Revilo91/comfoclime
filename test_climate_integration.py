#!/usr/bin/env python3
"""
Integration test for ComfoClime Climate control.

This test directly interacts with a real ComfoClime device without using mocks.
It tests all major climate control operations including HVAC modes, presets,
temperature settings, and fan control.

Requirements:
- A ComfoClime device must be available on the network
- Configure COMFOCLIME_IP environment variable or edit the IP address below
- Python 3.10+ with requests library

Usage:
    # Set device IP address
    export COMFOCLIME_IP="192.168.1.100"
    
    # Run the test
    python3 test_climate_integration.py
    
    # Or run with custom IP
    python3 test_climate_integration.py --ip 192.168.1.100

The test will:
1. Connect to the ComfoClime device
2. Read current state
3. Test HVAC mode switching (OFF, HEAT, COOL, FAN_ONLY)
4. Test preset mode switching (COMFORT, BOOST, ECO, MANUAL)
5. Test temperature setting
6. Test fan mode control
7. Restore original state
8. Display comprehensive results

WARNING: This test will change settings on your ComfoClime device!
Make sure to run it when you can tolerate temporary changes to your climate control.
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Add the custom_components directory to the path so we can import the API module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components", "comfoclime"))

# Import only the API module to avoid Home Assistant dependencies
from comfoclime_api import ComfoClimeAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

# HVAC Mode constants (matching climate.py)
HVAC_MODE_OFF = "off"
HVAC_MODE_HEAT = "heat"
HVAC_MODE_COOL = "cool"
HVAC_MODE_FAN_ONLY = "fan_only"

# Preset Mode constants (matching climate.py)
PRESET_NONE = "none"  # Manual mode
PRESET_COMFORT = "comfort"
PRESET_BOOST = "boost"
PRESET_ECO = "eco"

# Fan Mode constants (matching climate.py)
FAN_OFF = "off"
FAN_LOW = "low"
FAN_MEDIUM = "medium"
FAN_HIGH = "high"

# Mapping constants (matching climate.py)
HVAC_MODE_REVERSE_MAPPING = {
    HVAC_MODE_OFF: None,        # Turn off device via hpStandby=True
    HVAC_MODE_FAN_ONLY: 0,      # Transitional season (fan only)
    HVAC_MODE_HEAT: 1,          # Heating season
    HVAC_MODE_COOL: 2,          # Cooling season
}

PRESET_REVERSE_MAPPING = {
    PRESET_COMFORT: 0,
    PRESET_BOOST: 1,
    PRESET_ECO: 2,
}

FAN_MODE_REVERSE_MAPPING = {
    FAN_OFF: 0,
    FAN_LOW: 1,
    FAN_MEDIUM: 2,
    FAN_HIGH: 3,
}


@dataclass
class ClimateState:
    """Current state of the climate device."""
    indoor_temperature: Optional[float] = None
    target_temperature: Optional[float] = None
    season: Optional[int] = None
    hp_standby: Optional[bool] = None
    fan_speed: Optional[int] = None
    status: Optional[int] = None
    temperature_profile: Optional[int] = None
    season_profile: Optional[int] = None
    set_point_temperature: Optional[float] = None
    heat_pump_status: Optional[int] = None


class ClimateIntegrationTest:
    """Integration test for ComfoClime Climate control."""
    
    def __init__(self, ip_address: str):
        """Initialize the test with the ComfoClime device IP address."""
        self.api = ComfoClimeAPI(f"http://{ip_address}")
        self.ip_address = ip_address
        self.original_state: Optional[ClimateState] = None
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self) -> bool:
        """Connect to the ComfoClime device and get UUID."""
        try:
            _LOGGER.info(f"Connecting to ComfoClime device at {self.ip_address}...")
            # We need a minimal async context - create a fake hass object
            class FakeHass:
                def async_add_executor_job(self, func, *args):
                    """Execute a function in executor (simplified for testing)."""
                    return asyncio.get_event_loop().run_in_executor(None, func, *args)
            
            self.hass = FakeHass()
            uuid = await self.api.async_get_uuid(self.hass)
            _LOGGER.info(f"Connected successfully! Device UUID: {uuid}")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to connect to ComfoClime device: {e}")
            return False
    
    async def get_current_state(self) -> ClimateState:
        """Read current state from the device."""
        dashboard = await self.api.async_get_dashboard_data(self.hass)
        thermal_profile = await self.api.async_get_thermal_profile(self.hass)
        
        state = ClimateState(
            indoor_temperature=dashboard.get("indoorTemperature"),
            season=dashboard.get("season"),
            hp_standby=dashboard.get("hpStandby"),
            fan_speed=dashboard.get("fanSpeed"),
            status=dashboard.get("status"),
            temperature_profile=dashboard.get("temperatureProfile"),
            season_profile=dashboard.get("seasonProfile"),
            set_point_temperature=dashboard.get("setPointTemperature"),
            heat_pump_status=dashboard.get("heatPumpStatus"),
            target_temperature=(thermal_profile.get("temperature", {}) or {}).get("manualTemperature"),
        )
        
        return state
    
    def print_state(self, state: ClimateState, label: str = "Current State"):
        """Print the current climate state in a readable format."""
        print(f"\n{'=' * 60}")
        print(f"{label}")
        print(f"{'=' * 60}")
        print(f"Indoor Temperature:    {state.indoor_temperature}°C")
        print(f"Target Temperature:    {state.target_temperature}°C")
        print(f"Set Point Temperature: {state.set_point_temperature}°C")
        print(f"Season:                {state.season} ({self._season_name(state.season)})")
        print(f"HP Standby:            {state.hp_standby}")
        print(f"Fan Speed:             {state.fan_speed} ({self._fan_name(state.fan_speed)})")
        print(f"Status:                {state.status} ({'Manual' if state.status == 0 else 'Auto' if state.status == 1 else 'Unknown'})")
        print(f"Temperature Profile:   {state.temperature_profile}")
        print(f"Season Profile:        {state.season_profile}")
        print(f"Heat Pump Status:      {state.heat_pump_status}")
        print(f"{'=' * 60}\n")
    
    @staticmethod
    def _season_name(season: Optional[int]) -> str:
        """Convert season number to name."""
        if season is None:
            return "Unknown"
        return {0: "Transition", 1: "Heating", 2: "Cooling"}.get(season, f"Unknown({season})")
    
    @staticmethod
    def _fan_name(speed: Optional[int]) -> str:
        """Convert fan speed to name."""
        if speed is None:
            return "Unknown"
        return {0: "Off", 1: "Low", 2: "Medium", 3: "High"}.get(speed, f"Unknown({speed})")
    
    async def wait_for_update(self, seconds: float = 3.0):
        """Wait for the device to process the update."""
        _LOGGER.info(f"Waiting {seconds}s for device to process update...")
        await asyncio.sleep(seconds)
    
    async def test_hvac_mode(self, hvac_mode: str) -> bool:
        """Test setting HVAC mode."""
        test_name = f"Set HVAC Mode: {hvac_mode.upper()}"
        _LOGGER.info(f"\n{'*' * 60}")
        _LOGGER.info(f"Testing: {test_name}")
        _LOGGER.info(f"{'*' * 60}")
        
        try:
            season_value = HVAC_MODE_REVERSE_MAPPING[hvac_mode]
            
            # Set HVAC mode using the same logic as climate.py
            if hvac_mode == HVAC_MODE_OFF:
                _LOGGER.info("Setting HVAC mode to OFF - setting hpStandby=True")
                await self.api.async_update_dashboard(self.hass, hp_standby=True)
            else:
                _LOGGER.info(f"Setting HVAC mode to {hvac_mode} - setting season={season_value} and hpStandby=False")
                await self.api.async_set_hvac_season(
                    self.hass,
                    season=season_value,
                    hp_standby=False
                )
            
            # Wait for device to update
            await self.wait_for_update()
            
            # Verify the change
            state = await self.get_current_state()
            
            success = False
            if hvac_mode == HVAC_MODE_OFF:
                success = state.hp_standby is True
                _LOGGER.info(f"Verification: hpStandby={state.hp_standby} (expected: True)")
            else:
                success = state.season == season_value and state.hp_standby is False
                _LOGGER.info(f"Verification: season={state.season}, hpStandby={state.hp_standby} "
                           f"(expected: season={season_value}, hpStandby=False)")
            
            self.test_results[test_name] = {
                "success": success,
                "state_after": state,
                "expected_season": season_value,
                "actual_season": state.season,
                "expected_standby": True if hvac_mode == HVAC_MODE_OFF else False,
                "actual_standby": state.hp_standby,
            }
            
            if success:
                _LOGGER.info(f"✅ {test_name} - SUCCESS")
            else:
                _LOGGER.warning(f"❌ {test_name} - FAILED")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"❌ {test_name} - EXCEPTION: {e}", exc_info=True)
            self.test_results[test_name] = {"success": False, "error": str(e)}
            return False
    
    async def test_preset_mode(self, preset_mode: str) -> bool:
        """Test setting preset mode."""
        test_name = f"Set Preset Mode: {preset_mode.upper()}"
        _LOGGER.info(f"\n{'*' * 60}")
        _LOGGER.info(f"Testing: {test_name}")
        _LOGGER.info(f"{'*' * 60}")
        
        try:
            # Set preset mode using the same logic as climate.py
            if preset_mode == PRESET_NONE:
                _LOGGER.info("Setting preset to MANUAL (none) - setting status=0")
                await self.api.async_update_dashboard(self.hass, status=0)
            else:
                profile_value = PRESET_REVERSE_MAPPING[preset_mode]
                _LOGGER.info(f"Setting preset to {preset_mode} (profile={profile_value}) - "
                           f"setting temperatureProfile={profile_value}, seasonProfile={profile_value}, status=1")
                await self.api.async_update_dashboard(
                    self.hass,
                    temperature_profile=profile_value,
                    season_profile=profile_value,
                    status=1,
                )
            
            # Wait for device to update
            await self.wait_for_update()
            
            # Verify the change
            state = await self.get_current_state()
            
            success = False
            if preset_mode == PRESET_NONE:
                success = state.status == 0
                _LOGGER.info(f"Verification: status={state.status} (expected: 0)")
            else:
                profile_value = PRESET_REVERSE_MAPPING[preset_mode]
                success = (state.temperature_profile == profile_value and 
                          state.season_profile == profile_value and 
                          state.status == 1)
                _LOGGER.info(f"Verification: temperatureProfile={state.temperature_profile}, "
                           f"seasonProfile={state.season_profile}, status={state.status} "
                           f"(expected: all={profile_value}, status=1)")
            
            self.test_results[test_name] = {
                "success": success,
                "state_after": state,
            }
            
            if success:
                _LOGGER.info(f"✅ {test_name} - SUCCESS")
            else:
                _LOGGER.warning(f"❌ {test_name} - FAILED")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"❌ {test_name} - EXCEPTION: {e}", exc_info=True)
            self.test_results[test_name] = {"success": False, "error": str(e)}
            return False
    
    async def test_temperature(self, temperature: float) -> bool:
        """Test setting target temperature."""
        test_name = f"Set Temperature: {temperature}°C"
        _LOGGER.info(f"\n{'*' * 60}")
        _LOGGER.info(f"Testing: {test_name}")
        _LOGGER.info(f"{'*' * 60}")
        
        try:
            _LOGGER.info(f"Setting temperature to {temperature}°C with status=0 (manual mode)")
            await self.api.async_update_dashboard(
                self.hass,
                set_point_temperature=temperature,
                status=0,
            )
            
            # Wait for device to update
            await self.wait_for_update()
            
            # Verify the change
            state = await self.get_current_state()
            
            # Check if set point temperature matches (allowing small float tolerance)
            success = (state.set_point_temperature is not None and 
                      abs(state.set_point_temperature - temperature) < 0.1)
            
            _LOGGER.info(f"Verification: setPointTemperature={state.set_point_temperature} "
                       f"(expected: {temperature})")
            
            self.test_results[test_name] = {
                "success": success,
                "state_after": state,
                "expected_temperature": temperature,
                "actual_temperature": state.set_point_temperature,
            }
            
            if success:
                _LOGGER.info(f"✅ {test_name} - SUCCESS")
            else:
                _LOGGER.warning(f"❌ {test_name} - FAILED")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"❌ {test_name} - EXCEPTION: {e}", exc_info=True)
            self.test_results[test_name] = {"success": False, "error": str(e)}
            return False
    
    async def test_fan_mode(self, fan_mode: str) -> bool:
        """Test setting fan mode."""
        test_name = f"Set Fan Mode: {fan_mode.upper()}"
        _LOGGER.info(f"\n{'*' * 60}")
        _LOGGER.info(f"Testing: {test_name}")
        _LOGGER.info(f"{'*' * 60}")
        
        try:
            fan_speed = FAN_MODE_REVERSE_MAPPING[fan_mode]
            _LOGGER.info(f"Setting fan mode to {fan_mode} (speed={fan_speed})")
            
            await self.api.async_update_dashboard(self.hass, fan_speed=fan_speed)
            
            # Wait for device to update
            await self.wait_for_update()
            
            # Verify the change
            state = await self.get_current_state()
            
            success = state.fan_speed == fan_speed
            _LOGGER.info(f"Verification: fanSpeed={state.fan_speed} (expected: {fan_speed})")
            
            self.test_results[test_name] = {
                "success": success,
                "state_after": state,
                "expected_fan_speed": fan_speed,
                "actual_fan_speed": state.fan_speed,
            }
            
            if success:
                _LOGGER.info(f"✅ {test_name} - SUCCESS")
            else:
                _LOGGER.warning(f"❌ {test_name} - FAILED")
            
            return success
            
        except Exception as e:
            _LOGGER.error(f"❌ {test_name} - EXCEPTION: {e}", exc_info=True)
            self.test_results[test_name] = {"success": False, "error": str(e)}
            return False
    
    async def restore_state(self) -> bool:
        """Restore the original state of the device."""
        if self.original_state is None:
            _LOGGER.warning("No original state to restore")
            return False
        
        _LOGGER.info("\n" + "=" * 60)
        _LOGGER.info("Restoring original device state...")
        _LOGGER.info("=" * 60)
        
        try:
            state = self.original_state
            
            # Restore dashboard settings
            dashboard_updates = {}
            if state.status is not None:
                dashboard_updates["status"] = state.status
            if state.set_point_temperature is not None:
                dashboard_updates["set_point_temperature"] = state.set_point_temperature
            if state.temperature_profile is not None:
                dashboard_updates["temperature_profile"] = state.temperature_profile
            if state.season_profile is not None:
                dashboard_updates["season_profile"] = state.season_profile
            if state.fan_speed is not None:
                dashboard_updates["fan_speed"] = state.fan_speed
            if state.hp_standby is not None:
                dashboard_updates["hp_standby"] = state.hp_standby
            
            if dashboard_updates:
                _LOGGER.info(f"Restoring dashboard settings: {dashboard_updates}")
                await self.api.async_update_dashboard(self.hass, **dashboard_updates)
                await self.wait_for_update()
            
            # Restore season via thermal profile if needed
            if state.season is not None and not state.hp_standby:
                _LOGGER.info(f"Restoring season: {state.season}")
                await self.api.async_update_thermal_profile(
                    self.hass,
                    {"season": {"season": state.season}}
                )
                await self.wait_for_update()
            
            _LOGGER.info("✅ Original state restored successfully")
            return True
            
        except Exception as e:
            _LOGGER.error(f"❌ Failed to restore original state: {e}", exc_info=True)
            return False
    
    def print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.get("success", False))
        failed_tests = total_tests - passed_tests
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            print(f"{status} - {test_name}")
            if "error" in result:
                print(f"         Error: {result['error']}")
        
        print("\n" + "-" * 60)
        print(f"Total Tests:  {total_tests}")
        print(f"Passed:       {passed_tests}")
        print(f"Failed:       {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%")
        print("=" * 60 + "\n")
        
        return failed_tests == 0
    
    async def run_all_tests(self):
        """Run all climate control tests."""
        print("\n" + "=" * 60)
        print("ComfoClime Climate Integration Test")
        print("=" * 60)
        print(f"Device IP: {self.ip_address}")
        print(f"Test Start: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        # Connect to device
        if not await self.connect():
            print("\n❌ Failed to connect to device. Aborting tests.")
            return False
        
        # Read and save original state
        _LOGGER.info("Reading original device state...")
        self.original_state = await self.get_current_state()
        self.print_state(self.original_state, "Original State (will be restored)")
        
        # Run tests
        try:
            # Test HVAC modes
            await self.test_hvac_mode(HVAC_MODE_HEAT)
            await self.test_hvac_mode(HVAC_MODE_COOL)
            await self.test_hvac_mode(HVAC_MODE_FAN_ONLY)
            await self.test_hvac_mode(HVAC_MODE_OFF)
            
            # Restore to active state for remaining tests
            if self.original_state.hp_standby:
                _LOGGER.info("Activating device for remaining tests...")
                await self.api.async_update_dashboard(self.hass, hp_standby=False)
                await self.wait_for_update()
            
            # Test preset modes
            await self.test_preset_mode(PRESET_COMFORT)
            await self.test_preset_mode(PRESET_BOOST)
            await self.test_preset_mode(PRESET_ECO)
            await self.test_preset_mode(PRESET_NONE)
            
            # Test temperature setting
            await self.test_temperature(21.0)
            await self.test_temperature(22.5)
            
            # Test fan modes
            await self.test_fan_mode(FAN_LOW)
            await self.test_fan_mode(FAN_MEDIUM)
            await self.test_fan_mode(FAN_HIGH)
            await self.test_fan_mode(FAN_OFF)
            
        finally:
            # Always try to restore original state
            await self.restore_state()
            
            # Display final state
            final_state = await self.get_current_state()
            self.print_state(final_state, "Final State")
        
        # Print summary
        success = self.print_summary()
        
        return success


async def main():
    """Main entry point for the test."""
    # Get IP address from environment variable or command line
    ip_address = os.environ.get("COMFOCLIME_IP")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
            sys.exit(0)
        elif sys.argv[1] == "--ip" and len(sys.argv) > 2:
            ip_address = sys.argv[2]
        else:
            ip_address = sys.argv[1]
    
    if not ip_address:
        print("ERROR: No IP address provided!")
        print("\nPlease provide the ComfoClime device IP address using one of these methods:")
        print("  1. Environment variable: export COMFOCLIME_IP='192.168.1.100'")
        print("  2. Command line argument: python3 test_climate_integration.py 192.168.1.100")
        print("  3. Command line option: python3 test_climate_integration.py --ip 192.168.1.100")
        print("\nFor more help, run: python3 test_climate_integration.py --help")
        sys.exit(1)
    
    # Create and run test
    test = ClimateIntegrationTest(ip_address)
    success = await test.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
