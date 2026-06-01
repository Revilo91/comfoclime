"""Shared base models for entity definitions.

Centralizes common metadata fields used by multiple entity definition types.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SensorPriority(str, Enum):
    """Priority levels for sensor polling.

    Determines how frequently sensors are polled:
    - HIGH: Critical real-time data (5-15s) - temperatures, power, status
    - MEDIUM: Important monitoring data (30-60s) - fan speeds, pressures, flow
    - LOW: Less frequent updates (120-300s) - energy totals, efficiency, statistics
    - VERY_LOW: Rarely changing data (600s+) - versions, configuration, definitions
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class EntityDefinitionBase(BaseModel):
    """Base definition with shared name and translation metadata."""

    model_config = {"frozen": True}

    name: str = Field(..., description="Display name for the entity")
    translation_key: str = Field(..., description="Key for i18n translations")
    priority: SensorPriority = Field(
        default=SensorPriority.MEDIUM,
        description="Polling priority (high/medium/low/very_low)",
    )


class KeyEntityDefinitionBase(EntityDefinitionBase):
    """Base definition for entities addressed by a key."""

    key: str = Field(..., description="Unique identifier for the entity in API responses")


class PathEntityDefinitionBase(EntityDefinitionBase):
    """Base definition for entities addressed by a property path."""

    path: str = Field(..., description="Property path in format 'X/Y/Z'")
