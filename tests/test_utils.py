"""Tests for shared utility functions."""

from __future__ import annotations

from datetime import date

from raid_ledger.utils import most_recent_tuesday


class TestMostRecentTuesday:
    def test_tuesday_returns_itself(self):
        assert most_recent_tuesday(date(2026, 3, 17)) == date(2026, 3, 17)

    def test_wednesday_returns_previous_tuesday(self):
        assert most_recent_tuesday(date(2026, 3, 18)) == date(2026, 3, 17)

    def test_monday_returns_previous_tuesday(self):
        assert most_recent_tuesday(date(2026, 3, 23)) == date(2026, 3, 17)

    def test_sunday_returns_previous_tuesday(self):
        assert most_recent_tuesday(date(2026, 3, 22)) == date(2026, 3, 17)

    def test_saturday_returns_previous_tuesday(self):
        assert most_recent_tuesday(date(2026, 3, 21)) == date(2026, 3, 17)
