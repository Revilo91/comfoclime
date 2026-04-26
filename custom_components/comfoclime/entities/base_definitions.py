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
