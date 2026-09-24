"""Tests for ComfoClime config_flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.comfoclime.config_flow import (
    DEFAULT_OPTIONS,
    ComfoClimeConfigFlow,
    ComfoClimeOptionsFlow,
)


def _mock_session(response=None, *, get_error=None):
    """Build a mock aiohttp session whose .get() returns/raises as given."""
    session = MagicMock()
    get_cm = MagicMock()
    if get_error is not None:
        get_cm.__aenter__ = AsyncMock(side_effect=get_error)
    else:
        get_cm.__aenter__ = AsyncMock(return_value=response)
    get_cm.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=get_cm)
    return session


@pytest.mark.asyncio
async def test_user_flow_success():
    """Test successful user configuration flow."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock(return_value=None)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"uuid": "test-uuid-123"})

    with patch(
        "custom_components.comfoclime.config_flow.async_get_clientsession",
        return_value=_mock_session(mock_response),
    ):
        result = await flow.async_step_user(user_input={"host": "192.168.1.100"})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "ComfoClime @ 192.168.1.100"
    assert result["data"] == {"host": "192.168.1.100"}
    # Entity selection is the entity registry's job, so the entry carries
    # only performance settings.
    assert result["options"] == DEFAULT_OPTIONS
    assert not [key for key in result["options"] if key.startswith("enabled")]
    flow.async_set_unique_id.assert_awaited_once_with("test-uuid-123")
    flow._abort_if_unique_id_configured.assert_called_once_with(updates={"host": "192.168.1.100"})


@pytest.mark.asyncio
async def test_user_flow_no_uuid():
    """Test user configuration flow when device doesn't return UUID."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})

    with patch(
        "custom_components.comfoclime.config_flow.async_get_clientsession",
        return_value=_mock_session(mock_response),
    ):
        result = await flow.async_step_user(user_input={"host": "192.168.1.100"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "no_uuid"}


@pytest.mark.asyncio
async def test_user_flow_connection_error():
    """Test user configuration flow when connection fails."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    with patch(
        "custom_components.comfoclime.config_flow.async_get_clientsession",
        return_value=_mock_session(get_error=TimeoutError()),
    ):
        result = await flow.async_step_user(user_input={"host": "192.168.1.100"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "cannot_connect"}


@pytest.mark.asyncio
async def test_user_flow_no_response():
    """Test user flow when device returns non-200 status."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()

    mock_response = MagicMock()
    mock_response.status = 500

    with patch("custom_components.comfoclime.config_flow.validate_host") as mock_validate:
        mock_validate.return_value = (True, "")

        with patch(
            "custom_components.comfoclime.config_flow.async_get_clientsession",
            return_value=_mock_session(mock_response),
        ):
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
async def test_reconfigure_flow_success():
    """A matching device (same or unset unique_id) updates the entry's host."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"entry_id": "entry-1"}

    entry = MagicMock()
    entry.unique_id = "test-uuid-123"
    entry.data = {"host": "192.168.1.50"}
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    flow.hass.config_entries.async_reload = AsyncMock()

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"uuid": "test-uuid-123"})

    with patch(
        "custom_components.comfoclime.config_flow.async_get_clientsession",
        return_value=_mock_session(mock_response),
    ):
        result = await flow.async_step_reconfigure(user_input={"host": "192.168.1.100"})

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        entry, data={"host": "192.168.1.100"}, unique_id="test-uuid-123"
    )


@pytest.mark.asyncio
async def test_reconfigure_flow_wrong_device():
    """A host that answers as a different device is rejected, entry is untouched."""
    flow = ComfoClimeConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"entry_id": "entry-1"}

    entry = MagicMock()
    entry.unique_id = "test-uuid-123"
    entry.data = {"host": "192.168.1.50"}
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"uuid": "some-other-uuid"})

    with patch(
        "custom_components.comfoclime.config_flow.async_get_clientsession",
        return_value=_mock_session(mock_response),
    ):
        result = await flow.async_step_reconfigure(user_input={"host": "192.168.1.100"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"host": "wrong_device"}
    flow.hass.config_entries.async_update_entry.assert_not_called()


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
