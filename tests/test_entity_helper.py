"""Tests for entity_helper module.

The entity-selection machinery this module used to own is gone; enabling and
disabling entities is Home Assistant's job now. What remains is the set of
accessors that read device metadata from either a Pydantic ``DeviceConfig``
or a raw API dict, which is why every accessor is tested against both shapes.
"""

from custom_components.comfoclime.entity_helper import (
    MODEL_TYPE_NAMES,
    _friendly_model_name,
    get_device_display_name,
    get_device_model_type,
    get_device_model_type_id,
    get_device_uuid,
    get_device_version,
)
from custom_components.comfoclime.models import DeviceConfig


def test_get_device_uuid():
    """get_device_uuid reads a Pydantic DeviceConfig model."""
    device = DeviceConfig(uuid="pydantic-uuid-456", model_type_id=20, display_name="Test Device")
    assert get_device_uuid(device) == "pydantic-uuid-456"


def test_get_device_uuid_from_dict():
    """get_device_uuid reads the raw API dict shape."""
    assert get_device_uuid({"uuid": "dict-uuid-123"}) == "dict-uuid-123"


def test_get_device_uuid_missing():
    """A device without a UUID yields None rather than raising."""
    assert get_device_uuid({}) is None
    assert get_device_uuid(object()) is None


def test_get_device_model_type_id():
    """get_device_model_type_id reads a Pydantic DeviceConfig model."""
    device = DeviceConfig(uuid="test-uuid", model_type_id=1, display_name="ComfoAirQ")
    assert get_device_model_type_id(device) == 1


def test_get_device_model_type_id_from_dict():
    """The dict shape uses the API's camelCase 'modelTypeId' key."""
    assert get_device_model_type_id({"modelTypeId": 20}) == 20
    assert get_device_model_type_id({}) is None


def test_get_device_display_name_falls_back():
    """A missing or empty display name falls back to the supplied default."""
    device = DeviceConfig(uuid="u", model_type_id=20, display_name="ComfoClime 36")
    assert get_device_display_name(device) == "ComfoClime 36"
    assert get_device_display_name({}, default="Fallback") == "Fallback"


def test_get_device_version():
    """Firmware version is read from both shapes."""
    device = DeviceConfig(uuid="u", model_type_id=20, display_name="d", version="R1.5.0")
    assert get_device_version(device) == "R1.5.0"
    assert get_device_version({"version": "R1.4.0"}) == "R1.4.0"
    assert get_device_version({}) is None


def test_get_device_model_type_prefers_vendor_string_for_dicts():
    """Dicts carry the vendor's '@modelType' verbatim."""
    assert get_device_model_type({"@modelType": "ComfoAirQ 600"}) == "ComfoAirQ 600"


def test_get_device_model_type_derives_name_for_models():
    """Pydantic models have no vendor string, so a friendly name is derived."""
    device = DeviceConfig(uuid="u", model_type_id=20, display_name="d")
    assert get_device_model_type(device) == "ComfoClime"


def test_friendly_model_name_known_ids():
    """Known modelTypeIds map to their product names."""
    assert _friendly_model_name(1) == "ComfoAirQ"
    assert _friendly_model_name(20) == "ComfoClime"
    assert _friendly_model_name(222) == "ComfoHub"
    assert set(MODEL_TYPE_NAMES) == {1, 20, 222}


def test_friendly_model_name_handles_unknown_and_junk():
    """Unknown or non-numeric IDs degrade to a readable label, never an error."""
    assert _friendly_model_name(99) == "Model 99"
    assert _friendly_model_name("20") == "ComfoClime"
    assert _friendly_model_name("NULL") == "Model NULL"
    assert _friendly_model_name(None) == "Unknown Model"
