#!/usr/bin/env python3
"""Test script to verify the ComfoClime integration imports correctly."""

import sys
import importlib.util

def test_import(module_path, module_name):
    """Test if a module can be imported successfully."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            print(f"❌ Could not create spec for {module_name}")
            return False
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        print(f"✅ Successfully imported {module_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return False

def main():
    """Run import tests for all ComfoClime modules."""
    print("Testing ComfoClime integration imports...")
    
    base_path = "custom_components/comfoclime"
    modules = [
        ("__init__.py", "comfoclime"),
        ("comfoclime_api.py", "comfoclime_api"),
        ("coordinator.py", "coordinator"),
        ("climate.py", "climate"),
        ("config_flow.py", "config_flow"),
        ("sensor.py", "sensor"),
        ("switch.py", "switch"),
        ("number.py", "number"),
        ("select.py", "select"),
        ("fan.py", "fan"),
    ]
    
    success_count = 0
    total_count = len(modules)
    
    for module_file, module_name in modules:
        module_path = f"{base_path}/{module_file}"
        if test_import(module_path, module_name):
            success_count += 1
    
    print(f"\nResult: {success_count}/{total_count} modules imported successfully")
    
    if success_count == total_count:
        print("🎉 All modules imported successfully! Integration is ready for Home Assistant.")
        return 0
    else:
        print("⚠️  Some modules failed to import. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
