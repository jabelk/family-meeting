"""Tests for calendar time validation (AM/PM correction)."""

from src.tools.calendar import _is_early_morning_allowed, _validate_event_time


class TestIsEarlyMorningAllowed:
    def test_workout_allowed(self):
        assert _is_early_morning_allowed("Morning workout") is True

    def test_gym_allowed(self):
        assert _is_early_morning_allowed("Gym session") is True

    def test_breakfast_allowed(self):
        assert _is_early_morning_allowed("Breakfast prep") is True

    def test_ski_allowed(self):
        assert _is_early_morning_allowed("Ski lesson departure") is True

    def test_flight_allowed(self):
        assert _is_early_morning_allowed("Flight to LAX") is True

    def test_swim_not_allowed(self):
        assert _is_early_morning_allowed("Swim lessons") is False

    def test_pickup_not_allowed(self):
        assert _is_early_morning_allowed("School pickup: Vienna") is False

    def test_dinner_not_allowed(self):
        assert _is_early_morning_allowed("Return home & dinner prep") is False

    def test_case_insensitive(self):
        assert _is_early_morning_allowed("GYM TIME") is True
        assert _is_early_morning_allowed("Early Morning Routine") is True

    def test_empty_string(self):
        assert _is_early_morning_allowed("") is False


class TestValidateEventTime:
    def test_afternoon_event_at_2am_shifted(self):
        """'Swim lessons' at 2 AM should be shifted to 2 PM."""
        start = "2026-03-15T02:00:00-07:00"
        end = "2026-03-15T03:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Swim lessons")
        assert "T14:00:00" in c_start
        assert "T15:00:00" in c_end
        assert len(corrections) == 2  # both start and end corrected

    def test_workout_at_6am_preserved(self):
        """'Workout' at 6 AM should NOT be shifted."""
        start = "2026-03-15T06:00:00-07:00"
        end = "2026-03-15T07:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Morning workout")
        assert c_start == start
        assert c_end == end
        assert len(corrections) == 0

    def test_gym_at_5am_preserved(self):
        """'Gym' at 5 AM should NOT be shifted."""
        start = "2026-03-15T05:00:00-07:00"
        end = "2026-03-15T06:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Gym session")
        assert c_start == start
        assert c_end == end
        assert len(corrections) == 0

    def test_swim_at_4am_shifted(self):
        """'Swim lessons' at 4 AM should be shifted to 4 PM."""
        start = "2026-03-15T04:00:00-07:00"
        end = "2026-03-15T05:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Swim lessons - Erin brings girls")
        assert "T16:00:00" in c_start
        assert "T17:00:00" in c_end
        assert len(corrections) == 2

    def test_2pm_event_unchanged(self):
        """Event at 2 PM (14:00) should pass through unchanged."""
        start = "2026-03-15T14:00:00-07:00"
        end = "2026-03-15T15:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "School pickup")
        assert c_start == start
        assert c_end == end
        assert len(corrections) == 0

    def test_8am_boundary_not_shifted(self):
        """Event at exactly 8 AM should NOT be shifted (boundary)."""
        start = "2026-03-15T08:00:00-07:00"
        end = "2026-03-15T09:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Drop off Vienna")
        assert c_start == start
        assert c_end == end
        assert len(corrections) == 0

    def test_malformed_time_passthrough(self):
        """Malformed time strings should be returned as-is."""
        c_start, c_end, corrections = _validate_event_time("not-a-time", "also-bad", "Test")
        assert c_start == "not-a-time"
        assert c_end == "also-bad"
        assert len(corrections) == 0

    def test_midnight_event_shifted(self):
        """Event at midnight (hour 0) should be shifted to noon."""
        start = "2026-03-15T00:30:00-07:00"
        end = "2026-03-15T01:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Zoey quiet time")
        assert "T12:30:00" in c_start
        assert "T13:00:00" in c_end

    def test_7am_non_allowlisted_shifted(self):
        """Non-allowlisted event at 7 AM should be shifted to 7 PM."""
        start = "2026-03-15T07:00:00-07:00"
        end = "2026-03-15T07:30:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Dinner prep")
        assert "T19:00:00" in c_start
        assert "T19:30:00" in c_end

    def test_only_start_in_range(self):
        """If start is at 3 AM but end is at 14:00, only start gets shifted."""
        start = "2026-03-15T03:00:00-07:00"
        end = "2026-03-15T14:00:00-07:00"
        c_start, c_end, corrections = _validate_event_time(start, end, "Pickup")
        assert "T15:00:00" in c_start
        assert c_end == end  # end was already PM, unchanged
        assert len(corrections) == 1
