# Raid Ledger — Project Instructions

## Overview

Weekly M+ accountability system for WoW CE guilds.
Raider.io API -> SQLAlchemy -> Streamlit dashboard.

## Stack

Python 3.11+, Pydantic v2 (frozen models), SQLAlchemy 2.0, httpx, Streamlit
SQLite for dev, Supabase PostgreSQL for prod (DATABASE_URL env var)

## Virtual Environment

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev,dashboard]"
```

## Key Architecture

- `raid_ledger/models/` — Pydantic domain models (frozen)
- `raid_ledger/db/schema.py` — SQLAlchemy ORM, 6 tables
- `raid_ledger/db/repositories.py` — CRUD, returns Pydantic models (not ORM objects)
- `raid_ledger/api/raiderio.py` — httpx client, 2 endpoints (character + guild)
- `raid_ledger/engine/rules.py` — 3-state evaluation (pass/fail/flag), OR logic
- `raid_ledger/engine/collector.py` — weekly orchestrator, upserts
- `raid_ledger/engine/analyzer.py` — pattern detection queries
- `dashboard/` — Streamlit app, separate from installable package
- `raid_ledger/config.py` — Pydantic Settings, loads from config/default.toml + env vars

## Key Decisions

- `week_of` is always a Tuesday (WoW US reset day)
- Snapshots have 3 states: pass/fail/flag (not boolean)
- `reasons` column stores JSON TEXT (not JSONB) for SQLite compatibility
- `raw_api_response` stored for re-evaluation — never included in SELECT for dashboard queries
- ON DELETE RESTRICT on all FKs — players deactivated, never deleted
- All user-facing settings in DB (settings table), not TOML files
- Vault slots derived from M+ count only (MVP) — no separate vault check
- Repos return Pydantic models, not ORM objects

## Tests

```bash
pytest --tb=short -q                    # all tests
pytest -m integration --tb=short        # live API tests (needs network)
pytest --cov=raid_ledger               # with coverage
```

## Lint

```bash
ruff check raid_ledger/ tests/
```
