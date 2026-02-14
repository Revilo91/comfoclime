"""Entity definitions for ComfoClime select controls using Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityDefinitionBase(BaseModel):
    """Base class for all entity definitions.

    Contains common fields shared by all entity types.

    Attributes:
        name: Display name for the entity (fallback if translation missing).
        translation_key: Key for i18n translations.
    """

    model_config = {"frozen": True}

    name: str = Field(..., description="Display name for the entity (fallback if translation missing)")
    translation_key: str = Field(..., description="Key for i18n translations")


class SelectDefinition(EntityDefinitionBase):
    """Definition of a select entity.

    Attributes:
        key: Unique identifier for the select in API responses.
        options: Dictionary mapping numeric values to string options.
    """

    key: str = Field(..., description="Unique identifier for the select in API responses")
    options: dict[int, str] = Field(..., description="Dictionary mapping numeric values to string options")


class PropertySelectDefinition(EntityDefinitionBase):
    """Definition of a property-based select entity.

    Attributes:
        path: Property path in format "X/Y/Z".
        options: Dictionary mapping numeric values to string options.
    """

    path: str = Field(..., description="Property path in format 'X/Y/Z'")
    options: dict[int, str] = Field(..., description="Dictionary mapping numeric values to string options")


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
