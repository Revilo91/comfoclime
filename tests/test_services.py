"""Tests for ComfoClime service handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.helpers.config_validation as cv
import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.comfoclime.services import (
    DOMAIN,
    _get_any_api,
    _get_api_for_device,
    async_setup_services,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_entry(entry_id: str, api: MagicMock) -> MagicMock:
    """Return a mock loaded config entry carrying *api* in its runtime data."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.runtime_data.api = api
    return entry


def _make_hass(apis: dict[str, MagicMock] | None = None) -> MagicMock:
    """Return a minimal mock hass whose loaded entries carry the given APIs.

    The loaded list is evaluated at call time (``hass.loaded_entries``), so
    tests can add entries after services were registered.
    """
    hass = MagicMock()
    hass.loaded_entries = [_make_entry(entry_id, api) for entry_id, api in (apis or {}).items()]
    hass.config_entries.async_loaded_entries.side_effect = lambda domain: (
        list(hass.loaded_entries) if domain == DOMAIN else []
    )
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


def _make_api() -> MagicMock:
    """Return a mock ComfoClimeAPI."""
    api = MagicMock()
    api.async_set_property_for_device = AsyncMock()
    api.async_reset_system = AsyncMock()
    return api


def _make_device(entry_id: str = "entry1", identifiers: set | None = None) -> MagicMock:
    """Return a mock device registry entry.

    Spec'd without ``config_entries``: that property is deprecated since HA 2026.10
    (devices belong to exactly one entry), so reading it must fail the test.
    """
    device = MagicMock(spec=["config_entry_id", "identifiers"])
    device.config_entry_id = entry_id
    device.identifiers = identifiers or {(DOMAIN, "device-uuid-123")}
    return device


# ---------------------------------------------------------------------------
# Tests for _get_any_api
# ---------------------------------------------------------------------------


def test_get_any_api_returns_first_api():
    """_get_any_api returns the API from the first loaded entry."""
    api = _make_api()
    hass = _make_hass({"entry1": api})
    result = _get_any_api(hass, DOMAIN)
    assert result is api


def test_get_any_api_queries_loaded_entries_of_domain():
    """_get_any_api only looks at loaded entries of the requested domain."""
    hass = _make_hass({"entry1": _make_api()})
    _get_any_api(hass, DOMAIN)
    hass.config_entries.async_loaded_entries.assert_called_once_with(DOMAIN)


def test_get_any_api_raises_when_no_entry_loaded():
    """_get_any_api raises HomeAssistantError when no entries are loaded."""
    hass = _make_hass({})
    with pytest.raises(HomeAssistantError) as exc_info:
        _get_any_api(hass, DOMAIN)
    assert exc_info.value.translation_key == "no_entry_loaded"


def test_get_any_api_raises_for_other_domain():
    """_get_any_api raises HomeAssistantError when nothing of the domain is loaded."""
    hass = _make_hass({"entry1": _make_api()})
    with pytest.raises(HomeAssistantError) as exc_info:
        _get_any_api(hass, "other_domain")
    assert exc_info.value.translation_key == "no_entry_loaded"


# ---------------------------------------------------------------------------
# Tests for _get_api_for_device
# ---------------------------------------------------------------------------


def test_get_api_for_device_matches_config_entry():
    """_get_api_for_device returns the API for the device's config entry."""
    api = _make_api()
    hass = _make_hass({"entry1": api})
    device = _make_device(entry_id="entry1")
    result = _get_api_for_device(hass, DOMAIN, device)
    assert result is api


def test_get_api_for_device_raises_when_no_matching_entry():
    """_get_api_for_device raises HomeAssistantError when entry is not loaded."""
    hass = _make_hass({"entry2": _make_api()})
    device = _make_device(entry_id="entry1")  # entry1 is not in domain data
    with pytest.raises(HomeAssistantError) as exc_info:
        _get_api_for_device(hass, DOMAIN, device)
    assert exc_info.value.translation_key == "device_entry_not_loaded"


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
    hass = _make_hass({"entry1": api})

    device = _make_device(entry_id="entry1", identifiers={(DOMAIN, "dev-uuid")})

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
    hass = _make_hass({"entry1": _make_api()})
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

    with pytest.raises(ServiceValidationError) as exc_info:
        await handler(call)
    assert exc_info.value.translation_key == "invalid_property_path"


@pytest.mark.asyncio
async def test_set_property_invalid_byte_count_raises():
    """set_property handler raises HomeAssistantError for byte_count not in (1,2)."""
    hass = _make_hass({"entry1": _make_api()})
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

    with pytest.raises(ServiceValidationError) as exc_info:
        await handler(call)
    assert exc_info.value.translation_key == "invalid_byte_count"


@pytest.mark.asyncio
async def test_set_property_device_not_found_raises():
    """set_property handler raises HomeAssistantError when device is not in registry."""
    hass = _make_hass({"entry1": _make_api()})
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
        with pytest.raises(ServiceValidationError) as exc_info:
            await handler(call)
    assert exc_info.value.translation_key == "device_not_found"


@pytest.mark.asyncio
async def test_set_property_wrong_domain_raises():
    """set_property handler raises HomeAssistantError when device belongs to other integration."""
    hass = _make_hass({"entry1": _make_api()})
    call = MagicMock()
    call.data = {
        "device_id": "ha-device-id",
        "path": "29/1/10",
        "value": 22.0,
        "byte_count": 1,
        "signed": False,
        "faktor": 1.0,
    }

    device = _make_device(entry_id="entry1", identifiers={("other_integration", "dev-uuid")})

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "set_property")

    with patch("homeassistant.helpers.device_registry.async_get") as mock_dr:
        mock_dr.return_value.async_get.return_value = device
        with pytest.raises(ServiceValidationError) as exc_info:
            await handler(call)
    assert exc_info.value.translation_key == "device_wrong_integration"


# ---------------------------------------------------------------------------
# Tests for reset_system handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_system_calls_api():
    """reset_system handler calls api.async_reset_system."""
    api = _make_api()
    hass = _make_hass({"entry1": api})
    call = MagicMock()

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")
    await handler(call)

    api.async_reset_system.assert_called_once()


@pytest.mark.asyncio
async def test_reset_system_no_integration_loaded_raises():
    """reset_system handler raises HomeAssistantError when no entry is loaded."""
    hass = _make_hass({})
    call = MagicMock()

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")

    with pytest.raises(HomeAssistantError):
        await handler(call)


@pytest.mark.asyncio
async def test_reset_system_propagates_timeout_error():
    """reset_system handler wraps TimeoutError in HomeAssistantError."""
    api = _make_api()
    api.async_reset_system.side_effect = TimeoutError()
    hass = _make_hass({"entry1": api})
    call = MagicMock()

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")

    with pytest.raises(HomeAssistantError) as exc_info:
        await handler(call)
    assert exc_info.value.translation_key == "reset_failed"


# ---------------------------------------------------------------------------
# Tests for set_scenario_mode (platform entity service)
# ---------------------------------------------------------------------------


def _register_and_get_scenario_kwargs() -> dict:
    """Run async_setup_services and return kwargs of the platform entity service registration."""
    hass = _make_hass()
    with patch("custom_components.comfoclime.services.async_register_platform_entity_service") as register:
        async_setup_services(hass, DOMAIN)
    register.assert_called_once()
    args, kwargs = register.call_args
    assert args == (hass, DOMAIN, "set_scenario_mode")
    return kwargs


def test_set_scenario_mode_registered_as_platform_entity_service():
    """set_scenario_mode is a climate entity service calling the entity method."""
    kwargs = _register_and_get_scenario_kwargs()

    assert kwargs["entity_domain"] == "climate"
    assert kwargs["func"] == "async_set_scenario_mode"
    assert cv.is_entity_service_schema(kwargs["schema"])


def test_set_scenario_mode_not_registered_as_plain_service():
    """The plain-service handler for set_scenario_mode is gone."""
    hass = _make_hass()
    with patch("custom_components.comfoclime.services.async_register_platform_entity_service"):
        async_setup_services(hass, DOMAIN)

    registered = {call[0][1] for call in hass.services.async_register.call_args_list}
    assert registered == {"set_property", "reset_system"}


@pytest.mark.parametrize("scenario", ["cooking", "party", "away", "scenario_boost"])
def test_set_scenario_mode_schema_accepts_preset_names(scenario):
    """Schema accepts every scenario the climate entity understands."""
    schema = _register_and_get_scenario_kwargs()["schema"]

    data = schema({"entity_id": "climate.comfoclime", "scenario": scenario})

    assert data["scenario"] == scenario
    assert data["entity_id"] == ["climate.comfoclime"]


def test_set_scenario_mode_schema_maps_boost_alias():
    """services.yaml used to offer 'boost'; it maps to the real 'scenario_boost' preset."""
    schema = _register_and_get_scenario_kwargs()["schema"]

    data = schema({"entity_id": "climate.comfoclime", "scenario": "boost"})

    assert data["scenario"] == "scenario_boost"


def test_set_scenario_mode_schema_accepts_entity_id_in_data_and_target_forms():
    """Legacy `data: {entity_id: ...}` and area/device targets pass the entity schema."""
    schema = _register_and_get_scenario_kwargs()["schema"]

    assert schema({"entity_id": "climate.a", "scenario": "party"})["entity_id"] == ["climate.a"]
    assert schema({"entity_id": ["climate.a", "climate.b"], "scenario": "party"})["entity_id"] == [
        "climate.a",
        "climate.b",
    ]
    assert schema({"area_id": "kitchen", "scenario": "party"})["area_id"] == ["kitchen"]


def test_set_scenario_mode_schema_optional_fields():
    """duration and start_delay are optional and validated."""
    schema = _register_and_get_scenario_kwargs()["schema"]

    data = schema(
        {
            "entity_id": "climate.comfoclime",
            "scenario": "cooking",
            "duration": 45,
            "start_delay": "2030-01-01 10:00:00",
        }
    )

    assert data["duration"] == 45
    assert data["start_delay"] == "2030-01-01 10:00:00"
    assert "duration" not in schema({"entity_id": "climate.comfoclime", "scenario": "cooking"})


@pytest.mark.parametrize(
    "bad",
    [
        {"entity_id": "climate.comfoclime"},
        {"entity_id": "climate.comfoclime", "scenario": "sleeping"},
        {"entity_id": "climate.comfoclime", "scenario": "cooking", "duration": 0},
        {"entity_id": "climate.comfoclime", "scenario": "cooking", "duration": -5},
        {"entity_id": "climate.comfoclime", "scenario": "cooking", "duration": "abc"},
        {"entity_id": "climate.comfoclime", "scenario": "cooking", "start_delay": "tomorrow"},
    ],
    ids=["no-scenario", "unknown-scenario", "zero-duration", "negative-duration", "string-duration", "bad-start-delay"],
)
def test_set_scenario_mode_schema_rejects_invalid(bad):
    """Invalid input is rejected by the schema, i.e. before any API call."""
    schema = _register_and_get_scenario_kwargs()["schema"]

    with pytest.raises(vol.Invalid):
        schema(bad)


@pytest.mark.asyncio
async def test_reset_system_resolves_loaded_entries_at_call_time():
    """reset_system looks up loaded entries when called, not when registered.

    This verifies that after a config entry reload the handler uses the new API.
    """
    hass = _make_hass({})  # empty at registration time

    async_setup_services(hass, DOMAIN)
    handler = next(c[0][2] for c in hass.services.async_register.call_args_list if c[0][1] == "reset_system")

    # Simulate config entry reload: new entry with a new api is loaded
    api = _make_api()
    hass.loaded_entries.append(_make_entry("entry1", api))

    call = MagicMock()
    await handler(call)

    api.async_reset_system.assert_called_once()
