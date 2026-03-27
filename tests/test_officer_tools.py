"""Tests for officer tools business logic — roster import, benchmarks, notes."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from raid_ledger.api.wowaudit import WowauditClient, WowauditRosterMember
from raid_ledger.db.repositories import BenchmarkRepo, NoteRepo, PlayerRepo
from raid_ledger.engine.collector import NoBenchmarkError, WeeklyCollector
from raid_ledger.models.benchmark import WeeklyBenchmark
from raid_ledger.models.player import Player, PlayerStatus
from raid_ledger.utils import most_recent_tuesday

# ---------------------------------------------------------------------------
# Roster import logic
# ---------------------------------------------------------------------------


class TestRosterImport:
    def test_import_new_player(self, db_session):
        """WowauditRosterMember maps to Player and is created in DB."""
        member = WowauditRosterMember(
            wowaudit_id=100, name="Testplayer", realm="Tichondrius",
            class_name="Warlock", role="dps", rank="Main",
            status="tracking", blizzard_id=12345,
        )
        repo = PlayerRepo(db_session)
        player = repo.create(Player(
            name=member.name, realm=member.realm, region="us",
            class_name=member.class_name, role=member.role,
            status=PlayerStatus.CORE, joined_date=date.today(),
        ))
        db_session.commit()

        assert player.player_id is not None
        assert player.name == "Testplayer"
        assert player.role == "dps"
        assert player.status == PlayerStatus.CORE

    def test_skip_duplicate(self, db_session):
        """Player that already exists is detected by get_by_name_realm_region."""
        repo = PlayerRepo(db_session)
        repo.create(Player(
            name="Existing", realm="Tichondrius", region="us",
            class_name="Mage", role="dps", status=PlayerStatus.CORE,
            joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        existing = repo.get_by_name_realm_region("Existing", "Tichondrius")
        assert existing is not None

    def test_role_mapping_preserved(self, db_session):
        """WowauditRosterMember roles (tank/healer/dps) flow through correctly."""
        members = [
            WowauditRosterMember(
                wowaudit_id=1, name="Tank", realm="Test",
                class_name="DK", role="tank", rank="Main", status="tracking",
            ),
            WowauditRosterMember(
                wowaudit_id=2, name="Healer", realm="Test",
                class_name="Priest", role="healer", rank="Main", status="tracking",
            ),
            WowauditRosterMember(
                wowaudit_id=3, name="Dps", realm="Test",
                class_name="Rogue", role="dps", rank="Main", status="tracking",
            ),
        ]
        repo = PlayerRepo(db_session)
        for m in members:
            repo.create(Player(
                name=m.name, realm=m.realm, region="us",
                class_name=m.class_name, role=m.role,
                status=PlayerStatus.CORE, joined_date=date.today(),
            ))
        db_session.commit()

        all_players = repo.list_all()
        roles = {p.name: p.role for p in all_players}
        assert roles["Tank"] == "tank"
        assert roles["Healer"] == "healer"
        assert roles["Dps"] == "dps"


# ---------------------------------------------------------------------------
# Player management
# ---------------------------------------------------------------------------


class TestPlayerManagement:
    def test_update_status(self, db_session):
        repo = PlayerRepo(db_session)
        player = repo.create(Player(
            name="P1", realm="Test", class_name="Mage",
            role="dps", status=PlayerStatus.CORE, joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        updated = repo.update_status(player.player_id, PlayerStatus.BENCH)
        db_session.commit()

        assert updated.status == PlayerStatus.BENCH

    def test_deactivate_player(self, db_session):
        repo = PlayerRepo(db_session)
        player = repo.create(Player(
            name="P1", realm="Test", class_name="Mage",
            role="dps", status=PlayerStatus.CORE, joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        repo.update_status(player.player_id, PlayerStatus.INACTIVE)
        db_session.commit()

        # Inactive player not in active list
        active = repo.get_active()
        assert len(active) == 0

        # But still in full list
        all_p = repo.list_all()
        assert len(all_p) == 1


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


class TestBenchmarks:
    def test_create_benchmark(self, db_session):
        repo = BenchmarkRepo(db_session)
        b = repo.create_or_update(WeeklyBenchmark(
            week_of=date(2026, 3, 17),
            min_mplus_runs=8, min_key_level=10,
            min_ilvl=None, min_vault_slots=3,
            set_by="Officer", set_at=datetime.now(tz=UTC),
        ))
        db_session.commit()

        assert b.benchmark_id is not None
        assert b.min_mplus_runs == 8

    def test_upsert_benchmark(self, db_session):
        repo = BenchmarkRepo(db_session)
        repo.create_or_update(WeeklyBenchmark(
            week_of=date(2026, 3, 17),
            min_mplus_runs=8, min_key_level=10,
            min_ilvl=None, min_vault_slots=3,
            set_by="Officer1", set_at=datetime.now(tz=UTC),
        ))
        db_session.commit()

        # Update same week
        repo.create_or_update(WeeklyBenchmark(
            week_of=date(2026, 3, 17),
            min_mplus_runs=10, min_key_level=12,
            min_ilvl=None, min_vault_slots=3,
            set_by="Officer2", set_at=datetime.now(tz=UTC),
        ))
        db_session.commit()

        result = repo.get_by_week(date(2026, 3, 17))
        assert result.min_mplus_runs == 10
        assert result.set_by == "Officer2"

    def test_week_of_tuesday_validation(self):
        """most_recent_tuesday snaps non-Tuesdays to the prior Tuesday."""
        # Wednesday March 18 -> Tuesday March 17
        assert most_recent_tuesday(date(2026, 3, 18)) == date(2026, 3, 17)
        # Tuesday stays
        assert most_recent_tuesday(date(2026, 3, 17)) == date(2026, 3, 17)


# ---------------------------------------------------------------------------
# Officer notes
# ---------------------------------------------------------------------------


class TestOfficerNotes:
    def test_add_note_with_week(self, db_session):
        player_repo = PlayerRepo(db_session)
        player = player_repo.create(Player(
            name="P1", realm="Test", class_name="Mage",
            role="dps", status=PlayerStatus.CORE, joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        note_repo = NoteRepo(db_session)
        note_id = note_repo.create(
            player_id=player.player_id,
            note_text="Missed raid, excused",
            created_by="OfficerA",
            week_of=date(2026, 3, 17),
        )
        db_session.commit()

        assert note_id is not None
        notes = note_repo.get_by_player_week(player.player_id, date(2026, 3, 17))
        assert len(notes) == 1
        assert notes[0]["note_text"] == "Missed raid, excused"
        assert notes[0]["created_by"] == "OfficerA"

    def test_add_general_note(self, db_session):
        player_repo = PlayerRepo(db_session)
        player = player_repo.create(Player(
            name="P1", realm="Test", class_name="Mage",
            role="dps", status=PlayerStatus.CORE, joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        note_repo = NoteRepo(db_session)
        note_repo.create(
            player_id=player.player_id,
            note_text="Good attitude, considering for officer",
            created_by="OfficerB",
        )
        db_session.commit()

        notes = note_repo.get_by_player(player.player_id)
        assert len(notes) == 1
        assert notes[0]["week_of"] is None


# ---------------------------------------------------------------------------
# Collection trigger (mock)
# ---------------------------------------------------------------------------


class TestCollectionTrigger:
    @pytest.mark.anyio
    async def test_collection_no_benchmark_raises(self, db_session):
        """Collection without a benchmark raises NoBenchmarkError."""
        from unittest.mock import AsyncMock

        from raid_ledger.config import AppConfig, CollectionConfig, WowauditConfig

        player_repo = PlayerRepo(db_session)
        player_repo.create(Player(
            name="P1", realm="Test", class_name="Mage",
            role="dps", status=PlayerStatus.CORE, joined_date=date(2026, 3, 1),
        ))
        db_session.commit()

        cfg = AppConfig(
            collection=CollectionConfig(request_delay_seconds=0, max_retries=1),
            wowaudit=WowauditConfig(base_url="https://wowaudit.com", api_key="test"),
        )
        client = WowauditClient(
            wowaudit_config=cfg.wowaudit,
            collection_config=cfg.collection,
        )
        client.fetch_historical_data = AsyncMock(return_value=(1055, {}))

        collector = WeeklyCollector(db_session, client, cfg)
        with pytest.raises(NoBenchmarkError):
            await collector.collect(date(2026, 3, 17))
