"""Typed runtime data stored on the config entry (``entry.runtime_data``).

Lives in its own module so platforms, ``entity_base`` and ``services`` can
import it without importing ``__init__`` (which imports them), avoiding cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .comfoclime_api import ComfoClimeAPI
    from .coordinator import (
        ComfoClimeAlarmsCoordinator,
        ComfoClimeDashboardCoordinator,
        ComfoClimeDefinitionCoordinator,
        ComfoClimeHealthCoordinator,
        ComfoClimeMonitoringCoordinator,
        ComfoClimePropertyCoordinator,
        ComfoClimeTelemetryCoordinator,
        ComfoClimeThermalprofileCoordinator,
    )


@dataclass
class ComfoClimeRuntimeData:
    """Everything a loaded ComfoClime config entry shares with its platforms."""

    api: ComfoClimeAPI
    coordinator: ComfoClimeDashboardCoordinator
    tpcoordinator: ComfoClimeThermalprofileCoordinator
    monitoringcoordinator: ComfoClimeMonitoringCoordinator
    tlcoordinator: ComfoClimeTelemetryCoordinator
    propcoordinator: ComfoClimePropertyCoordinator
    definitioncoordinator: ComfoClimeDefinitionCoordinator
    devices: list[Any]
    main_device: Any | None
    main_device_registry_id: str | None
    # Lazy coordinators: no first refresh, they poll only while an enabled entity uses them.
    healthcoordinator: ComfoClimeHealthCoordinator | None = None
    alarmscoordinator: ComfoClimeAlarmsCoordinator | None = None


type ComfoClimeConfigEntry = ConfigEntry[ComfoClimeRuntimeData]
