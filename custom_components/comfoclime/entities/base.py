"""Base classes for entity definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityDefinitionBase(BaseModel):
    """Base class for all entity definitions.

    Contains common fields shared by all entity types.

    Attributes:
        name: Display name for the entity (fallback if translation missing).
        translation_key: Key for i18n translations.
    """

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    name: str = Field(..., description="Display name for the entity (fallback if translation missing)")
    translation_key: str = Field(..., description="Key for i18n translations")
