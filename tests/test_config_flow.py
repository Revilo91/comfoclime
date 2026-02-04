"""Tests for ComfoClime config_flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.data_entry_flow import FlowResultType

from custom_components.comfoclime.config_flow import (
    ComfoClimeConfigFlow,
    ComfoClimeOptionsFlow,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_WRITE_TIMEOUT,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_CACHE_TTL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_REQUEST_INTERVAL,
    DEFAULT_WRITE_COOLDOWN,
    DEFAULT_REQUEST_DEBOUNCE,
)


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

        result = await flow.async_step_user(user_input={"host": "192.168.1.100"})

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

        result = await flow.async_step_user(user_input={"host": "192.168.1.100"})

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

        result = await flow.async_step_user(user_input={"host": "192.168.1.100"})

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
    assert flow._get_current_value("enable_diagnostics", False)
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
    assert flow._has_changes

    # Original entry.options should be unchanged
    assert not entry.options["enable_diagnostics"]


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
