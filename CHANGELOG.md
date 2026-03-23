# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-03-23

**Milestone M1: Models + DB**

### Added

- Pydantic domain models: `Player`, `WeeklySnapshot`, `WeeklyBenchmark` (all frozen)
- Enums: `PlayerStatus`, `SnapshotStatus`, `FailureReason`, `FlagReason`
- SQLAlchemy 2.0 ORM schema with 6 tables: `players`, `weekly_benchmarks`, `weekly_snapshots`, `officer_notes`, `collection_runs`, `settings`
- All indexes per design: composite unique constraints, status indexes, week lookups
- Repository classes: `PlayerRepo`, `SnapshotRepo`, `BenchmarkRepo`, `NoteRepo`, `CollectionRunRepo`, `SettingsRepo`
- Snapshot upsert on `UNIQUE(player_id, week_of)` for safe re-runs
- `AppConfig` with Pydantic Settings loading from `config/default.toml` + env var overrides
- SQLite (dev) and PostgreSQL (prod) dual support via `DATABASE_URL`
- 59 tests covering models, config, and all repository CRUD operations
- README, CHANGELOG, CLAUDE.md

## [0.1.0] — 2026-03-23

### Added

- Project scaffold: directory structure, pyproject.toml, config/default.toml
- Dependencies: pydantic, sqlalchemy, httpx, typer, python-dotenv
- Dev dependencies: pytest, pytest-cov, ruff, respx
- .gitignore, LICENSE (MIT), .env.example
- GitHub Actions CI pipeline (pytest + ruff)
