#!/usr/bin/env python3
"""Debug script for ComfoClime Climate entity."""

import asyncio
import sys
import os
sys.path.append('custom_components/comfoclime')

from comfoclime_api import ComfoClimeAPI

async def debug_climate_data():
    """Debug climate data sources."""
    # IP-Adresse hier eintragen
    ip_address = "192.168.1.100"  # ÄNDERN SIE DIESE IP-ADRESSE

    api = ComfoClimeAPI(f"http://{ip_address}")

    print("=== ComfoClime Climate Debug ===")
    print(f"API URL: {api.base_url}")

    print("\n=== Dashboard Data ===")
    try:
        dashboard = await api.async_get_dashboard_data(None)
        print(f"Indoor Temperature: {dashboard.get('indoorTemperature')}")
        print(f"Fan Speed: {dashboard.get('fanSpeed')}")
        print(f"Season: {dashboard.get('season')}")
        print(f"Temperature Profile: {dashboard.get('temperatureProfile')}")
        print(f"Full dashboard keys: {list(dashboard.keys())}")
        print(f"Full dashboard: {dashboard}")
    except Exception as e:
        print(f"Dashboard error: {e}")

    print("\n=== Thermal Profile Data ===")
    try:
        thermal = await api.async_get_thermal_profile(None)
        if thermal:
            heating_data = thermal.get('heatingThermalProfileSeasonData', {})
            cooling_data = thermal.get('coolingThermalProfileSeasonData', {})

            print(f"Heating comfort temperature: {heating_data.get('comfortTemperature')}")
            print(f"Cooling comfort temperature: {cooling_data.get('comfortTemperature')}")
            print(f"Season info: {thermal.get('season', {})}")
            print(f"Temperature info: {thermal.get('temperature', {})}")
            print(f"Full thermal keys: {list(thermal.keys())}")
            print(f"Full thermal: {thermal}")
        else:
            print("No thermal profile data received")
    except Exception as e:
        print(f"Thermal profile error: {e}")

    print("\n=== Device List ===")
    try:
        devices = await api.async_get_devices()
        if devices:
            print(f"Found {len(devices)} devices:")
            for i, device in enumerate(devices):
                print(f"  Device {i+1}: {device.get('displayName', 'Unknown')} (UUID: {device.get('uuid')})")
                print(f"    Type: {device.get('@modelType')}")
                print(f"    Version: {device.get('version')}")
        else:
            print("No devices found")
    except Exception as e:
        print(f"Device list error: {e}")

if __name__ == "__main__":
    print("Starte ComfoClime Debug Script...")
    print("WICHTIG: Bitte ändern Sie die IP-Adresse in der Datei!")
    asyncio.run(debug_climate_data())
