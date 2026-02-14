"""Tests for ComfoClime config_flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.comfoclime.config_flow import ComfoClimeConfigFlow


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
