"""Entity definitions for ComfoClime switches using Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import EntityDefinitionBase


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
