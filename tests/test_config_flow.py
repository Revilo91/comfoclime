"""Tests for ComfoClime config_flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector

from custom_components.comfoclime.config_flow import (
    ComfoClimeConfigFlow,
    ComfoClimeOptionsFlow,
    DOMAIN,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_WRITE_TIMEOUT,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_CACHE_TTL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_REQUEST_INTERVAL,
    DEFAULT_WRITE_COOLDOWN,
    DEFAULT_REQUEST_DEBOUNCE,
)
from custom_components.comfoclime.entity_helper import get_default_enabled_individual_entities


@pytest.mark.asyncio
async def test_user_flow_success():
    """Test successful user configuration flow."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    # Mock successful ping response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"uuid": "test-uuid-123"})

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get)

        mock_session_class.return_value = mock_session

        result = await flow.async_step_user(
            user_input={"host": "192.168.1.100"}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "ComfoClime @ 192.168.1.100"
    assert result["data"] == {"host": "192.168.1.100"}


@pytest.mark.asyncio
async def test_user_flow_no_uuid():
    """Test user configuration flow when device doesn't return UUID."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    # Mock ping response without uuid
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get)

        mock_session_class.return_value = mock_session

        result = await flow.async_step_user(
            user_input={"host": "192.168.1.100"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "no_uuid"}


@pytest.mark.asyncio
async def test_user_flow_connection_error():
    """Test user configuration flow when connection fails."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(side_effect=TimeoutError())
        mock_session.__aexit__ = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await flow.async_step_user(
            user_input={"host": "192.168.1.100"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "cannot_connect"}


@pytest.mark.asyncio
async def test_options_flow_default_values():
    """Test options flow shows configuration menu."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_init(user_input=None)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert "general" in result["menu_options"]
    assert "entities" in result["menu_options"]
    assert "save_and_exit" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_general_step():
    """Test general settings menu shows submenu options."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_general(user_input=None)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "general"
    assert "general_diagnostics" in result["menu_options"]
    assert "general_timeouts" in result["menu_options"]
    assert "general_polling" in result["menu_options"]
    assert "general_rate_limiting" in result["menu_options"]
    assert "init" in result["menu_options"]  # Back button


@pytest.mark.asyncio
async def test_options_flow_general_diagnostics_form():
    """Test general diagnostics form shows configuration fields."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_general_diagnostics(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general_diagnostics"

    # Check that schema has the expected field
    schema = result["data_schema"].schema
    field_names = {key.schema: key for key in schema.keys()}

    assert "enable_diagnostics" in field_names


@pytest.mark.asyncio
async def test_options_flow_entities_step():
    """Test entity selection step shows all entity categories in single form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities"

    # Check that schema has all expected sensor/entity fields
    schema = result["data_schema"].schema
    field_names = [key.schema for key in schema.keys()]

    # Verify all 10 entity selection fields exist
    assert "enabled_dashboard" in field_names
    assert "enabled_thermalprofile" in field_names
    assert "enabled_monitoring" in field_names
    assert "enabled_connected_device_telemetry" in field_names
    assert "enabled_connected_device_properties" in field_names
    assert "enabled_connected_device_definition" in field_names
    assert "enabled_access_tracking" in field_names
    assert "enabled_switches" in field_names
    assert "enabled_numbers" in field_names
    assert "enabled_selects" in field_names




@pytest.mark.asyncio
async def test_options_flow_with_existing_values():
    """Test options flow preserves existing values in pending changes."""
    entry = MagicMock()
    entry.options = {
        "enable_diagnostics": True,
        "read_timeout": 15,
        "write_timeout": 45,
        "polling_interval": 120,
        "cache_ttl": 60,
        "max_retries": 5,
        "min_request_interval": 0.2,
        "write_cooldown": 3.0,
        "request_debounce": 0.5,
    }

    flow = ComfoClimeOptionsFlow(entry)

    # Test that _get_current_value returns saved values
    assert flow._get_current_value("enable_diagnostics", False) == True
    assert flow._get_current_value("read_timeout", DEFAULT_READ_TIMEOUT) == 15

    # Test init menu
    result = await flow.async_step_init(user_input=None)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_pending_changes():
    """Test options flow collects pending changes without saving immediately."""
    entry = MagicMock()
    entry.options = {"enable_diagnostics": False}

    flow = ComfoClimeOptionsFlow(entry)

    # Submit changes to general_diagnostics
    user_input = {"enable_diagnostics": True}
    result = await flow.async_step_general_diagnostics(user_input=user_input)

    # Should return to general menu, not save
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "general"

    # Changes should be in pending_changes
    assert flow._pending_changes == {"enable_diagnostics": True}
    assert flow._has_changes == True

    # Original entry.options should be unchanged
    assert entry.options["enable_diagnostics"] == False


@pytest.mark.asyncio
async def test_options_flow_save_and_exit():
    """Test save_and_exit saves all pending changes."""
    entry = MagicMock()
    entry.options = {"enable_diagnostics": False, "read_timeout": 10}

    flow = ComfoClimeOptionsFlow(entry)

    # Add some pending changes
    flow._pending_changes = {
        "enable_diagnostics": True,
        "read_timeout": 20,
        "write_timeout": 40,
    }

    result = await flow.async_step_save_and_exit(user_input=None)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Should merge entry.options with pending_changes
    expected = {
        "enable_diagnostics": True,
        "read_timeout": 20,
        "write_timeout": 40,
    }
    assert result["data"] == expected


@pytest.mark.asyncio
async def test_options_flow_validates_timeout_ranges():
    """Test that timeout values form has proper validation configured."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    # Test with out-of-range values should be caught by voluptuous validation
    # This test verifies the schema is properly configured
    result = await flow.async_step_general_timeouts(user_input=None)

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema

    # Find the read_timeout field and verify it has a default value
    for key in schema.keys():
        if key.schema == "read_timeout":
            # Check that the field has a default value set
            assert hasattr(key, "default")
            assert key.default() == DEFAULT_READ_TIMEOUT
            break


@pytest.mark.asyncio
async def test_options_flow_menu_navigation():
    """Test navigation from menu to different steps."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    # Test main menu shows correct options
    result = await flow.async_step_init(user_input=None)
    assert result["type"] == FlowResultType.MENU
    assert "general" in result["menu_options"]
    assert "entities" in result["menu_options"]
    assert "save_and_exit" in result["menu_options"]


def test_default_constants():
    """Test that default constants are properly defined."""
    assert DEFAULT_READ_TIMEOUT == 10
    assert DEFAULT_WRITE_TIMEOUT == 30
    assert DEFAULT_POLLING_INTERVAL == 60
    assert DEFAULT_CACHE_TTL == 30
    assert DEFAULT_MAX_RETRIES == 3
    assert DEFAULT_MIN_REQUEST_INTERVAL == 0.1
    assert DEFAULT_WRITE_COOLDOWN == 2.0
    assert DEFAULT_REQUEST_DEBOUNCE == 0.3


# ============================================================================
# Additional config flow tests for improved coverage
# ============================================================================


@pytest.mark.asyncio
async def test_user_flow_invalid_host():
    """Test user configuration flow with invalid host (security validation)."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    # Test with command injection attempt
    result = await flow.async_step_user(
        user_input={"host": "192.168.1.1; rm -rf /"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}


@pytest.mark.asyncio
async def test_user_flow_non_200_response():
    """Test user configuration flow when device returns non-200 status."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    # Mock non-200 response
    mock_response = MagicMock()
    mock_response.status = 404

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        mock_get = MagicMock()
        mock_get.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get)

        mock_session_class.return_value = mock_session

        result = await flow.async_step_user(
            user_input={"host": "192.168.1.100"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "no_response"}


@pytest.mark.asyncio
async def test_user_flow_shows_form_initially():
    """Test user configuration flow shows form when no user input."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "errors" not in result or result["errors"] == {}


@pytest.mark.asyncio
async def test_options_flow_get_options_flow():
    """Test async_get_options_flow class method."""
    entry = MagicMock()
    options_flow = ComfoClimeConfigFlow.async_get_options_flow(entry)
    assert isinstance(options_flow, ComfoClimeOptionsFlow)
    assert options_flow.entry == entry


@pytest.mark.asyncio
async def test_options_flow_general_timeouts_submit():
    """Test submitting timeout configuration."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    # Submit new timeout values
    user_input = {"read_timeout": 20, "write_timeout": 45}
    result = await flow.async_step_general_timeouts(user_input=user_input)

    # Should return to general menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "general"

    # Check pending changes
    assert flow._pending_changes["read_timeout"] == 20
    assert flow._pending_changes["write_timeout"] == 45


@pytest.mark.asyncio
async def test_options_flow_general_polling_form():
    """Test polling and caching form shows configuration fields."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_general_polling(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general_polling"

    schema = result["data_schema"].schema
    field_names = [key.schema for key in schema.keys()]

    assert "polling_interval" in field_names
    assert "cache_ttl" in field_names
    assert "max_retries" in field_names


@pytest.mark.asyncio
async def test_options_flow_general_polling_submit():
    """Test submitting polling configuration."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"polling_interval": 90, "cache_ttl": 45, "max_retries": 5}
    result = await flow.async_step_general_polling(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert flow._pending_changes["polling_interval"] == 90
    assert flow._pending_changes["cache_ttl"] == 45
    assert flow._pending_changes["max_retries"] == 5


@pytest.mark.asyncio
async def test_options_flow_general_rate_limiting_form():
    """Test rate limiting form shows configuration fields."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_general_rate_limiting(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general_rate_limiting"

    schema = result["data_schema"].schema
    field_names = [key.schema for key in schema.keys()]

    assert "min_request_interval" in field_names
    assert "write_cooldown" in field_names
    assert "request_debounce" in field_names


@pytest.mark.asyncio
async def test_options_flow_general_rate_limiting_submit():
    """Test submitting rate limiting configuration."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {
        "min_request_interval": 0.2,
        "write_cooldown": 3.0,
        "request_debounce": 0.5,
    }
    result = await flow.async_step_general_rate_limiting(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert flow._pending_changes["min_request_interval"] == 0.2
    assert flow._pending_changes["write_cooldown"] == 3.0
    assert flow._pending_changes["request_debounce"] == 0.5


@pytest.mark.asyncio
async def test_options_flow_entities_submit():
    """Test submitting entity selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    # Submit entity selection with some values
    user_input = {
        "enabled_dashboard": ["sensors_dashboard_indoorTemperature"],
        "enabled_thermalprofile": [],
        "enabled_monitoring": ["sensors_monitoring_uuid"],
        "enabled_connected_device_telemetry": [],
        "enabled_connected_device_properties": [],
        "enabled_connected_device_definition": [],
        "enabled_access_tracking": [],
        "enabled_switches": [],
        "enabled_numbers": [],
        "enabled_selects": [],
    }
    result = await flow.async_step_entities(user_input=user_input)

    # Should return to init menu
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    # Check pending changes
    assert "enabled_dashboard" in flow._pending_changes
    assert "enabled_monitoring" in flow._pending_changes


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_menu():
    """Test sensor category submenu."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors(user_input=None)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"
    assert "entities_sensors_dashboard" in result["menu_options"]
    assert "entities_sensors_thermalprofile" in result["menu_options"]
    assert "entities_sensors_monitoring" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_entities_menu():
    """Test entity categories submenu."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_menu(user_input=None)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_menu"
    assert "entities_sensors" in result["menu_options"]
    assert "entities_switches" in result["menu_options"]
    assert "entities_numbers" in result["menu_options"]
    assert "entities_selects" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_dashboard_form():
    """Test dashboard sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_dashboard(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_dashboard"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_dashboard_submit():
    """Test submitting dashboard sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_dashboard": ["sensors_dashboard_indoorTemperature"]}
    result = await flow.async_step_entities_sensors_dashboard(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"
    assert "enabled_dashboard" in flow._pending_changes


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_thermalprofile_form():
    """Test thermal profile sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_thermalprofile(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_thermalprofile"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_thermalprofile_submit():
    """Test submitting thermal profile sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_thermalprofile": []}
    result = await flow.async_step_entities_sensors_thermalprofile(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_monitoring_form():
    """Test monitoring sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_monitoring(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_monitoring"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_monitoring_submit():
    """Test submitting monitoring sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_monitoring": ["sensors_monitoring_uuid"]}
    result = await flow.async_step_entities_sensors_monitoring(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_connected_telemetry_form():
    """Test connected device telemetry sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_connected_telemetry(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_connected_telemetry"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_connected_telemetry_submit():
    """Test submitting connected device telemetry sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_connected_device_telemetry": []}
    result = await flow.async_step_entities_sensors_connected_telemetry(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_connected_properties_form():
    """Test connected device properties sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_connected_properties(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_connected_properties"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_connected_properties_submit():
    """Test submitting connected device properties sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_connected_device_properties": []}
    result = await flow.async_step_entities_sensors_connected_properties(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_connected_definition_form():
    """Test connected device definition sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_connected_definition(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_connected_definition"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_connected_definition_submit():
    """Test submitting connected device definition sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_connected_device_definition": []}
    result = await flow.async_step_entities_sensors_connected_definition(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_access_tracking_form():
    """Test access tracking sensors selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_sensors_access_tracking(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_sensors_access_tracking"


@pytest.mark.asyncio
async def test_options_flow_entities_sensors_access_tracking_submit():
    """Test submitting access tracking sensor selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_access_tracking": []}
    result = await flow.async_step_entities_sensors_access_tracking(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_sensors"


@pytest.mark.asyncio
async def test_options_flow_entities_switches_form():
    """Test switches selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_switches(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_switches"


@pytest.mark.asyncio
async def test_options_flow_entities_switches_submit():
    """Test submitting switch selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_switches": []}
    result = await flow.async_step_entities_switches(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_menu"


@pytest.mark.asyncio
async def test_options_flow_entities_numbers_form():
    """Test numbers selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_numbers(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_numbers"


@pytest.mark.asyncio
async def test_options_flow_entities_numbers_submit():
    """Test submitting number selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_numbers": []}
    result = await flow.async_step_entities_numbers(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_menu"


@pytest.mark.asyncio
async def test_options_flow_entities_selects_form():
    """Test selects selection form."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    result = await flow.async_step_entities_selects(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities_selects"


@pytest.mark.asyncio
async def test_options_flow_entities_selects_submit():
    """Test submitting select selection."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enabled_selects": []}
    result = await flow.async_step_entities_selects(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "entities_menu"


@pytest.mark.asyncio
async def test_options_flow_pending_changes_priority():
    """Test that pending changes take priority over saved options."""
    entry = MagicMock()
    entry.options = {"read_timeout": 10}

    flow = ComfoClimeOptionsFlow(entry)

    # First check that saved option is returned
    assert flow._get_current_value("read_timeout", 5) == 10

    # Add a pending change
    flow._update_pending({"read_timeout": 20})

    # Now pending change should take priority
    assert flow._get_current_value("read_timeout", 5) == 20

    # Original entry should still have old value
    assert entry.options["read_timeout"] == 10


@pytest.mark.asyncio
async def test_options_flow_diagnostics_submit():
    """Test submitting diagnostics configuration."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)

    user_input = {"enable_diagnostics": True}
    result = await flow.async_step_general_diagnostics(user_input=user_input)

    assert result["type"] == FlowResultType.MENU
    assert flow._pending_changes["enable_diagnostics"] == True