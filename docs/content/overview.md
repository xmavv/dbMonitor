# PG Inspector Documentation

PG Inspector is a lightweight web dashboard for monitoring and analyzing **PostgreSQL** performance in real time. It surfaces expensive queries, table health, index usage, locks, triggers, and server extensions — without writing SQL against system catalogs yourself.

<div class="doc-callout doc-callout-info">
<strong>Who is this for?</strong> DBAs, backend developers, and students who need to understand what PostgreSQL is doing under load — whether you're debugging a slow app, investigating locks, or learning how indexes affect query plans.
</div>

## Requirements

| Requirement | Details |
|-------------|---------|
| **PostgreSQL** | Version 15 recommended (tested target) |
| **Python** | 3.11+ for local runs |
| **Docker** | Optional but recommended — runs Postgres + app together |
| **Extension** | `pg_stat_statements` must be loaded via `shared_preload_libraries` for Top Queries |

The app reads from PostgreSQL system views (`pg_stat_*`, `pg_locks`, `pg_stat_activity`, etc.). It does **not** modify your data — only `SELECT` and `EXPLAIN` for plan analysis.

## Architecture at a glance

```
Browser (index.html + app.js)
        │  fetch /api/*
        ▼
Flask (app.py) — REST endpoints
        │
        ▼
db.py — SQL against pg_stat_* views
        │
        ▼
PostgreSQL 15
```

## Dashboard modules

| Module | What it shows |
|--------|---------------|
| **Top Queries** | Most expensive queries from `pg_stat_statements` |
| **Table Health** | Live/dead tuples, scan ratios, VACUUM/ANALYZE dates, cache hit |
| **DB Sizes** | Table vs index disk usage with visual bars |
| **Index Usage** | Index scan counts, unused and duplicate index detection |
| **Lock Monitor** | Blocking chains and long-running active queries |
| **Triggers** | Installed triggers with status and definition |
| **Extensions** | Installed PostgreSQL extensions |

## Quick links

- [Getting Started](/docs/getting-started) — run the stack in minutes
- [Configuration](/docs/configuration) — environment variables
- [Color Legend](/docs/color-legend) — what red, yellow, and green mean
- [Common Scenarios](/docs/scenarios) — step-by-step troubleshooting flows
