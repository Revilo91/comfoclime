"""Entity definitions for ComfoClime switches using Pydantic models."""

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


class SwitchDefinition(EntityDefinitionBase):
    """Definition of a switch entity.

    Attributes:
        key: Unique identifier for the switch in API responses or dict key.
        endpoint: Either "thermal_profile" or "dashboard".
        invert: If True, invert the state logic (e.g., for hpstandby).
    """

    key: str = Field(..., description="Unique identifier for the switch in API responses or dict key")
    endpoint: str = Field(..., description="Either 'thermal_profile' or 'dashboard'")
    invert: bool = Field(
        default=False,
        description="If True, invert the state logic (e.g., for hpstandby)",
    )


SWITCHES = [
    SwitchDefinition(
        key="season.status",
        name="Automatic Season Detection",
        translation_key="automatic_season_detection",
        endpoint="thermal_profile",
        invert=False,
    ),
    SwitchDefinition(
        key="temperature.status",
        name="Automatic Comfort Temperature",
        translation_key="automatic_comfort_temperature",
        endpoint="thermal_profile",
        invert=False,
    ),
    SwitchDefinition(
        key="hpstandby",
        name="Heatpump on/off",
        translation_key="heatpump_onoff",
        endpoint="dashboard",
        invert=True,
    ),
]
