"""Real device fixtures and recording utilities for ComfoClime tests.

This module provides fixtures for testing against real ComfoClime devices
or recorded responses from real devices.

Usage:
    1. Record responses from real device:
       pytest tests/ --record-responses --device-ip=10.0.2.27

    2. Run tests against real device:
       pytest tests/ --real-device --device-ip=10.0.2.27

    3. Run tests with recorded responses (default, offline):
       pytest tests/
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio

from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)


# Path for recorded responses
RESPONSES_DIR = Path(__file__).parent / "recorded_responses"


class ResponseRecorder:
    """Records and loads API responses for test fixtures."""

    def __init__(self, responses_dir: Path):
        self.responses_dir = responses_dir
        self.responses_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, endpoint: str) -> Path:
        """Get filepath for an endpoint."""
        filename = endpoint.replace("/", "_").strip("_") + ".json"
        return self.responses_dir / filename

    def save_response(self, endpoint: str, response: Any) -> None:
        """Save a response to a file."""
        filepath = self._get_filepath(endpoint)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved: {filepath.name}")

    def load_response(self, endpoint: str) -> Any | None:
        """Load a recorded response."""
        filepath = self._get_filepath(endpoint)
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        return None

    def has_response(self, endpoint: str) -> bool:
        """Check if a response exists."""
        return self._get_filepath(endpoint).exists()


class RecordedResponseAPI:
    """Mock API that uses recorded responses instead of real network calls.

    This allows running tests offline using previously recorded data.
    Implements the same interface as ComfoClimeAPI for test compatibility.
    """

    def __init__(self, responses_dir: Path):
        self.recorder = ResponseRecorder(responses_dir)
        self._device_uuid: str | None = None
        self._connected_devices: list[dict] = []

    async def async_get_uuid(self) -> str:
        """Get device UUID from recorded response."""
        response = self.recorder.load_response("monitoring_ping")
        if response and isinstance(response, dict):
            self._device_uuid = response.get("uuid", "recorded-device-uuid")
        else:
            self._device_uuid = "recorded-device-uuid"
        return self._device_uuid

    @property
    def uuid(self) -> str:
        """Return cached UUID."""
        return self._device_uuid or "recorded-device-uuid"

    async def async_get_monitoring_ping(self) -> dict:
        """Get monitoring ping from recorded response."""
        return self.recorder.load_response("monitoring_ping") or {}

    async def async_get_dashboard_data(self) -> dict:
        """Get dashboard data from recorded response."""
        # Try with UUID suffix first, then without
        data = self.recorder.load_response(f"dashboard_{self._device_uuid}")
        if not data:
            data = self.recorder.load_response("dashboard")
        return data or {}

    async def async_get_thermal_profile(self) -> dict:
        """Get thermal profile from recorded response."""
        data = self.recorder.load_response(f"thermalProfile_{self._device_uuid}")
        if not data:
            data = self.recorder.load_response("thermalProfile")
        return data or {}

    async def async_get_connected_devices(self) -> list[dict]:
        """Get connected devices from recorded response."""
        # Try multiple possible response formats
        data = self.recorder.load_response(f"devices_{self._device_uuid}")
        if not data:
            data = self.recorder.load_response(f"connectedDevice_{self._device_uuid}")
        if not data:
            data = self.recorder.load_response("devices")
        if not data:
            data = self.recorder.load_response("connectedDevice")

        # Handle both {"devices": [...]} and [...] formats
        if isinstance(data, dict) and "devices" in data:
            devices = data["devices"]
        elif isinstance(data, list):
            devices = data
        else:
            devices = []

        self._connected_devices = devices
        return devices

    async def async_get_device_definition(self, device_uuid: str) -> dict:
        """Get device definition from recorded response."""
        return self.recorder.load_response(f"definition_{device_uuid}") or {}

    async def async_read_telemetry_for_device(
        self, device_uuid: str, telemetry_id: int | str, **kwargs
    ) -> float | None:
        """Get telemetry data from recorded response."""
        data = self.recorder.load_response(f"telemetry_{device_uuid}") or {}
        tel_data = data.get(str(telemetry_id))

        if not tel_data or "data" not in tel_data:
            return None

        # Decode the raw bytes like the real API does
        raw_data = tel_data["data"]
        faktor = kwargs.get("faktor", 1.0)
        signed = kwargs.get("signed", True)
        byte_count = kwargs.get("byte_count", len(raw_data))

        if byte_count == 1 or len(raw_data) == 1:
            value = raw_data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif byte_count == 2 or len(raw_data) >= 2:
            lsb, msb = raw_data[0], raw_data[1]
            value = lsb + (msb << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        else:
            return None

        return value * faktor

    async def async_read_property_for_device(
        self, device_uuid: str, path: str, **kwargs
    ) -> int | None:
        """Get property data from recorded response."""
        data = self.recorder.load_response(f"property_{device_uuid}") or {}
        prop_data = data.get(path)

        if not prop_data or "data" not in prop_data:
            return None

        # Decode the raw bytes like the real API does
        raw_data = prop_data["data"]
        faktor = kwargs.get("faktor", 1.0)
        signed = kwargs.get("signed", True)
        byte_count = kwargs.get("byte_count", len(raw_data))

        if byte_count == 1 or len(raw_data) == 1:
            value = raw_data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif byte_count == 2 or len(raw_data) >= 2:
            lsb, msb = raw_data[0], raw_data[1]
            value = lsb + (msb << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        else:
            return None

        return int(value * faktor)

    # ================================================================
    # Write methods - mock implementations for testing
    # ================================================================

    async def async_update_dashboard(self, **kwargs) -> None:
        """Mock update - logs call but doesn't persist."""
        _LOGGER.debug("[RecordedAPI] async_update_dashboard called with: %s", kwargs)

    async def async_set_hvac_season(self, season: int, hpStandby: bool) -> None:
        """Mock set HVAC season."""
        _LOGGER.debug(
            "[RecordedAPI] async_set_hvac_season called: season=%s, hpStandby=%s",
            season,
            hpStandby,
        )

    async def async_update_thermal_profile(self, **kwargs) -> None:
        """Mock update thermal profile."""
        _LOGGER.debug(
            "[RecordedAPI] async_update_thermal_profile called with: %s", kwargs
        )

    async def async_set_property_for_device(
        self, device_uuid: str, property_path: str, value: int, **kwargs
    ) -> None:
        """Mock set property."""
        _LOGGER.debug(
            "[RecordedAPI] async_set_property_for_device: %s/%s = %s",
            device_uuid,
            property_path,
            value,
        )

    async def async_reset_system(self) -> None:
        """Mock reset system."""
        _LOGGER.debug("[RecordedAPI] async_reset_system called")

    def close(self) -> None:
        """Close the API (no-op for recorded responses)."""
        pass


async def record_all_responses(device_ip: str, responses_dir: Path) -> None:
    """Record all API responses from a real device.

    Records responses from all known API endpoints:
    - /monitoring/ping - Device UUID and status
    - /system/{uuid}/dashboard - Temperature, fan, HVAC status
    - /system/{uuid}/thermalprofile - Heating/cooling profiles
    - /system/{uuid}/devices - Connected devices list
    - /device/{uuid}/definition - Device definitions
    - /device/{uuid}/telemetry/{id} - Sensor readings
    - /device/{uuid}/property/{path} - Device properties
    """
    recorder = ResponseRecorder(responses_dir)
    base_url = f"http://{device_ip}"  # No /api prefix - ComfoClime uses root URL

    print(f"\n🔴 Recording responses from ComfoClime at {device_ip}...")
    print(f"   Saving to: {responses_dir}\n")

    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # ================================================================
        # 1. Monitoring Ping - Get UUID
        # ================================================================
        uuid = None
        try:
            async with session.get(f"{base_url}/monitoring/ping") as resp:
                if resp.status == 200:
                    ping_data = await resp.json()
                    recorder.save_response("monitoring_ping", ping_data)
                    uuid = ping_data.get("uuid")
                    print(f"   Device UUID: {uuid}")
                    print(
                        f"   Uptime: {ping_data.get('up_time_seconds', ping_data.get('uptime', 'N/A'))} seconds\n"
                    )
                else:
                    print(f"❌ Monitoring ping failed with status {resp.status}")
                    return
        except Exception as e:
            print(f"❌ Failed to get monitoring ping: {e}")
            return

        if not uuid:
            print("❌ No UUID found in monitoring ping response!")
            return

        # ================================================================
        # 2. Dashboard - Main device status
        # ================================================================
        print("📊 Recording system endpoints...")
        try:
            async with session.get(f"{base_url}/system/{uuid}/dashboard") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    recorder.save_response(f"dashboard_{uuid}", data)
                    print(
                        f"   ✓ Dashboard: Indoor {data.get('indoorTemperature', 'N/A')}°C, "
                        f"Outdoor {data.get('outdoorTemperature', 'N/A')}°C"
                    )
                else:
                    print(f"   ⚠ Dashboard failed: HTTP {resp.status}")
        except Exception as e:
            print(f"   ⚠ Dashboard failed: {e}")

        # ================================================================
        # 3. Thermal Profile - Heating/cooling settings
        # ================================================================
        try:
            async with session.get(f"{base_url}/system/{uuid}/thermalprofile") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    recorder.save_response(f"thermalProfile_{uuid}", data)
                    print(
                        f"   ✓ Thermal Profile: Profile {data.get('temperatureProfile', 'N/A')}"
                    )
                else:
                    print(f"   ⚠ Thermal profile failed: HTTP {resp.status}")
        except Exception as e:
            print(f"   ⚠ Thermal profile failed: {e}")

        # ================================================================
        # 4. Connected Devices - List of all ComfoNet devices
        # ================================================================
        connected_devices = []
        try:
            # Try /system/{uuid}/devices endpoint first
            async with session.get(f"{base_url}/system/{uuid}/devices") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Response can be {"devices": [...]} or just [...]
                    if isinstance(data, dict) and "devices" in data:
                        connected_devices = data["devices"]
                    elif isinstance(data, list):
                        connected_devices = data
                    recorder.save_response(f"devices_{uuid}", data)
                    print(
                        f"   ✓ Devices: Found {len(connected_devices)} connected device(s)"
                    )
                else:
                    print(
                        f"   ⚠ Devices (/system/{uuid}/devices) failed: HTTP {resp.status}"
                    )
        except Exception as e:
            print(f"   ⚠ Devices endpoint failed: {e}")

        # Try alternate endpoint if first one failed
        if not connected_devices:
            try:
                async with session.get(
                    f"{base_url}/system/{uuid}/connectedDevice"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict) and "devices" in data:
                            connected_devices = data["devices"]
                        elif isinstance(data, list):
                            connected_devices = data
                        recorder.save_response(f"connectedDevice_{uuid}", data)
                        print(
                            f"   ✓ Connected Devices (alternate): Found {len(connected_devices)} device(s)"
                        )
            except Exception as e:
                print(f"   ⚠ Connected devices (alternate) failed: {e}")

        # ================================================================
        # 5. Per-Device Data (definitions, telemetry, properties)
        # ================================================================
        # Also include the main device (ComfoClime itself)
        all_devices = connected_devices.copy()

        # Add main device if not already in list
        main_device_in_list = any(d.get("uuid") == uuid for d in all_devices)
        if not main_device_in_list:
            all_devices.append(
                {
                    "uuid": uuid,
                    "displayName": "ComfoClime (Main)",
                    "@modelType": "ComfoClime",
                    "modelTypeId": 20,
                }
            )

        for device in all_devices:
            dev_uuid = device.get("uuid")
            if not dev_uuid:
                continue

            dev_name = device.get("displayName", device.get("name", dev_uuid))
            model_type = device.get("@modelType", device.get("modelType", "Unknown"))
            model_id = device.get("modelTypeId", "?")

            print(f"\n   📱 Device: {dev_name}")
            print(f"      Model: {model_type} (ID: {model_id})")
            print(f"      UUID: {dev_uuid}")

            # ----- Definition data -----
            try:
                async with session.get(
                    f"{base_url}/device/{dev_uuid}/definition"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        recorder.save_response(f"definition_{dev_uuid}", data)
                        print("      ✓ Definition recorded")
                    else:
                        # Try alternate path
                        async with session.get(
                            f"{base_url}/system/{uuid}/connectedDevice/{dev_uuid}/definition"
                        ) as resp2:
                            if resp2.status == 200:
                                data = await resp2.json()
                                recorder.save_response(f"definition_{dev_uuid}", data)
                                print("      ✓ Definition recorded (alternate path)")
            except Exception as e:
                print(f"      ⚠ Definition failed: {e}")

            # ----- Telemetry data -----
            # Record a wide range of telemetry IDs
            telemetry_ids = (
                list(range(0, 51))
                + list(range(4100, 4250))
                + [
                    # Common telemetry IDs from sensor_definitions.py
                    4145,
                    4146,
                    4147,
                    4148,
                    4149,  # Temperatures
                    4201,
                    4202,  # Power
                    4211,
                    4212,
                    4213,  # Air flow
                ]
            )
            telemetry_ids = sorted(set(telemetry_ids))  # Remove duplicates

            telemetry_data = {}
            successful_telemetry = 0
            print(
                f"      Recording telemetry (testing {len(telemetry_ids)} IDs)...",
                end=" ",
                flush=True,
            )

            for tel_id in telemetry_ids:
                try:
                    async with session.get(
                        f"{base_url}/device/{dev_uuid}/telemetry/{tel_id}"
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and data.get("data"):
                                telemetry_data[str(tel_id)] = data
                                successful_telemetry += 1
                except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError):
                    continue

            if telemetry_data:
                recorder.save_response(f"telemetry_{dev_uuid}", telemetry_data)
                print(f"✓ {successful_telemetry} values found")
            else:
                print("(none available)")

            # ----- Property data -----
            # Common property paths from the integration
            property_paths = [
                # From number_definitions.py and other entity definitions
                "1/1/1",
                "1/1/2",
                "1/1/3",
                "1/1/4",
                "1/1/5",
                "29/1/1",
                "29/1/2",
                "29/1/3",
                "29/1/4",
                "29/1/5",
                "29/1/6",
                "29/1/7",
                "29/1/8",
                "29/1/9",
                "29/1/10",
                "29/1/11",
                "29/1/12",
                "29/1/13",
                "29/1/14",
                "29/1/15",
                # Ventilation properties
                "1/6/1",
                "1/6/2",
                "1/6/3",
                # Bypass/Comfort properties
                "1/2/1",
                "1/2/2",
                # Temperature offset properties
                "1/4/1",
                "1/4/2",
                "1/4/3",
            ]

            property_data = {}
            successful_properties = 0
            print(
                f"      Recording properties (testing {len(property_paths)} paths)...",
                end=" ",
                flush=True,
            )

            for path in property_paths:
                try:
                    async with session.get(
                        f"{base_url}/device/{dev_uuid}/property/{path}"
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data and data.get("data"):
                                property_data[path] = data
                                successful_properties += 1
                except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError):
                    continue

            if property_data:
                recorder.save_response(f"property_{dev_uuid}", property_data)
                print(f"✓ {successful_properties} values found")
            else:
                print("(none available)")

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'=' * 60}")
    print(f"✅ Recording complete!")
    print(f"   Files saved to: {responses_dir}")

    # List recorded files
    json_files = list(responses_dir.glob("*.json"))
    print(f"   Total files: {len(json_files)}")
    for f in sorted(json_files):
        size = f.stat().st_size
        print(f"      - {f.name} ({size} bytes)")
    print(f"{'=' * 60}\n")


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def real_or_recorded_api(
    real_device_ip: str, use_real_device: bool, record_responses: bool
):
    """Create a real API or recorded response API based on test mode.

    Returns:
        - Real ComfoClimeAPI if --real-device is set
        - RecordedResponseAPI otherwise (for offline testing)
    """
    if record_responses:
        # Record mode: save responses from real device
        await record_all_responses(real_device_ip, RESPONSES_DIR)
        api = ComfoClimeAPI(real_device_ip)
        yield api
        api.close()

    elif use_real_device:
        # Real device mode
        api = ComfoClimeAPI(real_device_ip)
        yield api
        api.close()

    else:
        # Offline mode: use recorded responses
        if not RESPONSES_DIR.exists() or not any(RESPONSES_DIR.glob("*.json")):
            pytest.skip(
                "No recorded responses found. "
                "Run with --record-responses --device-ip=<IP> first."
            )

        api = RecordedResponseAPI(RESPONSES_DIR)
        await api.async_get_uuid()
        yield api
