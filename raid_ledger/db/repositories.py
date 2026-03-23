"""Repository classes — CRUD operations that return Pydantic models, not ORM objects."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from raid_ledger.db.schema import (
    CollectionRunRow,
    OfficerNoteRow,
    PlayerRow,
    SettingRow,
    WeeklyBenchmarkRow,
    WeeklySnapshotRow,
)
from raid_ledger.models.benchmark import WeeklyBenchmark
from raid_ledger.models.player import Player, PlayerStatus
from raid_ledger.models.snapshot import WeeklySnapshot


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

def _player_from_row(row: PlayerRow) -> Player:
    return Player(
        player_id=row.player_id,
        name=row.name,
        realm=row.realm,
        region=row.region,
        class_name=row.class_name,
        spec_name=row.spec_name,
        role=row.role,
        status=PlayerStatus(row.status),
        joined_date=row.joined_date,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PlayerRepo:

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, player: Player) -> Player:
        row = PlayerRow(
            name=player.name,
            realm=player.realm,
            region=player.region,
            class_name=player.class_name,
            spec_name=player.spec_name,
            role=player.role,
            status=player.status.value,
            joined_date=player.joined_date,
        )
        self._session.add(row)
        self._session.flush()
        return _player_from_row(row)

    def get_by_id(self, player_id: int) -> Player | None:
        row = self._session.get(PlayerRow, player_id)
        return _player_from_row(row) if row else None

    def get_by_name_realm_region(
        self, name: str, realm: str, region: str = "us"
    ) -> Player | None:
        stmt = select(PlayerRow).where(
            PlayerRow.name == name,
            PlayerRow.realm == realm,
            PlayerRow.region == region,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return _player_from_row(row) if row else None

    def get_active(self) -> list[Player]:
        stmt = select(PlayerRow).where(
            PlayerRow.status.in_(["core", "trial"])
        ).order_by(PlayerRow.name)
        rows = self._session.execute(stmt).scalars().all()
        return [_player_from_row(r) for r in rows]

    def update_status(self, player_id: int, status: PlayerStatus) -> Player | None:
        row = self._session.get(PlayerRow, player_id)
        if row is None:
            return None
        row.status = status.value
        self._session.flush()
        return _player_from_row(row)

    def list_all(self) -> list[Player]:
        stmt = select(PlayerRow).order_by(PlayerRow.name)
        rows = self._session.execute(stmt).scalars().all()
        return [_player_from_row(r) for r in rows]


# ---------------------------------------------------------------------------
# WeeklySnapshot
# ---------------------------------------------------------------------------

def _snapshot_from_row(row: WeeklySnapshotRow) -> WeeklySnapshot:
    reasons_raw = row.reasons
    if reasons_raw:
        reasons = json.loads(reasons_raw)
    else:
        reasons = []
    return WeeklySnapshot(
        snapshot_id=row.snapshot_id,
        player_id=row.player_id,
        week_of=row.week_of,
        mplus_runs_total=row.mplus_runs_total,
        mplus_runs_at_level=row.mplus_runs_at_level,
        highest_key_level=row.highest_key_level,
        item_level=row.item_level,
        vault_slots_earned=row.vault_slots_earned,
        raiderio_score=row.raiderio_score,
        status=row.status,
        reasons=reasons,
        override_by=row.override_by,
        data_source=row.data_source,
        raw_api_response=row.raw_api_response,
        collected_at=row.collected_at,
    )


class SnapshotRepo:

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, snapshot: WeeklySnapshot) -> WeeklySnapshot:
        """Insert or update a snapshot for (player_id, week_of)."""
        stmt = select(WeeklySnapshotRow).where(
            WeeklySnapshotRow.player_id == snapshot.player_id,
            WeeklySnapshotRow.week_of == snapshot.week_of,
        )
        row = self._session.execute(stmt).scalar_one_or_none()

        reasons_json = json.dumps(snapshot.reasons) if snapshot.reasons else None

        if row is None:
            row = WeeklySnapshotRow(
                player_id=snapshot.player_id,
                week_of=snapshot.week_of,
                mplus_runs_total=snapshot.mplus_runs_total,
                mplus_runs_at_level=snapshot.mplus_runs_at_level,
                highest_key_level=snapshot.highest_key_level,
                item_level=snapshot.item_level,
                vault_slots_earned=snapshot.vault_slots_earned,
                raiderio_score=snapshot.raiderio_score,
                status=str(snapshot.status),
                reasons=reasons_json,
                override_by=snapshot.override_by,
                data_source=snapshot.data_source,
                raw_api_response=snapshot.raw_api_response,
            )
            self._session.add(row)
        else:
            row.mplus_runs_total = snapshot.mplus_runs_total
            row.mplus_runs_at_level = snapshot.mplus_runs_at_level
            row.highest_key_level = snapshot.highest_key_level
            row.item_level = snapshot.item_level
            row.vault_slots_earned = snapshot.vault_slots_earned
            row.raiderio_score = snapshot.raiderio_score
            row.status = str(snapshot.status)
            row.reasons = reasons_json
            row.override_by = snapshot.override_by
            row.data_source = snapshot.data_source
            row.raw_api_response = snapshot.raw_api_response
            row.collected_at = _utcnow()

        self._session.flush()
        return _snapshot_from_row(row)

    def get_by_player_week(self, player_id: int, week_of: date) -> WeeklySnapshot | None:
        stmt = select(WeeklySnapshotRow).where(
            WeeklySnapshotRow.player_id == player_id,
            WeeklySnapshotRow.week_of == week_of,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return _snapshot_from_row(row) if row else None

    def get_by_week(self, week_of: date) -> list[WeeklySnapshot]:
        stmt = (
            select(WeeklySnapshotRow)
            .where(WeeklySnapshotRow.week_of == week_of)
            .order_by(WeeklySnapshotRow.player_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [_snapshot_from_row(r) for r in rows]

    def get_player_history(
        self, player_id: int, weeks: int | None = None
    ) -> list[WeeklySnapshot]:
        stmt = (
            select(WeeklySnapshotRow)
            .where(WeeklySnapshotRow.player_id == player_id)
            .order_by(WeeklySnapshotRow.week_of.desc())
        )
        if weeks is not None:
            stmt = stmt.limit(weeks)
        rows = self._session.execute(stmt).scalars().all()
        return [_snapshot_from_row(r) for r in rows]


# ---------------------------------------------------------------------------
# WeeklyBenchmark
# ---------------------------------------------------------------------------

def _benchmark_from_row(row: WeeklyBenchmarkRow) -> WeeklyBenchmark:
    return WeeklyBenchmark(
        benchmark_id=row.benchmark_id,
        week_of=row.week_of,
        min_mplus_runs=row.min_mplus_runs,
        min_key_level=row.min_key_level,
        min_ilvl=row.min_ilvl,
        min_vault_slots=row.min_vault_slots,
        set_by=row.set_by,
        set_at=row.set_at,
    )


class BenchmarkRepo:

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_or_update(self, benchmark: WeeklyBenchmark) -> WeeklyBenchmark:
        """Insert or update a benchmark for a given week_of."""
        stmt = select(WeeklyBenchmarkRow).where(
            WeeklyBenchmarkRow.week_of == benchmark.week_of
        )
        row = self._session.execute(stmt).scalar_one_or_none()

        if row is None:
            row = WeeklyBenchmarkRow(
                week_of=benchmark.week_of,
                min_mplus_runs=benchmark.min_mplus_runs,
                min_key_level=benchmark.min_key_level,
                min_ilvl=benchmark.min_ilvl,
                min_vault_slots=benchmark.min_vault_slots,
                set_by=benchmark.set_by,
                set_at=benchmark.set_at,
            )
            self._session.add(row)
        else:
            row.min_mplus_runs = benchmark.min_mplus_runs
            row.min_key_level = benchmark.min_key_level
            row.min_ilvl = benchmark.min_ilvl
            row.min_vault_slots = benchmark.min_vault_slots
            row.set_by = benchmark.set_by
            row.set_at = benchmark.set_at

        self._session.flush()
        return _benchmark_from_row(row)

    def get_by_week(self, week_of: date) -> WeeklyBenchmark | None:
        stmt = select(WeeklyBenchmarkRow).where(
            WeeklyBenchmarkRow.week_of == week_of
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return _benchmark_from_row(row) if row else None

    def get_most_recent(self) -> WeeklyBenchmark | None:
        stmt = (
            select(WeeklyBenchmarkRow)
            .order_by(WeeklyBenchmarkRow.week_of.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return _benchmark_from_row(row) if row else None

    def list_all(self) -> list[WeeklyBenchmark]:
        stmt = select(WeeklyBenchmarkRow).order_by(WeeklyBenchmarkRow.week_of.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [_benchmark_from_row(r) for r in rows]


# ---------------------------------------------------------------------------
# OfficerNote
# ---------------------------------------------------------------------------

class NoteRepo:

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        player_id: int,
        note_text: str,
        created_by: str,
        week_of: date | None = None,
    ) -> int:
        row = OfficerNoteRow(
            player_id=player_id,
            week_of=week_of,
            note_text=note_text,
            created_by=created_by,
        )
        self._session.add(row)
        self._session.flush()
        return row.note_id

    def get_by_player(self, player_id: int) -> list[dict]:
        stmt = (
            select(OfficerNoteRow)
            .where(OfficerNoteRow.player_id == player_id)
            .order_by(OfficerNoteRow.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [
            {
                "note_id": r.note_id,
                "player_id": r.player_id,
                "week_of": r.week_of,
                "note_text": r.note_text,
                "created_by": r.created_by,
                "created_at": r.created_at,
            }
            for r in rows
        ]

    def get_by_player_week(self, player_id: int, week_of: date) -> list[dict]:
        stmt = (
            select(OfficerNoteRow)
            .where(
                OfficerNoteRow.player_id == player_id,
                OfficerNoteRow.week_of == week_of,
            )
            .order_by(OfficerNoteRow.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [
            {
                "note_id": r.note_id,
                "player_id": r.player_id,
                "week_of": r.week_of,
                "note_text": r.note_text,
                "created_by": r.created_by,
                "created_at": r.created_at,
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# CollectionRun
# ---------------------------------------------------------------------------

class CollectionRunRepo:

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, week_of: date, status: str = "started") -> int:
        row = CollectionRunRow(
            week_of=week_of,
            status=status,
            started_at=_utcnow(),
        )
        self._session.add(row)
        self._session.flush()
        return row.run_id

    def update(
        self,
        run_id: int,
        *,
        status: str | None = None,
        players_collected: int | None = None,
        api_errors: int | None = None,
        error_log: str | None = None,
        completed: bool = False,
    ) -> None:
        row = self._session.get(CollectionRunRow, run_id)
        if row is None:
            return
        if status is not None:
            row.status = status
        if players_collected is not None:
            row.players_collected = players_collected
        if api_errors is not None:
            row.api_errors = api_errors
        if error_log is not None:
            row.error_log = error_log
        if completed:
            row.completed_at = _utcnow()
        self._session.flush()

    def get_by_week(self, week_of: date) -> list[dict]:
        stmt = (
            select(CollectionRunRow)
            .where(CollectionRunRow.week_of == week_of)
            .order_by(CollectionRunRow.started_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [
            {
                "run_id": r.run_id,
                "week_of": r.week_of,
                "status": r.status,
                "players_collected": r.players_collected,
                "api_errors": r.api_errors,
                "error_log": r.error_log,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Settings (key-value store)
# ---------------------------------------------------------------------------

class SettingsRepo:

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> str | None:
        row = self._session.get(SettingRow, key)
        return row.value if row else None

    def set(self, key: str, value: str, set_by: str) -> None:
        row = self._session.get(SettingRow, key)
        now = _utcnow()
        if row is None:
            row = SettingRow(key=key, value=value, set_by=set_by, set_at=now)
            self._session.add(row)
        else:
            row.value = value
            row.set_by = set_by
            row.set_at = now
        self._session.flush()

    def list_all(self) -> dict[str, str]:
        stmt = select(SettingRow).order_by(SettingRow.key)
        rows = self._session.execute(stmt).scalars().all()
        return {r.key: r.value for r in rows}

    def seed_from_config(self, config_dict: dict, set_by: str = "system") -> int:
        """Seed settings from a flat dict. Only inserts keys that don't exist yet.

        Returns the number of keys seeded.
        """
        count = 0
        now = _utcnow()
        for key, value in config_dict.items():
            existing = self._session.get(SettingRow, key)
            if existing is None:
                row = SettingRow(
                    key=key,
                    value=json.dumps(value) if not isinstance(value, str) else value,
                    set_by=set_by,
                    set_at=now,
                )
                self._session.add(row)
                count += 1
        self._session.flush()
        return count
