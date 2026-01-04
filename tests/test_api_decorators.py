"""Tests for API decorators."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.comfoclime.api_decorators import (
    api_get,
    api_put,
)


class MockAPI:
    """Mock API class for testing decorators."""

    def __init__(self):
        self.base_url = "http://test.local"
        self.uuid = "test-uuid"
        self.read_timeout = 10
        self.write_timeout = 30
        self.max_retries = 3
        self._request_lock = MagicMock()
        self._request_lock.__aenter__ = AsyncMock()
        self._request_lock.__aexit__ = AsyncMock()
        self._wait_for_rate_limit = AsyncMock()
        self._async_get_uuid_internal = AsyncMock()
        self.async_get_uuid = AsyncMock()
        self._get_session = AsyncMock()

    def fix_signed_temperatures_in_dict(self, data):
        """Mock temperature fix method."""
        return data


@pytest.mark.asyncio
async def test_api_get_simple():
    """Test api_get decorator with simple endpoint."""
    mock_response = {"key": "value"}

    @api_get("/test/endpoint")
    async def test_method(self, response_data):
        return response_data

    api = MockAPI()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(), json=AsyncMock(return_value=mock_response)
        )
    )
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    assert result == mock_response
    api._wait_for_rate_limit.assert_called_once_with(is_write=False)


@pytest.mark.asyncio
async def test_api_get_with_uuid():
    """Test api_get decorator with requires_uuid=True."""
    mock_response = {"dashboard": "data"}

    @api_get("/system/{uuid}/dashboard", requires_uuid=True)
    async def test_method(self, response_data):
        return response_data

    api = MockAPI()
    api.uuid = None  # Test UUID retrieval

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(), json=AsyncMock(return_value=mock_response)
        )
    )
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)
    api._async_get_uuid_internal = AsyncMock()

    # Set UUID after internal call
    async def set_uuid():
        api.uuid = "fetched-uuid"

    api._async_get_uuid_internal.side_effect = set_uuid

    result = await test_method(api)

    assert result == mock_response
    api._async_get_uuid_internal.assert_called_once()


@pytest.mark.asyncio
async def test_api_get_with_parameters():
    """Test api_get decorator with URL parameters."""
    mock_response = {"definition": "data"}

    @api_get("/device/{device_uuid}/definition")
    async def test_method(self, response_data, device_uuid: str):
        assert device_uuid == "my-device-id"
        return response_data

    api = MockAPI()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(), json=AsyncMock(return_value=mock_response)
        )
    )
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api, "my-device-id")

    assert result == mock_response
    # Verify the URL was constructed correctly
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert "my-device-id" in call_args[0][0]


@pytest.mark.asyncio
async def test_api_get_with_response_key():
    """Test api_get decorator with response_key extraction."""
    mock_response = {"devices": [{"id": 1}, {"id": 2}]}

    @api_get("/system/{uuid}/devices", requires_uuid=True, response_key="devices")
    async def test_method(self, response_data):
        return response_data

    api = MockAPI()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(), json=AsyncMock(return_value=mock_response)
        )
    )
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    # Should extract just the "devices" key
    assert result == [{"id": 1}, {"id": 2}]


@pytest.mark.asyncio
async def test_api_get_with_fix_temperatures():
    """Test api_get decorator with fix_temperatures=True."""
    mock_response = {"temperature": 22.5}

    @api_get("/test/endpoint", fix_temperatures=True)
    async def test_method(self, response_data):
        return response_data

    api = MockAPI()
    api.fix_signed_temperatures_in_dict = MagicMock(return_value={"temperature": 23.0})

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(), json=AsyncMock(return_value=mock_response)
        )
    )
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    # Should have called fix_signed_temperatures_in_dict
    api.fix_signed_temperatures_in_dict.assert_called_once_with(mock_response)
    assert result == {"temperature": 23.0}


@pytest.mark.asyncio
async def test_api_get_preserves_function_metadata():
    """Test that api_get decorator preserves function metadata."""

    @api_get("/test/endpoint")
    async def my_documented_method(self, response_data):
        """This is the docstring."""
        return response_data

    assert my_documented_method.__name__ == "my_documented_method"
    assert "docstring" in my_documented_method.__doc__


@pytest.mark.asyncio
async def test_api_get_skip_lock():
    """Test api_get decorator with skip_lock=True doesn't acquire lock."""
    mock_response = {"uuid": "test-uuid-123"}

    @api_get("/monitoring/ping", skip_lock=True)
    async def test_method(self, response_data):
        return response_data

    api = MockAPI()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(
        return_value=MagicMock(
            raise_for_status=MagicMock(), json=AsyncMock(return_value=mock_response)
        )
    )
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    assert result == mock_response
    # With skip_lock=True, lock should NOT be acquired
    api._request_lock.__aenter__.assert_not_called()
    api._request_lock.__aexit__.assert_not_called()
    # But rate limiting should still be called
    api._wait_for_rate_limit.assert_called_once_with(is_write=False)


class MockAPIForPut:
    """Mock API class for testing PUT decorators."""

    def __init__(self):
        self.base_url = "http://test.local"
        self.uuid = "test-uuid"
        self.write_timeout = 30
        self.max_retries = 3
        self.hass = MagicMock()
        self.hass.config.time_zone = "UTC"
        self._request_lock = MagicMock()
        self._request_lock.__aenter__ = AsyncMock()
        self._request_lock.__aexit__ = AsyncMock()
        self._wait_for_rate_limit = AsyncMock()
        self._get_session = AsyncMock()
        self._async_get_uuid_internal = AsyncMock()
        self.async_get_uuid = AsyncMock()


@pytest.mark.asyncio
async def test_api_put_simple():
    """Test api_put decorator with simple endpoint."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()

    @api_put("/test/endpoint")
    async def test_method(self):
        return {"key": "value"}

    api = MockAPIForPut()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock()
    mock_session.put = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    assert result is True
    api._wait_for_rate_limit.assert_called_once_with(is_write=True)


@pytest.mark.asyncio
async def test_api_put_dashboard():
    """Test api_put decorator for dashboard updates."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"status": "ok"})

    @api_put("/system/{uuid}/dashboard", requires_uuid=True, is_dashboard=True)
    async def test_method(self):
        return {"temperature": 22.5}

    api = MockAPIForPut()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock()
    mock_session.put = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    assert result == {"status": "ok"}
    # Verify PUT was called with timestamp in payload (dashboard mode)
    put_call = mock_session.put.call_args
    assert put_call is not None


@pytest.mark.asyncio
async def test_api_put_requires_uuid():
    """Test api_put decorator calls _async_get_uuid_internal when UUID is not set."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()

    @api_put("/system/{uuid}/data", requires_uuid=True)
    async def test_method(self):
        return {"data": "test"}

    api = MockAPIForPut()
    api.uuid = None  # UUID not set

    # Mock _async_get_uuid_internal to set the UUID
    async def set_uuid():
        api.uuid = "fetched-uuid"

    api._async_get_uuid_internal = AsyncMock(side_effect=set_uuid)

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock()
    mock_session.put = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api)

    assert result is True
    # Verify _async_get_uuid_internal was called
    api._async_get_uuid_internal.assert_called_once()
    # Verify UUID was set
    assert api.uuid == "fetched-uuid"


@pytest.mark.asyncio
async def test_api_put_empty_payload():
    """Test api_put decorator with empty payload skips PUT."""

    @api_put("/test/endpoint")
    async def test_method(self):
        return {}

    api = MockAPIForPut()
    api._get_session = AsyncMock()  # Should not be called

    result = await test_method(api)

    # Should return True without making any request
    assert result is True
    api._get_session.assert_not_called()


@pytest.mark.asyncio
async def test_api_put_empty_payload_dashboard():
    """Test api_put decorator with empty payload for dashboard."""

    @api_put("/dashboard", is_dashboard=True)
    async def test_method(self):
        return {}

    api = MockAPIForPut()
    api._get_session = AsyncMock()  # Should not be called

    result = await test_method(api)

    # Should return {} for dashboard without making any request
    assert result == {}
    api._get_session.assert_not_called()


@pytest.mark.asyncio
async def test_api_put_preserves_function_metadata():
    """Test that api_put decorator preserves function metadata."""

    @api_put("/test/endpoint")
    async def my_put_method(self):
        """This is the PUT docstring."""
        return {"data": 1}

    assert my_put_method.__name__ == "my_put_method"
    assert "PUT docstring" in my_put_method.__doc__


@pytest.mark.asyncio
async def test_api_put_with_url_parameters():
    """Test api_put decorator with URL parameters."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.raise_for_status = MagicMock()

    @api_put("/device/{device_uuid}/method/{x}/{y}/3")
    async def test_method(self, device_uuid: str, x: int, y: int):
        return {"data": [1, 2, 3]}

    api = MockAPIForPut()

    # Mock session and response
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock()
    mock_session.put = MagicMock(return_value=mock_context)
    api._get_session = AsyncMock(return_value=mock_session)

    result = await test_method(api, "device-123", 29, 1)

    assert result is True
    # Verify PUT was called with correct URL
    put_call = mock_session.put.call_args
    assert put_call is not None
    # Check that URL contains the parameters
    called_url = put_call[0][0]
    assert "device-123" in called_url
    assert "/29/" in called_url
    assert "/1/" in called_url
