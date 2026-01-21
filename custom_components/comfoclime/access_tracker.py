# access_tracker.py
"""Access tracking for ComfoClime API requests.

This module provides the AccessTracker class that tracks:
- Access counts per coordinator per minute and per hour
- Last access timestamp per coordinator
- Total API request counts

This information is exposed via diagnostic sensors to help monitor
and optimize API access patterns to the Airduino board.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CoordinatorStats:
    """Statistics for a single coordinator's API accesses.

    Tracks access timestamps, counts, and timing for monitoring
    API usage patterns.

    Attributes:
        access_timestamps: FIFO queue of access timestamps (monotonic time).
        total_count: Total number of accesses since creation.
        last_access_time: Timestamp of most recent access.

    Example:
        >>> stats = CoordinatorStats()
        >>> stats.record_access(time.monotonic())
        >>> stats.total_count
        1
    """

    # Deque of timestamps for accesses in the last hour
    # Using deque for efficient removal of old entries
    access_timestamps: Deque[float] = field(default_factory=deque)
    total_count: int = field(default=0)
    last_access_time: float = field(default=0.0)

    def __post_init__(self) -> None:
        """Validate initial state."""
        if self.total_count < 0:
            raise ValueError("total_count cannot be negative")
        if self.last_access_time < 0:
            raise ValueError("last_access_time cannot be negative")

    def record_access(self, timestamp: float) -> None:
        """Record a new API access.

        Args:
            timestamp: Monotonic timestamp of the access.
        """
        self.access_timestamps.append(timestamp)
        self.total_count += 1
        self.last_access_time = timestamp

    def cleanup_old_entries(self, cutoff: float) -> int:
        """Remove entries older than cutoff.

        Args:
            cutoff: Timestamp threshold; entries before this are removed.

        Returns:
            Number of entries removed.
        """
        removed = 0
        while self.access_timestamps and self.access_timestamps[0] < cutoff:
            self.access_timestamps.popleft()
            removed += 1
        return removed


class AccessTracker:
    """Tracks API access patterns for all coordinators.

    Provides per-minute and per-hour access counts for each coordinator,
    allowing users to monitor and optimize API access patterns.

    Attributes:
        coordinators: Dictionary mapping coordinator names to their stats.
    """

    # Time windows for statistics
    MINUTE_WINDOW = 60.0  # seconds
    HOUR_WINDOW = 3600.0  # seconds

    def __init__(self):
        """Initialize the access tracker."""
        self._coordinators: dict[str, CoordinatorStats] = {}

    def _get_current_time(self) -> float:
        """Get current monotonic time for rate limiting."""
        return time.monotonic()

    def record_access(self, coordinator_name: str) -> None:
        """Record an API access for a coordinator.

        Args:
            coordinator_name: Name of the coordinator making the access.
        """
        current_time = self._get_current_time()

        if coordinator_name not in self._coordinators:
            self._coordinators[coordinator_name] = CoordinatorStats()

        stats = self._coordinators[coordinator_name]
        stats.record_access(current_time)

        _LOGGER.debug(
            f"Recorded access for {coordinator_name}, "
            f"total={stats.total_count}"
        )

    def _cleanup_old_entries(
        self, stats: CoordinatorStats, current_time: float
    ) -> None:
        """Remove entries older than the hour window.

        Args:
            stats: The coordinator stats to clean up.
            current_time: Current monotonic time.
        """
        cutoff = current_time - self.HOUR_WINDOW
        stats.cleanup_old_entries(cutoff)

    def get_accesses_per_minute(self, coordinator_name: str) -> int:
        """Get the number of accesses in the last minute for a coordinator.

        Args:
            coordinator_name: Name of the coordinator.

        Returns:
            Number of accesses in the last minute.
        """
        if coordinator_name not in self._coordinators:
            return 0

        stats = self._coordinators[coordinator_name]
        current_time = self._get_current_time()
        self._cleanup_old_entries(stats, current_time)

        cutoff = current_time - self.MINUTE_WINDOW
        return sum(1 for ts in stats.access_timestamps if ts >= cutoff)

    def get_accesses_per_hour(self, coordinator_name: str) -> int:
        """Get the number of accesses in the last hour for a coordinator.

        Args:
            coordinator_name: Name of the coordinator.

        Returns:
            Number of accesses in the last hour.
        """
        if coordinator_name not in self._coordinators:
            return 0

        stats = self._coordinators[coordinator_name]
        current_time = self._get_current_time()
        self._cleanup_old_entries(stats, current_time)

        return len(stats.access_timestamps)

    def get_total_accesses(self, coordinator_name: str) -> int:
        """Get the total number of accesses for a coordinator since startup.

        Args:
            coordinator_name: Name of the coordinator.

        Returns:
            Total number of accesses.
        """
        if coordinator_name not in self._coordinators:
            return 0
        return self._coordinators[coordinator_name].total_count

    def get_all_coordinator_names(self) -> list[str]:
        """Get all registered coordinator names.

        Returns:
            List of coordinator names.
        """
        return list(self._coordinators.keys())

    def get_total_accesses_per_minute(self) -> int:
        """Get total accesses per minute across all coordinators.

        Returns:
            Total accesses in the last minute.
        """
        return sum(
            self.get_accesses_per_minute(name)
            for name in self._coordinators.keys()
        )

    def get_total_accesses_per_hour(self) -> int:
        """Get total accesses per hour across all coordinators.

        Returns:
            Total accesses in the last hour.
        """
        return sum(
            self.get_accesses_per_hour(name)
            for name in self._coordinators.keys()
        )

    def get_summary(self) -> dict:
        """Get a summary of all coordinator access statistics.

        Returns:
            Dictionary with coordinator statistics.
        """
        summary = {}
        for name in self._coordinators.keys():
            summary[name] = {
                "per_minute": self.get_accesses_per_minute(name),
                "per_hour": self.get_accesses_per_hour(name),
                "total": self.get_total_accesses(name),
            }
        return summary
