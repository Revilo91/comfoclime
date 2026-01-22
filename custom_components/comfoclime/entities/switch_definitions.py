"""Entity definitions for ComfoClime switches using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SwitchDefinition:
    """Definition of a switch entity.
    
    Attributes:
        key: Unique identifier for the switch in API responses or dict key.
        name: Display name for the switch (fallback if translation missing).
        translation_key: Key for i18n translations.
        endpoint: Either "thermal_profile" or "dashboard".
        invert: If True, invert the state logic (e.g., for hpstandby).
    """
    key: str
    name: str
    translation_key: str
    endpoint: str
    invert: bool = False


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
