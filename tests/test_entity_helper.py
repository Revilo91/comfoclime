"""Tests for entity_helper module."""

import pytest

from custom_components.comfoclime.entity_helper import (
    get_all_entity_categories,
    get_default_enabled_entities,
    get_entity_selection_options,
    is_entity_category_enabled,
)


def test_get_all_entity_categories():
    """Test that get_all_entity_categories returns expected structure."""
    categories = get_all_entity_categories()
    
    assert "sensors" in categories
    assert "switches" in categories
    assert "numbers" in categories
    assert "selects" in categories
    
    # Check sensor subcategories
    assert "dashboard" in categories["sensors"]
    assert "thermalprofile" in categories["sensors"]
    assert "connected_device_telemetry" in categories["sensors"]
    assert "connected_device_properties" in categories["sensors"]
    assert "connected_device_definition" in categories["sensors"]
    assert "access_tracking" in categories["sensors"]
    
    # Check numbers subcategories
    assert "thermal_profile" in categories["numbers"]
    assert "connected_device_properties" in categories["numbers"]
    
    # Check selects subcategories
    assert "thermal_profile" in categories["selects"]
    assert "connected_device_properties" in categories["selects"]


def test_get_entity_selection_options():
    """Test that selection options are properly formatted."""
    options = get_entity_selection_options()
    
    assert isinstance(options, list)
    assert len(options) > 0
    
    # Check that each option has required keys
    for option in options:
        assert "value" in option
        assert "label" in option
        assert isinstance(option["value"], str)
        assert isinstance(option["label"], str)
    
    # Check that specific categories are present
    values = [opt["value"] for opt in options]
    assert "sensors_dashboard" in values
    assert "sensors_thermalprofile" in values
    assert "switches" in values
    assert "numbers_thermal_profile" in values
    assert "selects_thermal_profile" in values


def test_get_default_enabled_entities():
    """Test that default enabled entities returns a set."""
    defaults = get_default_enabled_entities()
    
    assert isinstance(defaults, set)
    assert len(defaults) > 0
    
    # Check that core categories are enabled by default
    assert "sensors_dashboard" in defaults
    assert "sensors_thermalprofile" in defaults
    assert "switches" in defaults
    assert "numbers_thermal_profile" in defaults
    assert "selects_thermal_profile" in defaults


def test_is_entity_category_enabled_with_none():
    """Test that all categories are enabled when options is None or empty."""
    # When enabled_entities is None (not configured yet), everything should be enabled
    assert is_entity_category_enabled({}, "sensors", "dashboard") is True
    assert is_entity_category_enabled({}, "switches") is True
    assert is_entity_category_enabled({}, "numbers", "thermal_profile") is True


def test_is_entity_category_enabled_with_selection():
    """Test entity category checking with explicit selection."""
    options = {
        "enabled_entities": [
            "sensors_dashboard",
            "switches",
        ]
    }
    
    # Enabled categories should return True
    assert is_entity_category_enabled(options, "sensors", "dashboard") is True
    assert is_entity_category_enabled(options, "switches") is True
    
    # Disabled categories should return False
    assert is_entity_category_enabled(options, "sensors", "thermalprofile") is False
    assert is_entity_category_enabled(options, "numbers", "thermal_profile") is False
    assert is_entity_category_enabled(options, "selects", "thermal_profile") is False


def test_is_entity_category_enabled_category_only():
    """Test checking categories without subcategories."""
    options = {
        "enabled_entities": ["switches"]
    }
    
    # Without subcategory parameter
    assert is_entity_category_enabled(options, "switches") is True
    
    # Categories not in the list should be disabled
    options2 = {
        "enabled_entities": ["sensors_dashboard"]
    }
    assert is_entity_category_enabled(options2, "switches") is False


def test_is_entity_category_enabled_empty_selection():
    """Test that empty selection list disables all categories."""
    options = {
        "enabled_entities": []
    }
    
    assert is_entity_category_enabled(options, "sensors", "dashboard") is False
    assert is_entity_category_enabled(options, "switches") is False
    assert is_entity_category_enabled(options, "numbers", "thermal_profile") is False
