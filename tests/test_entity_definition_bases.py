"""Tests for shared entity definition base models."""

import pytest
from pydantic import ValidationError

from custom_components.comfoclime.entities.number_definitions import NumberDefinition
from custom_components.comfoclime.entities.select_definitions import PropertySelectDefinition
from custom_components.comfoclime.entities.sensor_definitions import SensorDefinition
from custom_components.comfoclime.entities.switch_definitions import SwitchDefinition


def test_key_based_definitions_expose_shared_fields() -> None:
    """Key-based definitions should expose shared name and translation fields."""
    switch_def = SwitchDefinition(
        key="season.status",
        name="Automatic Season Detection",
        translation_key="automatic_season_detection",
        endpoint="thermal_profile",
    )
    number_def = NumberDefinition(
        key="temperature.manualTemperature",
        name="Manual Temperature",
        translation_key="manual_temperature",
        min=10,
        max=30,
        step=0.5,
    )
    sensor_def = SensorDefinition(
        key="indoorTemperature",
        name="Indoor Temperature",
        translation_key="indoor_temperature",
        unit="°C",
    )

    assert switch_def.name == "Automatic Season Detection"
    assert number_def.translation_key == "manual_temperature"
    assert sensor_def.key == "indoorTemperature"


def test_path_based_definitions_expose_shared_fields() -> None:
    """Path-based definitions should expose shared name and translation fields."""
    select_def = PropertySelectDefinition(
        path="29/1/6",
        name="Humidity Comfort Control",
        translation_key="humidity_comfort_control",
        options={0: "off", 1: "autoonly", 2: "on"},
    )

    assert select_def.path == "29/1/6"
    assert select_def.name == "Humidity Comfort Control"
    assert select_def.translation_key == "humidity_comfort_control"


def test_shared_definition_models_are_frozen() -> None:
    """Definition models should remain immutable after initialization."""
    switch_def = SwitchDefinition(
        key="season.status",
        name="Automatic Season Detection",
        translation_key="automatic_season_detection",
        endpoint="thermal_profile",
    )

    with pytest.raises(ValidationError):
        switch_def.name = "Changed"
