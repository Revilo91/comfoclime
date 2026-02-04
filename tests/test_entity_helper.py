"""Tests for entity_helper module."""


from custom_components.comfoclime.entity_helper import (
    _make_sensor_id,
    get_all_entity_categories,
    get_default_enabled_entities,
    get_default_enabled_individual_entities,
    get_entity_selection_options,
    get_individual_entity_options,
    is_entity_category_enabled,
    is_entity_enabled,
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
    options = {"enabled_entities": ["switches"]}

    # Without subcategory parameter
    assert is_entity_category_enabled(options, "switches") is True

    # Categories not in the list should be disabled
    options2 = {"enabled_entities": ["sensors_dashboard"]}
    assert is_entity_category_enabled(options2, "switches") is False


def test_is_entity_category_enabled_empty_selection():
    """Test that empty selection list disables all categories."""
    options = {"enabled_entities": []}

    assert is_entity_category_enabled(options, "sensors", "dashboard") is False
    assert is_entity_category_enabled(options, "switches") is False
    assert is_entity_category_enabled(options, "numbers", "thermal_profile") is False


def test_make_sensor_id_with_key():
    """Test _make_sensor_id with key field."""
    sensor_def = {"key": "indoorTemperature", "name": "Indoor Temperature"}
    result = _make_sensor_id("sensors", "dashboard", sensor_def)
    assert result == "sensors_dashboard_indoorTemperature"


def test_make_sensor_id_with_telemetry_id():
    """Test _make_sensor_id with telemetry_id field."""
    sensor_def = {"telemetry_id": 4193, "name": "Supply Air Temperature"}
    result = _make_sensor_id("sensors", "connected_telemetry", sensor_def)
    assert result == "sensors_connected_telemetry_telem_4193"


def test_make_sensor_id_with_path():
    """Test _make_sensor_id with path field."""
    sensor_def = {"path": "30/1/18", "name": "Ventilation Disbalance"}
    result = _make_sensor_id("sensors", "connected_properties", sensor_def)
    assert result == "sensors_connected_properties_prop_30_1_18"


def test_make_sensor_id_with_property():
    """Test _make_sensor_id with property field."""
    sensor_def = {"property": "29/1/2", "name": "RMOT Heating Threshold"}
    result = _make_sensor_id("numbers", "connected_properties", sensor_def)
    assert result == "numbers_connected_properties_prop_29_1_2"


def test_make_sensor_id_with_metric():
    """Test _make_sensor_id with coordinator and metric fields."""
    sensor_def = {
        "coordinator": "Dashboard",
        "metric": "per_minute",
        "name": "Dashboard Accesses",
    }
    result = _make_sensor_id("sensors", "access_tracking", sensor_def)
    assert result == "sensors_access_tracking_dashboard_per_minute"


def test_get_individual_entity_options():
    """Test that individual entity options are properly formatted as flat list."""
    options = get_individual_entity_options()

    assert isinstance(options, list)
    assert len(options) > 0

    # Check that each option has required keys (flat structure, not grouped)
    for option in options:
        assert "label" in option, "Option should have 'label' key"
        assert "value" in option, "Option should have 'value' key"
        assert isinstance(option["label"], str), "Option label should be string"
        assert isinstance(option["value"], str), "Option value should be string"

        # Check that label has emoji prefix (verifies user-friendly formatting)
        # Note: Emojis are: 📊 Dashboard, 🌡️ Thermal, 📡 Device telemetry, 🔧 Device property,
        # 📋 Device definition, 🔍 Access tracking, 🔌 Switch, 🔢 Number, 📝 Select
        has_emoji = any(char in option["label"] for char in "📊🌡️📡🔧📋🔍🔌🔢📝")
        assert has_emoji, f"Option label '{option['label']}' should have emoji prefix"

    # Check that some specific entities are present (flat structure)
    all_values = [opt["value"] for opt in options]

    assert any("sensors_dashboard_indoorTemperature" in v for v in all_values), (
        "Should contain indoor temperature sensor"
    )
    assert any("switches_all_" in v for v in all_values), "Should contain switches"
    assert len(all_values) > 10, "Should have multiple entities"


def test_get_default_enabled_individual_entities():
    """Test that default enabled individual entities returns a set."""
    defaults = get_default_enabled_individual_entities()

    assert isinstance(defaults, set)
    assert len(defaults) > 0

    # Check that some core entities are enabled by default
    assert any("sensors_dashboard_indoorTemperature" in d for d in defaults)
    assert any("switches_all_" in d for d in defaults)

    # Check that diagnostic sensors are NOT enabled by default
    # (access tracking sensors should not be in defaults)
    assert not any("access_tracking" in d and "per_minute" in d for d in defaults)


def test_is_entity_enabled_with_none():
    """Test that all entities are enabled when options is None or empty."""
    sensor_def = {"key": "indoorTemperature", "name": "Indoor Temperature"}

    # When enabled_entities is None (not configured yet), everything should be enabled
    assert is_entity_enabled({}, "sensors", "dashboard", sensor_def) is True


def test_is_entity_enabled_individual_selected():
    """Test entity checking when individual entity is selected."""
    sensor_def = {"key": "indoorTemperature", "name": "Indoor Temperature"}
    options = {"enabled_entities": ["sensors_dashboard_indoorTemperature"]}

    assert is_entity_enabled(options, "sensors", "dashboard", sensor_def) is True


def test_is_entity_enabled_individual_not_selected():
    """Test entity checking when individual entity is NOT selected."""
    sensor_def = {"key": "indoorTemperature", "name": "Indoor Temperature"}
    other_sensor_def = {"key": "outdoorTemperature", "name": "Outdoor Temperature"}
    options = {"enabled_entities": ["sensors_dashboard_outdoorTemperature"]}

    # indoor temp is not selected, should be False
    assert is_entity_enabled(options, "sensors", "dashboard", sensor_def) is False
    # outdoor temp is selected, should be True
    assert is_entity_enabled(options, "sensors", "dashboard", other_sensor_def) is True


def test_is_entity_enabled_category_backward_compat():
    """Test backward compatibility with old category-based selection."""
    sensor_def = {"key": "indoorTemperature", "name": "Indoor Temperature"}
    options = {
        "enabled_entities": ["sensors_dashboard"]  # Old-style category selection
    }

    # Should enable all entities in that category for backward compatibility
    assert is_entity_enabled(options, "sensors", "dashboard", sensor_def) is True


def test_is_entity_enabled_mixed_selection():
    """Test that individual selection takes precedence over category."""
    sensor_def = {"key": "indoorTemperature", "name": "Indoor Temperature"}
    other_sensor_def = {"key": "outdoorTemperature", "name": "Outdoor Temperature"}
    options = {
        "enabled_entities": [
            "sensors_dashboard",  # Category
            "sensors_dashboard_outdoorTemperature",  # Individual entity
        ]
    }

    # When individual entities are present, category is ignored
    # Only outdoor temp is explicitly enabled
    assert is_entity_enabled(options, "sensors", "dashboard", sensor_def) is False
    assert is_entity_enabled(options, "sensors", "dashboard", other_sensor_def) is True


def test_is_entity_category_enabled_with_individual_entities():
    """Test that category check works when individual entities are selected."""
    options = {
        "enabled_entities": [
            "sensors_dashboard_indoorTemperature",
            "sensors_dashboard_outdoorTemperature",
        ]
    }

    # Category should be enabled if any individual entities from it are enabled
    assert is_entity_category_enabled(options, "sensors", "dashboard") is True
    # Other categories should be disabled
    assert is_entity_category_enabled(options, "sensors", "thermalprofile") is False
