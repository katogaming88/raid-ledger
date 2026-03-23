"""Player domain model and status enum."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PlayerStatus(StrEnum):
    """Roster status for a player."""

    CORE = "core"
    TRIAL = "trial"
    BENCH = "bench"
    INACTIVE = "inactive"


class Player(BaseModel):
    """A raider on the guild roster.

    Names support UTF-8 (accented characters like Ñ, Ö).
    Realms are stored as slugs (e.g. "bleeding-hollow").
    """

    model_config = ConfigDict(frozen=True)

    player_id: int | None = None
    name: str
    realm: str
    region: str = "us"
    class_name: str
    spec_name: str | None = None
    role: str
    status: PlayerStatus = PlayerStatus.CORE
    joined_date: date
    created_at: datetime | None = None
    updated_at: datetime | None = None
