"""Tests for ComfoClime config_flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.comfoclime.config_flow import (
    DEFAULT_OPTIONS,
    ComfoClimeConfigFlow,
    ComfoClimeOptionsFlow,
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
    # Entity selection is the entity registry's job, so the entry carries
    # only performance settings.
    assert result["options"] == DEFAULT_OPTIONS
    assert not [key for key in result["options"] if key.startswith("enabled")]


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
async def test_user_flow_no_response():
    """Test user flow when device returns non-200 status."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    # Mock failed connection response
    mock_response = MagicMock()
    mock_response.status = 500

    with patch("custom_components.comfoclime.config_flow.validate_host") as mock_validate:
        mock_validate.return_value = (True, "")

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
    assert result["errors"]["host"] == "no_response"


@pytest.mark.asyncio
async def test_user_flow_invalid_host():
    """Test user flow with invalid host."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    with patch("custom_components.comfoclime.config_flow.validate_host") as mock_validate:
        mock_validate.return_value = (False, "Invalid hostname")

        result = await flow.async_step_user(user_input={"host": "invalid..host"})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["host"] == "invalid_host"


@pytest.mark.asyncio
async def test_options_menu_offers_only_performance_sections():
    """The options flow no longer contains any entity-selection step."""
    entry = MagicMock()
    entry.options = dict(DEFAULT_OPTIONS)
    flow = ComfoClimeOptionsFlow(entry)
    flow.hass = MagicMock()

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.MENU
    assert set(result["menu_options"]) == {"timeouts", "polling", "rate_limiting"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("step", "field", "value"),
    [
        ("timeouts", "read_timeout", 25),
        ("polling", "polling_interval", 120),
        ("rate_limiting", "inter_sensor_delay", 1.5),
    ],
)
async def test_options_step_saves_directly(step, field, value):
    """Each section writes straight through; there is no separate save step."""
    entry = MagicMock()
    entry.options = dict(DEFAULT_OPTIONS)
    flow = ComfoClimeOptionsFlow(entry)
    flow.hass = MagicMock()

    form = await getattr(flow, f"async_step_{step}")()
    assert form["type"] == FlowResultType.FORM
    assert form["step_id"] == step

    result = await getattr(flow, f"async_step_{step}")(user_input={field: value})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][field] == value
    # Untouched settings survive the partial submit.
    assert result["data"]["write_timeout"] == DEFAULT_OPTIONS["write_timeout"]


@pytest.mark.asyncio
async def test_options_forms_fall_back_to_defaults_for_missing_keys():
    """An entry saved before a setting existed still renders its form."""
    entry = MagicMock()
    entry.options = {}
    flow = ComfoClimeOptionsFlow(entry)
    flow.hass = MagicMock()

    for step in ("timeouts", "polling", "rate_limiting"):
        result = await getattr(flow, f"async_step_{step}")()
        assert result["type"] == FlowResultType.FORM
