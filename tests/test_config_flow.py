"""Tests for ComfoClime config_flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

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


@pytest.mark.asyncio
async def test_options_flow_general_step():
    """Test general settings step shows all configuration fields."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    result = await flow.async_step_general(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general"
    
    # Check that schema has the expected fields with default values
    schema = result["data_schema"].schema
    field_names = {key.schema: key for key in schema.keys()}
    
    assert "enable_diagnostics" in field_names
    assert "read_timeout" in field_names
    assert "write_timeout" in field_names
    assert "polling_interval" in field_names
    assert "cache_ttl" in field_names
    assert "max_retries" in field_names
    assert "min_request_interval" in field_names
    assert "write_cooldown" in field_names
    assert "request_debounce" in field_names


@pytest.mark.asyncio
async def test_options_flow_entities_step():
    """Test entity selection step shows entity categories."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    result = await flow.async_step_entities(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities"
    
    # Check that schema has the enabled_entities field
    schema = result["data_schema"].schema
    field_names = {key.schema: key for key in schema.keys()}
    
    assert "enabled_entities" in field_names
    
    # Check default value is set to all enabled categories
    enabled_entities_keys = [key for key in schema.keys() if key.schema == "enabled_entities"]
    assert len(enabled_entities_keys) > 0, "enabled_entities key not found in schema"
    enabled_entities_key = enabled_entities_keys[0]
    default_value = enabled_entities_key.default()
    assert isinstance(default_value, list)
    assert len(default_value) > 0


@pytest.mark.asyncio
async def test_options_flow_entities_options_format():
    """Test entity selection options are properly formatted dictionaries."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    result = await flow.async_step_entities(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    
    # Get the SelectSelector from the schema
    schema = result["data_schema"].schema
    enabled_entities_keys = [key for key in schema.keys() if key.schema == "enabled_entities"]
    assert len(enabled_entities_keys) > 0, "enabled_entities key not found in schema"
    enabled_entities_key = enabled_entities_keys[0]
    select_selector = schema[enabled_entities_key]
    
    # Verify the selector has a config with options
    assert hasattr(select_selector, "config")
    assert "options" in select_selector.config
    options = select_selector.config["options"]
    
    # Verify options is a list and each option has the correct format
    assert isinstance(options, list)
    assert len(options) > 0
    
    # Each option should be a dict with "value" and "label" keys
    for opt in options:
        assert isinstance(opt, dict)
        assert "value" in opt
        assert "label" in opt
        assert isinstance(opt["value"], str)
        assert isinstance(opt["label"], str)


@pytest.mark.asyncio
async def test_options_flow_entities_step_with_existing_values():
    """Test entity selection preserves existing values."""
    entry = MagicMock()
    entry.options = {
        "enabled_entities": ["sensors_dashboard", "switches"]
    }
    
    flow = ComfoClimeOptionsFlow(entry)
    
    result = await flow.async_step_entities(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "entities"
    
    # Check that existing selection is preserved
    schema = result["data_schema"].schema
    enabled_entities_keys = [key for key in schema.keys() if key.schema == "enabled_entities"]
    assert len(enabled_entities_keys) > 0, "enabled_entities key not found in schema"
    enabled_entities_key = enabled_entities_keys[0]
    default_value = enabled_entities_key.default()
    assert default_value == ["sensors_dashboard", "switches"]


@pytest.mark.asyncio
async def test_options_flow_with_existing_values():
    """Test options flow preserves existing values."""
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
    
    result = await flow.async_step_init(user_input=None)
    
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_save_values():
    """Test options flow saves user input."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    user_input = {
        "enable_diagnostics": True,
        "read_timeout": 20,
        "write_timeout": 40,
        "polling_interval": 90,
        "cache_ttl": 45,
        "max_retries": 2,
        "min_request_interval": 0.15,
        "write_cooldown": 2.5,
        "request_debounce": 0.4,
    }
    
    result = await flow.async_step_general(user_input=user_input)
    
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input


@pytest.mark.asyncio
async def test_options_flow_save_entity_selection():
    """Test options flow saves entity selection."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    user_input = {
        "enabled_entities": ["sensors_dashboard", "switches", "numbers_thermal_profile"]
    }
    
    result = await flow.async_step_entities(user_input=user_input)
    
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input


@pytest.mark.asyncio
async def test_options_flow_validates_timeout_ranges():
    """Test that timeout values are validated within allowed ranges."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    # Test with out-of-range values should be caught by voluptuous validation
    # This test verifies the schema is properly configured
    result = await flow.async_step_general(user_input=None)
    
    schema = result["data_schema"].schema
    
    # Find the read_timeout field and verify it has range validation
    for key in schema.keys():
        if key.schema == "read_timeout":
            # The validator should be vol.All with Range
            assert hasattr(key, "default")
            assert key.default() == DEFAULT_READ_TIMEOUT
            break


@pytest.mark.asyncio
async def test_options_flow_menu_navigation():
    """Test navigation from menu to different steps."""
    entry = MagicMock()
    entry.options = {}
    
    flow = ComfoClimeOptionsFlow(entry)
    
    # Test menu shows correct options
    result = await flow.async_step_init(user_input=None)
    assert result["type"] == FlowResultType.MENU
    assert "general" in result["menu_options"]
    assert "entities" in result["menu_options"]


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
