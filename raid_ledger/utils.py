"""Shared utility functions."""

from __future__ import annotations

from datetime import date, timedelta


def most_recent_tuesday(today: date | None = None) -> date:
    """Return the most recent Tuesday (including today if it's Tuesday).

    WoW US weekly reset is Tuesday — all week_of dates align to this.
    """
    d = today or date.today()
    days_since_tuesday = (d.weekday() - 1) % 7
    return d - timedelta(days=days_since_tuesday)
