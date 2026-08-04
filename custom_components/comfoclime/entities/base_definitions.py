"""Shared base models for entity definitions.

Centralizes common metadata fields used by multiple entity definition types.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityDefinitionBase(BaseModel):
    """Base definition with shared name and translation metadata."""

    model_config = {"frozen": True}

    name: str = Field(..., description="Display name for the entity")
    translation_key: str = Field(..., description="Key for i18n translations")


class KeyEntityDefinitionBase(EntityDefinitionBase):
    """Base definition for entities addressed by a key."""

    key: str = Field(..., description="Unique identifier for the entity in API responses")


class PathEntityDefinitionBase(EntityDefinitionBase):
    """Base definition for entities addressed by a property path."""

    path: str = Field(..., description="Property path in format 'X/Y/Z'")


def entity_category_for(entity_def: object) -> str | None:
    """Return the Home Assistant entity category for a definition.

    Telemetry marked ``diagnose`` is experimental or unverified, which is
    exactly what the diagnostic category is for, so it is folded in here
    rather than being tracked as a second, parallel concept.
    """
    category = getattr(entity_def, "entity_category", None)
    if category is not None:
        return category
    return "diagnostic" if getattr(entity_def, "diagnose", False) else None


def enabled_by_default(entity_def: object) -> bool:
    """Return whether an entity should start out enabled in the registry.

    Standard entities are visible from the start; anything filed under
    config or diagnostic is registered but disabled, so users who want it
    can switch it on per entity without the integration creating dozens of
    entities nobody asked for.
    """
    return entity_category_for(entity_def) is None
