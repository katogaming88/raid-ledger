"""Weekly benchmark model — defines requirements for each reset week."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class WeeklyBenchmark(BaseModel):
    """Officer-configured requirements for a specific reset week.

    week_of is always a Tuesday. Each week has its own benchmark row —
    changing next week's requirements does not affect past weeks.
    """

    model_config = ConfigDict(frozen=True)

    benchmark_id: int | None = None
    week_of: date
    min_mplus_runs: int
    min_key_level: int
    min_ilvl: int | None = None
    min_vault_slots: int
    set_by: str
    set_at: datetime
