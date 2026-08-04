"""Tests for ComfoClime service handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.comfoclime.services import (
    DOMAIN,
    _get_any_api,
    _get_api_for_device,
    async_setup_services,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_hass(domain_data: dict | None = None) -> MagicMock:
    """Return a minimal mock hass with hass.data pre-populated."""
    hass = MagicMock()
    hass.data = {DOMAIN: domain_data} if domain_data is not None else {}
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


def _make_api() -> MagicMock:
    """Return a mock ComfoClimeAPI."""
    api = MagicMock()
    api.async_set_property_for_device = AsyncMock()
    api.async_reset_system = AsyncMock()
    return api


def _make_device(entry_ids: set[str] | None = None, identifiers: set | None = None) -> MagicMock:
    """Return a mock device registry entry."""
    device = MagicMock()
    device.config_entries = entry_ids or {"entry1"}
    device.identifiers = identifiers or {(DOMAIN, "device-uuid-123")}
    return device


# ---------------------------------------------------------------------------
# Tests for _get_any_api
# ---------------------------------------------------------------------------


def test_get_any_api_returns_first_api():
    """_get_any_api returns the API from the first loaded entry."""
    api = _make_api()
    hass = _make_hass({"entry1": {"api": api}})
    result = _get_any_api(hass, DOMAIN)
    assert result is api


def test_get_any_api_skips_non_dict_entries():
    """_get_any_api skips non-dict values in domain data."""
    api = _make_api()
    hass = _make_hass({"entry1": "not_a_dict", "entry2": {"api": api}})
    result = _get_any_api(hass, DOMAIN)
    assert result is api


def test_get_any_api_raises_when_no_entry_loaded():
    """_get_any_api raises HomeAssistantError when no entries are loaded."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({})
    with pytest.raises(HomeAssistantError):
        _get_any_api(hass, DOMAIN)


def test_get_any_api_raises_when_domain_missing():
    """_get_any_api raises HomeAssistantError when domain key is absent."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass(None)  # no domain key
    with pytest.raises(HomeAssistantError):
        _get_any_api(hass, DOMAIN)


# ---------------------------------------------------------------------------
# Tests for _get_api_for_device
# ---------------------------------------------------------------------------


def test_get_api_for_device_matches_config_entry():
    """_get_api_for_device returns the API for the device's config entry."""
    api = _make_api()
    hass = _make_hass({"entry1": {"api": api}})
    device = _make_device(entry_ids={"entry1"})
    result = _get_api_for_device(hass, DOMAIN, device)
    assert result is api


def test_get_api_for_device_raises_when_no_matching_entry():
    """_get_api_for_device raises HomeAssistantError when entry is not loaded."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry2": {"api": _make_api()}})
    device = _make_device(entry_ids={"entry1"})  # entry1 is not in domain data
    with pytest.raises(HomeAssistantError):
        _get_api_for_device(hass, DOMAIN, device)


def test_get_api_for_device_raises_when_entry_data_missing_api():
    """_get_api_for_device raises HomeAssistantError when entry data has no api key."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry1": {"coordinator": MagicMock()}})  # no "api" key
    device = _make_device(entry_ids={"entry1"})
    with pytest.raises(HomeAssistantError):
        _get_api_for_device(hass, DOMAIN, device)


# ---------------------------------------------------------------------------
# Tests for async_setup_services
# ---------------------------------------------------------------------------


def test_async_setup_services_registers_all_three_services():
    """async_setup_services registers set_property, reset_system, set_scenario_mode."""
    hass = _make_hass()
    async_setup_services(hass, DOMAIN)

    registered = {call[0][1] for call in hass.services.async_register.call_args_list}
    assert "set_property" in registered
    assert "reset_system" in registered
    assert "set_scenario_mode" in registered
    assert hass.services.async_register.call_count == 3


def test_async_setup_services_uses_correct_domain():
    """async_setup_services registers services under the given domain."""
    hass = _make_hass()
    async_setup_services(hass, DOMAIN)

    domains = {call[0][0] for call in hass.services.async_register.call_args_list}
    assert domains == {DOMAIN}


# ---------------------------------------------------------------------------
# Tests for set_property handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_property_calls_api():
    """set_property handler writes property via API."""
    api = _make_api()
    hass = _make_hass({"entry1": {"api": api}})

    device = _make_device(entry_ids={"entry1"}, identifiers={(DOMAIN, "dev-uuid")})

    call = MagicMock()
    call.data = {
        "device_id": "ha-device-id",
        "path": "29/1/10",
        "value": 22.0,
        "byte_count": 2,
        "signed": True,
        "faktor": 1.0,
    }

    async_setup_services(hass, DOMAIN)
    # Extract the registered set_property handler
    handler = None
    for c in hass.services.async_register.call_args_list:
        if c[0][1] == "set_property":
            handler = c[0][2]
            break
    assert handler is not None

    with patch("homeassistant.helpers.device_registry.async_get") as mock_dr:
        mock_dr.return_value.async_get.return_value = device
        await handler(call)

    api.async_set_property_for_device.assert_called_once()


@pytest.mark.asyncio
async def test_set_property_invalid_path_raises():
    """set_property handler raises HomeAssistantError for an invalid path."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry1": {"api": _make_api()}})
    call = MagicMock()
    call.data = {
        "device_id": "ha-device-id",
        "path": "invalid_path",
        "value": 22.0,
        "byte_count": 2,
        "signed": True,
        "faktor": 1.0,
    }

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_property")

    with pytest.raises(HomeAssistantError, match="Ungültiger Property-Pfad"):
        await handler(call)


@pytest.mark.asyncio
async def test_set_property_invalid_byte_count_raises():
    """set_property handler raises HomeAssistantError for byte_count not in (1,2)."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry1": {"api": _make_api()}})
    call = MagicMock()
    call.data = {
        "device_id": "ha-device-id",
        "path": "29/1/10",
        "value": 22.0,
        "byte_count": 4,  # invalid
        "signed": True,
        "faktor": 1.0,
    }

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_property")

    with pytest.raises(HomeAssistantError, match="byte_count"):
        await handler(call)


@pytest.mark.asyncio
async def test_set_property_device_not_found_raises():
    """set_property handler raises HomeAssistantError when device is not in registry."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry1": {"api": _make_api()}})
    call = MagicMock()
    call.data = {
        "device_id": "nonexistent",
        "path": "29/1/10",
        "value": 22.0,
        "byte_count": 1,
        "signed": False,
        "faktor": 1.0,
    }

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_property")

    with patch("homeassistant.helpers.device_registry.async_get") as mock_dr:
        mock_dr.return_value.async_get.return_value = None
        with pytest.raises(HomeAssistantError, match="Gerät nicht gefunden"):
            await handler(call)


@pytest.mark.asyncio
async def test_set_property_wrong_domain_raises():
    """set_property handler raises HomeAssistantError when device belongs to other integration."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry1": {"api": _make_api()}})
    call = MagicMock()
    call.data = {
        "device_id": "ha-device-id",
        "path": "29/1/10",
        "value": 22.0,
        "byte_count": 1,
        "signed": False,
        "faktor": 1.0,
    }

    device = _make_device(entry_ids={"entry1"}, identifiers={("other_integration", "dev-uuid")})

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_property")

    with patch("homeassistant.helpers.device_registry.async_get") as mock_dr:
        mock_dr.return_value.async_get.return_value = device
        with pytest.raises(HomeAssistantError, match="gehört nicht"):
            await handler(call)


# ---------------------------------------------------------------------------
# Tests for reset_system handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_system_calls_api():
    """reset_system handler calls api.async_reset_system."""
    api = _make_api()
    hass = _make_hass({"entry1": {"api": api}})
    call = MagicMock()

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")
    await handler(call)

    api.async_reset_system.assert_called_once()


@pytest.mark.asyncio
async def test_reset_system_no_integration_loaded_raises():
    """reset_system handler raises HomeAssistantError when no entry is loaded."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({})
    call = MagicMock()

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")

    with pytest.raises(HomeAssistantError):
        await handler(call)


@pytest.mark.asyncio
async def test_reset_system_propagates_timeout_error():
    """reset_system handler wraps TimeoutError in HomeAssistantError."""
    from homeassistant.exceptions import HomeAssistantError

    api = _make_api()
    api.async_reset_system.side_effect = TimeoutError()
    hass = _make_hass({"entry1": {"api": api}})
    call = MagicMock()

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")

    with pytest.raises(HomeAssistantError, match="Neustart"):
        await handler(call)


# ---------------------------------------------------------------------------
# Tests for set_scenario_mode handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_scenario_mode_activates_mode():
    """set_scenario_mode handler delegates to climate entity."""
    climate_entity = MagicMock()
    climate_entity.entity_id = "climate.comfoclime"
    climate_entity.async_set_scenario_mode = AsyncMock()

    hass = _make_hass({"entry1": {"climate_entities": [climate_entity]}})
    call = MagicMock()
    call.data = {
        "entity_id": "climate.comfoclime",
        "scenario": "cooking",
        "duration": None,
        "start_delay": None,
    }
    call.data.get = lambda key, default=None: (
        call.data.get.__wrapped__(key, default)
        if hasattr(call.data.get, "__wrapped__")
        else call.data.get(key)
        if key in call.data
        else default
    )

    # Use a real dict for call.data to simplify
    call.data = {
        "entity_id": "climate.comfoclime",
        "scenario": "cooking",
    }
    # Patch .get to return None for optional fields
    original = dict(call.data)
    call.data = MagicMock()
    call.data.__getitem__ = lambda _, key: original[key]
    call.data.get = lambda key, default=None: original.get(key, default)

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_scenario_mode")
    await handler(call)

    climate_entity.async_set_scenario_mode.assert_called_once_with(
        scenario_mode="cooking",
        duration=None,
        start_delay=None,
    )


@pytest.mark.asyncio
async def test_set_scenario_mode_entity_not_found_raises():
    """set_scenario_mode raises HomeAssistantError when entity is not found."""
    from homeassistant.exceptions import HomeAssistantError

    hass = _make_hass({"entry1": {"climate_entities": []}})

    original = {"entity_id": "climate.nonexistent", "scenario": "party"}
    call = MagicMock()
    call.data = MagicMock()
    call.data.__getitem__ = lambda _, key: original[key]
    call.data.get = lambda key, default=None: original.get(key, default)

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_scenario_mode")

    with pytest.raises(HomeAssistantError, match="not found"):
        await handler(call)


@pytest.mark.asyncio
async def test_set_scenario_mode_uses_hass_data_at_call_time():
    """set_scenario_mode reads hass.data when called, not when registered.

    This verifies that after a config entry reload (where hass.data is updated)
    the handler finds the new climate entities, not stale ones from before the reload.
    """
    hass = _make_hass({})  # empty at registration time

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_scenario_mode")

    # Simulate config entry reload: new climate entity appears in hass.data
    climate_entity = MagicMock()
    climate_entity.entity_id = "climate.comfoclime"
    climate_entity.async_set_scenario_mode = AsyncMock()
    hass.data[DOMAIN] = {"entry1": {"climate_entities": [climate_entity]}}

    original = {"entity_id": "climate.comfoclime", "scenario": "boost"}
    call = MagicMock()
    call.data = MagicMock()
    call.data.__getitem__ = lambda _, key: original[key]
    call.data.get = lambda key, default=None: original.get(key, default)

    await handler(call)

    climate_entity.async_set_scenario_mode.assert_called_once()


@pytest.mark.asyncio
async def test_reset_system_uses_hass_data_at_call_time():
    """reset_system reads hass.data when called, not when registered.

    This verifies that after a config entry reload the handler uses the new API.
    """
    hass = _make_hass({})  # empty at registration time

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")

    # Simulate config entry reload: new api appears in hass.data
    api = _make_api()
    hass.data[DOMAIN] = {"entry1": {"api": api}}

    call = MagicMock()
    await handler(call)

    api.async_reset_system.assert_called_once()
