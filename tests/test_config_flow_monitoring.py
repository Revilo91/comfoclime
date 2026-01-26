"""Test that monitoring sensors can be disabled/enabled via the options flow.

This test simulates initial platform setup with monitoring enabled, then
simulates the user disabling all monitoring sensors (empty list) and
reloading the platform. Finally it re-enables them and ensures the
monitoring sensor is back.
"""

from custom_components.comfoclime.entity_helper import (
    get_monitoring_sensors,
    is_entity_category_enabled,
    is_entity_enabled,
)
from custom_components.comfoclime.entities.sensor_definitions import MONITORING_SENSORS


def test_monitoring_enable_disable_via_options(mock_config_entry):
    """Verify monitoring category and individual sensors follow options changes.

    This test avoids initializing the full platform (which triggers
    background coordinator refreshes). Instead it asserts the helper
    functions that gate entity creation behave correctly when
    `entry.options` is changed by the options flow.
    """
    entry = mock_config_entry

    # Start with monitoring enabled (default behaviour)
    monitoring_options = [opt["value"] for opt in get_monitoring_sensors()]
    entry.options = {"enabled_monitoring": monitoring_options}

    # Category should be enabled
    assert is_entity_category_enabled(entry.options, "sensors", "monitoring")

    # Pick monitoring sensor definition: uptime (use the actual dataclass)
    sensor_def = MONITORING_SENSORS[0]
    assert is_entity_enabled(entry.options, "sensors", "monitoring", sensor_def)

    # Now simulate user disabling all monitoring sensors
    entry.options = {**entry.options, "enabled_monitoring": []}

    assert not is_entity_category_enabled(entry.options, "sensors", "monitoring")
    assert not is_entity_enabled(entry.options, "sensors", "monitoring", sensor_def)

    # Re-enable again
    entry.options = {**entry.options, "enabled_monitoring": monitoring_options}

    assert is_entity_category_enabled(entry.options, "sensors", "monitoring")
    assert is_entity_enabled(entry.options, "sensors", "monitoring", sensor_def)
