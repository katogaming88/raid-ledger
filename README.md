# Raid Ledger

Weekly M+ accountability system for WoW CE progression guilds.
Track every raider every week. Flag who's behind, why, and whether it's a pattern.

## What It Does

- Automatically pulls M+ data from Raider.io after weekly reset
- Evaluates each raider against configurable weekly requirements
- Three-state verdicts: Pass / Fail / Flag (needs officer attention)
- Tracks failure patterns over time (chronic underperformers, streaks)
- Officer dashboard with full roster management, notes, and manual overrides

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| API | Raider.io (free, no auth required) |
| ORM | SQLAlchemy 2.0 |
| DB (dev) | SQLite |
| DB (prod) | Supabase PostgreSQL |
| Dashboard | Streamlit Community Cloud |
| Config | Pydantic + TOML |
| HTTP | httpx |
| CI | GitHub Actions (pytest + ruff) |

## Local Development

```bash
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev,dashboard]"
```

### Run Tests

```bash
pytest --tb=short -q
```

### Lint

```bash
ruff check raid_ledger/ tests/
```

## Project Structure

```
raid_ledger/
├── __init__.py          # Package version
├── config.py            # Pydantic Settings (TOML + env vars)
├── models/
│   ├── player.py        # Player model, PlayerStatus enum
│   ├── snapshot.py       # WeeklySnapshot, SnapshotStatus, FailureReason, FlagReason
│   └── benchmark.py      # WeeklyBenchmark model
├── db/
│   ├── connection.py     # SQLAlchemy engine + session factory
│   ├── schema.py         # ORM tables (6 tables + indexes)
│   └── repositories.py   # CRUD repos returning Pydantic models
├── api/                  # Raider.io HTTP client (M2)
├── engine/               # Rules engine + collector + analyzer (M3-M4)
└── cli.py                # Typer CLI (M7)
```

## Database

Six tables: `players`, `weekly_benchmarks`, `weekly_snapshots`, `officer_notes`, `collection_runs`, `settings`.

- SQLite for local development (zero config)
- PostgreSQL (Supabase) for production via `DATABASE_URL` env var
- All foreign keys use `ON DELETE RESTRICT` — players are deactivated, never deleted

## Configuration

`config/default.toml` provides seed values. After first run, the database `settings` table is the source of truth. All settings are editable through the dashboard Settings page.

## License

MIT
