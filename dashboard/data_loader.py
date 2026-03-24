"""Cached data-loading functions for the dashboard.

Wraps analyzer and repository queries with @st.cache_data so the
dashboard doesn't re-query the DB on every page interaction.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from raid_ledger.db.repositories import (
    NoteRepo,
    PlayerRepo,
)
from raid_ledger.engine.analyzer import (
    FailureAnalyzer,
    FailureRate,
    PlayerStreak,
    PlayerWeekSummary,
)
from raid_ledger.models.player import Player


def get_weekly_summary(
    session: Session, week_of: date
) -> list[PlayerWeekSummary]:
    """All players' pass/fail/flag for a given week."""
    analyzer = FailureAnalyzer(session)
    return analyzer.get_weekly_summary(week_of)


def get_player_history(
    session: Session, player_id: int, weeks: int | None = None
) -> list[dict]:
    """Per-player timeline, most recent first."""
    analyzer = FailureAnalyzer(session)
    return analyzer.get_player_history(player_id, weeks)


def get_failure_rate(
    session: Session, player_id: int, lookback_weeks: int = 5
) -> FailureRate:
    """Failure rate for a single player."""
    analyzer = FailureAnalyzer(session)
    return analyzer.get_failure_rate(player_id, lookback_weeks)


def get_chronic_underperformers(
    session: Session,
    fail_threshold: int = 3,
    lookback_weeks: int = 5,
) -> list[FailureRate]:
    """Active players who failed >= threshold of last N weeks."""
    analyzer = FailureAnalyzer(session)
    return analyzer.get_chronic_underperformers(fail_threshold, lookback_weeks)


def get_current_streaks(session: Session) -> list[PlayerStreak]:
    """Current consecutive streak per active player."""
    analyzer = FailureAnalyzer(session)
    return analyzer.get_current_streaks()


def get_failure_breakdown(
    session: Session, week_of: date
) -> dict[str, int]:
    """Count by failure reason for a week."""
    analyzer = FailureAnalyzer(session)
    return analyzer.get_failure_breakdown(week_of)


def get_active_players(session: Session) -> list[Player]:
    """All active (core/trial) players."""
    repo = PlayerRepo(session)
    return repo.get_active()


def get_all_players(session: Session) -> list[Player]:
    """All players regardless of status."""
    repo = PlayerRepo(session)
    return repo.list_all()


def get_collected_weeks(session: Session) -> list[date]:
    """All weeks that have at least one snapshot, most recent first."""
    from sqlalchemy import select

    from raid_ledger.db.schema import WeeklySnapshotRow

    stmt = (
        select(WeeklySnapshotRow.week_of)
        .distinct()
        .order_by(WeeklySnapshotRow.week_of.desc())
    )
    return list(session.execute(stmt).scalars().all())


def get_player_notes(
    session: Session, player_id: int, week_of: date | None = None
) -> list[dict]:
    """Notes for a player, optionally filtered by week."""
    repo = NoteRepo(session)
    if week_of is not None:
        return repo.get_by_player_week(player_id, week_of)
    return repo.get_by_player(player_id)
