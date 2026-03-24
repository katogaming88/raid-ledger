"""Tests for the dashboard data loader functions."""

from __future__ import annotations

from datetime import date

# Import data_loader functions — these don't use @st.cache_data in tests
from dashboard.data_loader import (
    get_active_players,
    get_all_players,
    get_collected_weeks,
    get_failure_rate,
    get_player_history,
    get_weekly_summary,
)
from raid_ledger.db.repositories import PlayerRepo, SnapshotRepo
from raid_ledger.models.player import Player, PlayerStatus
from raid_ledger.models.snapshot import SnapshotStatus, WeeklySnapshot

WEEK = date(2026, 3, 17)


def _seed_player(session, name="TestPlayer", status="core") -> int:
    repo = PlayerRepo(session)
    p = repo.create(Player(
        name=name, realm="tichondrius", class_name="Mage",
        role="dps", status=PlayerStatus(status), joined_date=date(2026, 3, 1),
    ))
    session.commit()
    return p.player_id


def _seed_snapshot(session, player_id, week_of=WEEK, status="pass"):
    repo = SnapshotRepo(session)
    repo.upsert(WeeklySnapshot(
        player_id=player_id, week_of=week_of, status=SnapshotStatus(status),
        mplus_runs_total=10, mplus_runs_at_level=8, highest_key_level=12,
        item_level=620.0, vault_slots_earned=3, raiderio_score=2400.0,
    ))
    session.commit()


class TestDataLoaderWithData:
    def test_get_weekly_summary(self, db_session):
        pid = _seed_player(db_session)
        _seed_snapshot(db_session, pid)
        result = get_weekly_summary(db_session, WEEK)
        assert len(result) == 1
        assert result[0].name == "TestPlayer"

    def test_get_player_history(self, db_session):
        pid = _seed_player(db_session)
        _seed_snapshot(db_session, pid, date(2026, 3, 10))
        _seed_snapshot(db_session, pid, date(2026, 3, 17))
        result = get_player_history(db_session, pid)
        assert len(result) == 2
        assert result[0]["week_of"] == date(2026, 3, 17)

    def test_get_failure_rate(self, db_session):
        pid = _seed_player(db_session)
        _seed_snapshot(db_session, pid, date(2026, 3, 10), "fail")
        _seed_snapshot(db_session, pid, date(2026, 3, 17), "pass")
        result = get_failure_rate(db_session, pid, lookback_weeks=5)
        assert result.failures == 1
        assert result.total_weeks == 2

    def test_get_active_players(self, db_session):
        _seed_player(db_session, "Active", "core")
        _seed_player(db_session, "Inactive", "inactive")
        result = get_active_players(db_session)
        names = [p.name for p in result]
        assert "Active" in names
        assert "Inactive" not in names

    def test_get_all_players(self, db_session):
        _seed_player(db_session, "Active", "core")
        _seed_player(db_session, "Inactive", "inactive")
        result = get_all_players(db_session)
        assert len(result) == 2

    def test_get_collected_weeks(self, db_session):
        pid = _seed_player(db_session)
        _seed_snapshot(db_session, pid, date(2026, 3, 10))
        _seed_snapshot(db_session, pid, date(2026, 3, 17))
        weeks = get_collected_weeks(db_session)
        assert len(weeks) == 2
        assert weeks[0] == date(2026, 3, 17)  # most recent first


class TestDataLoaderEmpty:
    def test_empty_weekly_summary(self, db_session):
        result = get_weekly_summary(db_session, WEEK)
        assert result == []

    def test_empty_player_history(self, db_session):
        result = get_player_history(db_session, 9999)
        assert result == []

    def test_empty_active_players(self, db_session):
        result = get_active_players(db_session)
        assert result == []

    def test_empty_collected_weeks(self, db_session):
        weeks = get_collected_weeks(db_session)
        assert weeks == []
