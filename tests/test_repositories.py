"""Tests for all repository classes — CRUD, constraints, upserts, edge cases."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from raid_ledger.db.repositories import (
    BenchmarkRepo,
    CollectionRunRepo,
    NoteRepo,
    PlayerRepo,
    SettingsRepo,
    SnapshotRepo,
)
from raid_ledger.models.benchmark import WeeklyBenchmark
from raid_ledger.models.player import Player, PlayerStatus
from raid_ledger.models.snapshot import SnapshotStatus, WeeklySnapshot

# ---------------------------------------------------------------------------
# PlayerRepo
# ---------------------------------------------------------------------------

class TestPlayerRepo:
    def test_create_and_get_by_id(self, db_session, sample_player):
        repo = PlayerRepo(db_session)
        created = repo.create(sample_player)
        assert created.player_id is not None
        assert created.name == "Testchar"

        fetched = repo.get_by_id(created.player_id)
        assert fetched is not None
        assert fetched.name == "Testchar"
        assert fetched.class_name == "Death Knight"

    def test_get_by_name_realm_region(self, db_session, sample_player):
        repo = PlayerRepo(db_session)
        repo.create(sample_player)

        found = repo.get_by_name_realm_region("Testchar", "tichondrius", "us")
        assert found is not None
        assert found.name == "Testchar"

        missing = repo.get_by_name_realm_region("Nobody", "tichondrius", "us")
        assert missing is None

    def test_unique_constraint(self, db_session, sample_player):
        repo = PlayerRepo(db_session)
        repo.create(sample_player)
        with pytest.raises(IntegrityError):
            repo.create(sample_player)

    def test_get_active(self, db_session):
        repo = PlayerRepo(db_session)
        for name, status in [
            ("Core1", PlayerStatus.CORE),
            ("Trial1", PlayerStatus.TRIAL),
            ("Bench1", PlayerStatus.BENCH),
            ("Inactive1", PlayerStatus.INACTIVE),
        ]:
            repo.create(Player(
                name=name, realm="tichondrius", class_name="Mage",
                role="dps", status=status, joined_date=date(2026, 3, 1),
            ))
        db_session.commit()

        active = repo.get_active()
        names = [p.name for p in active]
        assert "Core1" in names
        assert "Trial1" in names
        assert "Bench1" not in names
        assert "Inactive1" not in names

    def test_update_status(self, db_session, sample_player):
        repo = PlayerRepo(db_session)
        created = repo.create(sample_player)

        updated = repo.update_status(created.player_id, PlayerStatus.INACTIVE)
        assert updated is not None
        assert updated.status is PlayerStatus.INACTIVE

    def test_update_status_missing_player(self, db_session):
        repo = PlayerRepo(db_session)
        result = repo.update_status(9999, PlayerStatus.INACTIVE)
        assert result is None

    def test_list_all(self, db_session):
        repo = PlayerRepo(db_session)
        repo.create(Player(
            name="Alpha", realm="tichondrius", class_name="Mage",
            role="dps", joined_date=date(2026, 3, 1),
        ))
        repo.create(Player(
            name="Beta", realm="tichondrius", class_name="Warrior",
            role="tank", joined_date=date(2026, 3, 1),
        ))
        db_session.commit()
        all_players = repo.list_all()
        assert len(all_players) == 2
        assert all_players[0].name == "Alpha"

    def test_utf8_player_name(self, db_session):
        repo = PlayerRepo(db_session)
        p = Player(
            name="Tëstñame", realm="tichondrius", class_name="Paladin",
            role="tank", joined_date=date(2026, 3, 1),
        )
        created = repo.create(p)
        fetched = repo.get_by_id(created.player_id)
        assert fetched.name == "Tëstñame"

    def test_hyphenated_realm(self, db_session):
        repo = PlayerRepo(db_session)
        p = Player(
            name="AltChar", realm="bleeding-hollow", class_name="Rogue",
            role="dps", joined_date=date(2026, 3, 1),
        )
        created = repo.create(p)
        fetched = repo.get_by_id(created.player_id)
        assert fetched.realm == "bleeding-hollow"


# ---------------------------------------------------------------------------
# SnapshotRepo
# ---------------------------------------------------------------------------

class TestSnapshotRepo:
    def _create_player(self, db_session) -> int:
        repo = PlayerRepo(db_session)
        p = repo.create(Player(
            name="SnapPlayer", realm="tichondrius", class_name="Mage",
            role="dps", joined_date=date(2026, 3, 1),
        ))
        db_session.commit()
        return p.player_id

    def test_upsert_insert(self, db_session, sample_snapshot):
        pid = self._create_player(db_session)
        repo = SnapshotRepo(db_session)
        snap = sample_snapshot.model_copy(update={"player_id": pid})
        result = repo.upsert(snap)
        assert result.snapshot_id is not None
        assert result.mplus_runs_at_level == 8

    def test_upsert_update(self, db_session, sample_snapshot):
        pid = self._create_player(db_session)
        repo = SnapshotRepo(db_session)
        snap = sample_snapshot.model_copy(update={"player_id": pid})
        first = repo.upsert(snap)

        updated_snap = snap.model_copy(update={
            "mplus_runs_at_level": 5,
            "status": SnapshotStatus.FAIL,
            "reasons": ["insufficient_keys"],
        })
        second = repo.upsert(updated_snap)

        assert second.snapshot_id == first.snapshot_id
        assert second.mplus_runs_at_level == 5
        assert second.status is SnapshotStatus.FAIL

    def test_get_by_player_week(self, db_session, sample_snapshot):
        pid = self._create_player(db_session)
        repo = SnapshotRepo(db_session)
        snap = sample_snapshot.model_copy(update={"player_id": pid})
        repo.upsert(snap)
        db_session.commit()

        fetched = repo.get_by_player_week(pid, date(2026, 3, 17))
        assert fetched is not None
        assert fetched.mplus_runs_total == 10

        missing = repo.get_by_player_week(pid, date(2026, 3, 24))
        assert missing is None

    def test_get_by_week(self, db_session):
        p_repo = PlayerRepo(db_session)
        p1 = p_repo.create(Player(
            name="P1", realm="tichondrius", class_name="Mage",
            role="dps", joined_date=date(2026, 3, 1),
        ))
        p2 = p_repo.create(Player(
            name="P2", realm="tichondrius", class_name="Warrior",
            role="tank", joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        s_repo = SnapshotRepo(db_session)
        week = date(2026, 3, 17)
        for pid in [p1.player_id, p2.player_id]:
            s_repo.upsert(WeeklySnapshot(
                player_id=pid, week_of=week, status=SnapshotStatus.PASS,
            ))
        db_session.commit()

        results = s_repo.get_by_week(week)
        assert len(results) == 2

    def test_get_player_history(self, db_session):
        pid = self._create_player(db_session)
        repo = SnapshotRepo(db_session)
        weeks = [date(2026, 3, d) for d in [3, 10, 17]]
        for w in weeks:
            repo.upsert(WeeklySnapshot(
                player_id=pid, week_of=w, status=SnapshotStatus.PASS,
            ))
        db_session.commit()

        history = repo.get_player_history(pid)
        assert len(history) == 3
        assert history[0].week_of == date(2026, 3, 17)  # most recent first

        limited = repo.get_player_history(pid, weeks=2)
        assert len(limited) == 2

    def test_reasons_json_roundtrip(self, db_session, sample_snapshot):
        pid = self._create_player(db_session)
        repo = SnapshotRepo(db_session)
        snap = sample_snapshot.model_copy(update={
            "player_id": pid,
            "status": SnapshotStatus.FAIL,
            "reasons": ["insufficient_keys", "low_ilvl"],
        })
        repo.upsert(snap)
        db_session.commit()

        fetched = repo.get_by_player_week(pid, snap.week_of)
        assert fetched.reasons == ["insufficient_keys", "low_ilvl"]

    def test_fk_restrict_prevents_orphan_snapshot(self, db_session):
        repo = SnapshotRepo(db_session)
        snap = WeeklySnapshot(
            player_id=9999, week_of=date(2026, 3, 17),
            status=SnapshotStatus.PASS,
        )
        with pytest.raises(IntegrityError):
            repo.upsert(snap)
            db_session.commit()


# ---------------------------------------------------------------------------
# BenchmarkRepo
# ---------------------------------------------------------------------------

class TestBenchmarkRepo:
    def test_create_and_get_by_week(self, db_session, sample_benchmark):
        repo = BenchmarkRepo(db_session)
        created = repo.create_or_update(sample_benchmark)
        assert created.benchmark_id is not None

        fetched = repo.get_by_week(date(2026, 3, 17))
        assert fetched is not None
        assert fetched.min_mplus_runs == 8

    def test_update_existing(self, db_session, sample_benchmark):
        repo = BenchmarkRepo(db_session)
        repo.create_or_update(sample_benchmark)

        updated = sample_benchmark.model_copy(update={
            "min_mplus_runs": 6,
            "set_by": "OfficerB",
            "set_at": datetime(2026, 3, 18, 12, 0, 0, tzinfo=UTC),
        })
        result = repo.create_or_update(updated)
        assert result.min_mplus_runs == 6
        assert result.set_by == "OfficerB"

    def test_get_most_recent(self, db_session):
        repo = BenchmarkRepo(db_session)
        now = datetime(2026, 3, 17, 18, 0, 0, tzinfo=UTC)
        for week in [date(2026, 3, 3), date(2026, 3, 10), date(2026, 3, 17)]:
            repo.create_or_update(WeeklyBenchmark(
                week_of=week, min_mplus_runs=8, min_key_level=10,
                min_vault_slots=3, set_by="Officer", set_at=now,
            ))
        db_session.commit()

        most_recent = repo.get_most_recent()
        assert most_recent.week_of == date(2026, 3, 17)

    def test_get_most_recent_empty(self, db_session):
        repo = BenchmarkRepo(db_session)
        assert repo.get_most_recent() is None

    def test_list_all(self, db_session):
        repo = BenchmarkRepo(db_session)
        now = datetime(2026, 3, 17, 18, 0, 0, tzinfo=UTC)
        for week in [date(2026, 3, 3), date(2026, 3, 10)]:
            repo.create_or_update(WeeklyBenchmark(
                week_of=week, min_mplus_runs=8, min_key_level=10,
                min_vault_slots=3, set_by="Officer", set_at=now,
            ))
        db_session.commit()
        all_b = repo.list_all()
        assert len(all_b) == 2
        assert all_b[0].week_of > all_b[1].week_of  # desc order


# ---------------------------------------------------------------------------
# NoteRepo
# ---------------------------------------------------------------------------

class TestNoteRepo:
    def _create_player(self, db_session) -> int:
        repo = PlayerRepo(db_session)
        p = repo.create(Player(
            name="NotePlayer", realm="tichondrius", class_name="Priest",
            role="healer", joined_date=date(2026, 3, 1),
        ))
        db_session.commit()
        return p.player_id

    def test_create_and_get_by_player(self, db_session):
        pid = self._create_player(db_session)
        repo = NoteRepo(db_session)
        note_id = repo.create(pid, "Vacation next week", "OfficerA", date(2026, 3, 17))
        assert note_id is not None

        notes = repo.get_by_player(pid)
        assert len(notes) == 1
        assert notes[0]["note_text"] == "Vacation next week"
        assert notes[0]["created_by"] == "OfficerA"

    def test_get_by_player_week(self, db_session):
        pid = self._create_player(db_session)
        repo = NoteRepo(db_session)
        repo.create(pid, "Note for week 17", "OfficerA", date(2026, 3, 17))
        repo.create(pid, "Note for week 24", "OfficerA", date(2026, 3, 24))
        db_session.commit()

        week_17 = repo.get_by_player_week(pid, date(2026, 3, 17))
        assert len(week_17) == 1
        assert week_17[0]["note_text"] == "Note for week 17"

    def test_general_note_no_week(self, db_session):
        pid = self._create_player(db_session)
        repo = NoteRepo(db_session)
        note_id = repo.create(pid, "Player is rerolling", "OfficerB")
        assert note_id is not None

        notes = repo.get_by_player(pid)
        assert len(notes) == 1
        assert notes[0]["week_of"] is None


# ---------------------------------------------------------------------------
# CollectionRunRepo
# ---------------------------------------------------------------------------

class TestCollectionRunRepo:
    def test_create_and_update(self, db_session):
        repo = CollectionRunRepo(db_session)
        run_id = repo.create(date(2026, 3, 17))
        assert run_id is not None

        repo.update(run_id, status="completed", players_collected=25, completed=True)
        db_session.commit()

        runs = repo.get_by_week(date(2026, 3, 17))
        assert len(runs) == 1
        assert runs[0]["status"] == "completed"
        assert runs[0]["players_collected"] == 25
        assert runs[0]["completed_at"] is not None

    def test_partial_failure(self, db_session):
        repo = CollectionRunRepo(db_session)
        run_id = repo.create(date(2026, 3, 17))
        repo.update(
            run_id,
            status="partial",
            players_collected=20,
            api_errors=5,
            error_log="Timeout on 5 players",
            completed=True,
        )
        db_session.commit()

        runs = repo.get_by_week(date(2026, 3, 17))
        assert runs[0]["status"] == "partial"
        assert runs[0]["api_errors"] == 5

    def test_update_missing_run(self, db_session):
        repo = CollectionRunRepo(db_session)
        repo.update(9999, status="completed")  # should not raise


# ---------------------------------------------------------------------------
# SettingsRepo
# ---------------------------------------------------------------------------

class TestSettingsRepo:
    def test_set_and_get(self, db_session):
        repo = SettingsRepo(db_session)
        repo.set("guild.name", "Test Guild", "OfficerA")
        db_session.commit()

        value = repo.get("guild.name")
        assert value == "Test Guild"

    def test_overwrite_existing(self, db_session):
        repo = SettingsRepo(db_session)
        repo.set("guild.name", "Old Name", "OfficerA")
        repo.set("guild.name", "New Name", "OfficerB")
        db_session.commit()

        assert repo.get("guild.name") == "New Name"

    def test_get_missing_key(self, db_session):
        repo = SettingsRepo(db_session)
        assert repo.get("nonexistent.key") is None

    def test_list_all(self, db_session):
        repo = SettingsRepo(db_session)
        repo.set("a.key", "val1", "system")
        repo.set("b.key", "val2", "system")
        db_session.commit()

        all_settings = repo.list_all()
        assert len(all_settings) == 2
        assert all_settings["a.key"] == "val1"

    def test_seed_from_config(self, db_session):
        repo = SettingsRepo(db_session)
        config = {
            "collection.hours_after_reset": 3,
            "analysis.chronic_fail_threshold": 3,
            "guild.name": "",
        }
        count = repo.seed_from_config(config)
        assert count == 3

        assert repo.get("collection.hours_after_reset") == "3"

    def test_seed_does_not_overwrite(self, db_session):
        repo = SettingsRepo(db_session)
        repo.set("guild.name", "Already Set", "OfficerA")
        db_session.commit()

        config = {"guild.name": "Default"}
        count = repo.seed_from_config(config)
        assert count == 0
        assert repo.get("guild.name") == "Already Set"


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    def test_all_tables_created(self, engine):
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected = [
            "collection_runs",
            "officer_notes",
            "players",
            "settings",
            "weekly_benchmarks",
            "weekly_snapshots",
        ]
        for table in expected:
            assert table in tables, f"Table '{table}' not found"
