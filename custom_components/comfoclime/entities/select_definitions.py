"""Entity definitions for ComfoClime select controls using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SelectDefinition:
    """Definition of a select entity.
    
    Attributes:
        key: Unique identifier for the select in API responses.
        name: Display name for the select control.
        translation_key: Key for i18n translations.
        options: Dictionary mapping numeric values to string options.
    """
    key: str
    name: str
    translation_key: str
    options: dict[int, str]


@dataclass(frozen=True, slots=True)
class PropertySelectDefinition:
    """Definition of a property-based select entity.
    
    Attributes:
        path: Property path in format "X/Y/Z".
        name: Display name for the select control.
        translation_key: Key for i18n translations.
        options: Dictionary mapping numeric values to string options.
    """
    path: str
    name: str
    translation_key: str
    options: dict[int, str]


SELECT_ENTITIES = [
    SelectDefinition(
        key="temperatureProfile",
        name="Temperature Profile",
        translation_key="temperature_profile",
        options={0: "comfort", 1: "power", 2: "eco"},
    ),
    SelectDefinition(
        key="season.season",
        name="Season Mode",
        translation_key="season_mode",
        options={1: "heating", 0: "transition", 2: "cooling"},
    ),
]

PROPERTY_SELECT_ENTITIES = {
    1: [
        PropertySelectDefinition(
            path="29/1/6",
            name="Humidity Comfort Control",
            translation_key="humidity_comfort_control",
            options={0: "off", 1: "autoonly", 2: "on"},
        ),
        PropertySelectDefinition(
            path="29/1/7",
            name="Humidity Protection",
            translation_key="humidity_protection",
            options={0: "off", 1: "autoonly", 2: "on"},
        ),
    ]
}
