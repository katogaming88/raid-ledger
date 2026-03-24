"""Shared filter utilities for dashboard pages."""

from __future__ import annotations

from raid_ledger.engine.analyzer import PlayerWeekSummary


def apply_filters(
    summary: list[PlayerWeekSummary],
    status_filter: list[str],
    role_filter: list[str],
) -> list[PlayerWeekSummary]:
    """Filter a weekly summary by player status and role."""
    return [
        s for s in summary
        if s.player_status in status_filter and s.role in role_filter
    ]
