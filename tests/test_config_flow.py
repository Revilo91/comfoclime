"""Tests for ComfoClime config_flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.comfoclime.config_flow import (
    ComfoClimeConfigFlow,
    ComfoClimeOptionsFlow,
    _apply_bulk_action,
    _split_options_by_model_name,
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
    assert "enabled_connected_device_telemetry" in result["options"]
    assert "enabled_connected_telemetry" not in result["options"]
    assert result["options"]["enabled_access_tracking"] == []


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


def test_split_options_by_model_name_groups_correctly():
    """Options are grouped into ComfoClime, ComfoAirQ and fallback buckets."""
    options = [
        {"value": "a", "label": "📡 ComfoClime • Temp"},
        {"value": "b", "label": "📡 ComfoAirQ • Fan"},
        {"value": "c", "label": "📡 Other Model • Value"},
    ]

    grouped = _split_options_by_model_name(options)

    assert grouped["comfoclime"] == [{"value": "a", "label": "📡 ComfoClime • Temp"}]
    assert grouped["comfoairq"] == [{"value": "b", "label": "📡 ComfoAirQ • Fan"}]
    assert grouped["other"] == [{"value": "c", "label": "📡 Other Model • Value"}]


def test_apply_bulk_action_all_none_custom():
    """Bulk action helper returns expected selection payload."""
    all_values = ["x", "y", "z"]

    assert _apply_bulk_action("all", ["x"], all_values) == ["x", "y", "z"]
    assert _apply_bulk_action("none", ["x"], all_values) == []
    assert _apply_bulk_action("custom", ["x"], all_values) == ["x"]


@pytest.mark.asyncio
async def test_options_entities_bulk_and_model_split_normalization():
    """Entities step stores merged connected-device options and honors bulk actions."""
    entry = MagicMock()
    entry.options = {}

    flow = ComfoClimeOptionsFlow(entry)
    flow.hass = MagicMock()

    telemetry_options = [
        {"value": "sensors_connected_telemetry_t1", "label": "📡 ComfoClime • T1"},
        {"value": "sensors_connected_telemetry_t2", "label": "📡 ComfoAirQ • T2"},
    ]

    with (
        patch("custom_components.comfoclime.config_flow.get_dashboard_sensors", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_thermalprofile_sensors", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_monitoring_sensors", return_value=[]),
        patch(
            "custom_components.comfoclime.config_flow.get_connected_device_telemetry_sensors",
            return_value=telemetry_options,
        ),
        patch("custom_components.comfoclime.config_flow.get_connected_device_properties_sensors", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_connected_device_definition_sensors", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_access_tracking_sensors", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_switches", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_numbers", return_value=[]),
        patch("custom_components.comfoclime.config_flow.get_selects", return_value=[]),
        patch.object(flow, "async_step_init", new=AsyncMock(return_value={"type": FlowResultType.MENU})),
    ):
        result = await flow.async_step_entities(
            {
                "enabled_connected_device_telemetry_comfoclime_bulk_action": "all",
                "enabled_connected_device_telemetry_comfoairq_bulk_action": "none",
            }
        )

    assert result["type"] == FlowResultType.MENU
    assert flow._pending_changes["enabled_connected_device_telemetry"] == ["sensors_connected_telemetry_t1"]
    assert flow._pending_changes["enabled_connected_device_properties"] == []
    assert flow._pending_changes["enabled_connected_device_definition"] == []
    assert flow._pending_changes["enabled_climate"] is True
    assert flow._pending_changes["enabled_fan"] is True
