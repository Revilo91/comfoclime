"""Tests for the AccessTracker module."""

import pytest

from custom_components.comfoclime.access_tracker import AccessTracker


class TestAccessTracker:
    """Tests for AccessTracker class."""

    def test_record_access_creates_coordinator_entry(self):
        """Test that recording an access creates a coordinator entry."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        
        assert "Dashboard" in tracker.get_all_coordinator_names()
        assert tracker.get_total_accesses("Dashboard") == 1

    def test_record_multiple_accesses(self):
        """Test recording multiple accesses for a coordinator."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        
        assert tracker.get_total_accesses("Dashboard") == 3

    def test_multiple_coordinators(self):
        """Test tracking multiple coordinators independently."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        tracker.record_access("Telemetry")
        tracker.record_access("Telemetry")
        tracker.record_access("Telemetry")
        tracker.record_access("Property")
        
        assert tracker.get_total_accesses("Dashboard") == 2
        assert tracker.get_total_accesses("Telemetry") == 3
        assert tracker.get_total_accesses("Property") == 1

    def test_get_accesses_per_minute(self):
        """Test getting accesses per minute."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        
        # These accesses were just recorded, should be within the minute
        assert tracker.get_accesses_per_minute("Dashboard") == 2

    def test_get_accesses_per_hour(self):
        """Test getting accesses per hour."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        
        # These accesses were just recorded, should be within the hour
        assert tracker.get_accesses_per_hour("Dashboard") == 3

    def test_unknown_coordinator_returns_zero(self):
        """Test that querying unknown coordinator returns zero."""
        tracker = AccessTracker()
        
        assert tracker.get_accesses_per_minute("Unknown") == 0
        assert tracker.get_accesses_per_hour("Unknown") == 0
        assert tracker.get_total_accesses("Unknown") == 0

    def test_get_all_coordinator_names(self):
        """Test getting all registered coordinator names."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Telemetry")
        tracker.record_access("Property")
        
        names = tracker.get_all_coordinator_names()
        assert "Dashboard" in names
        assert "Telemetry" in names
        assert "Property" in names
        assert len(names) == 3

    def test_get_total_accesses_per_minute(self):
        """Test getting total accesses per minute across all coordinators."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        tracker.record_access("Telemetry")
        tracker.record_access("Telemetry")
        tracker.record_access("Telemetry")
        tracker.record_access("Property")
        
        assert tracker.get_total_accesses_per_minute() == 6

    def test_get_total_accesses_per_hour(self):
        """Test getting total accesses per hour across all coordinators."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Telemetry")
        tracker.record_access("Property")
        
        assert tracker.get_total_accesses_per_hour() == 3

    def test_get_summary(self):
        """Test getting a summary of all coordinator statistics."""
        tracker = AccessTracker()
        
        tracker.record_access("Dashboard")
        tracker.record_access("Dashboard")
        tracker.record_access("Telemetry")
        
        summary = tracker.get_summary()
        
        assert "Dashboard" in summary
        assert "Telemetry" in summary
        assert summary["Dashboard"]["total"] == 2
        assert summary["Telemetry"]["total"] == 1
        assert "per_minute" in summary["Dashboard"]
        assert "per_hour" in summary["Dashboard"]

    def test_old_entries_cleanup(self):
        """Test that old entries are cleaned up after the hour window."""
        tracker = AccessTracker()
        
        # Use a helper class that allows mocking time
        class MockTracker(AccessTracker):
            def __init__(self):
                super().__init__()
                self._mock_time = 0
            
            def _get_current_time(self):
                return self._mock_time
        
        mock_tracker = MockTracker()
        
        # Record access at time 0
        mock_tracker._mock_time = 0
        mock_tracker.record_access("Dashboard")
        
        # Record access at time 30 (30 seconds later)
        mock_tracker._mock_time = 30
        mock_tracker.record_access("Dashboard")
        
        # Check at time 70 - first access should be outside minute window
        mock_tracker._mock_time = 70
        assert mock_tracker.get_accesses_per_minute("Dashboard") == 1  # Only the second access
        
        # Check at time 3700 - both should be outside hour window
        mock_tracker._mock_time = 3700
        assert mock_tracker.get_accesses_per_hour("Dashboard") == 0
        
        # But total should still count all accesses
        assert mock_tracker.get_total_accesses("Dashboard") == 2


class TestAccessTrackerIntegration:
    """Integration tests for AccessTracker with coordinators."""

    def test_coordinator_names_match_expected(self):
        """Test that coordinator names match expected values."""
        tracker = AccessTracker()
        
        # These are the names used in the coordinators
        expected_names = ["Dashboard", "Thermalprofile", "Monitoring", "Telemetry", "Property", "Definition"]
        
        for name in expected_names:
            tracker.record_access(name)
        
        actual_names = tracker.get_all_coordinator_names()
        for name in expected_names:
            assert name in actual_names
