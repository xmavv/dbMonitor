# Getting Started

## Run with Docker (recommended)

The fastest way to start PG Inspector with a sample database:

```bash
docker compose up --build
```

After startup:

| Service | URL / connection |
|---------|------------------|
| **Dashboard** | [http://localhost:5001](http://localhost:5001) |
| **Documentation** | [http://localhost:5001/docs](http://localhost:5001/docs) |
| **PostgreSQL** | `localhost:5432` — db `mydb`, user `postgres`, password `postgres` |

`docker-compose.yml` starts two services:

- **postgres** — PostgreSQL 15 with `pg_stat_statements` preloaded
- **db-inspector** — Flask app; waits until Postgres is healthy

> By default the Postgres data volume is commented out, so data is ephemeral. Uncomment `volumes` in `docker-compose.yml` to persist data.

## Local run

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables (see [Configuration](/docs/configuration)):

   ```bash
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=postgres
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DB=mydb
   ```

3. Start the app:

   ```bash
   python app.py
   ```

   Open [http://localhost:5001](http://localhost:5001).

On first start the app runs `setup_database`: creates `pg_stat_statements`, a read-only `inspector` user, and grants `pg_read_all_stats`. Requires a privileged DB account (e.g. `postgres`).

## Using the dashboard

<div class="doc-mock">
<div class="doc-mock-label">Panel layout</div>
<pre class="doc-ascii">┌──────────────┬────────────────────────────────────────────┐
│  SIDEBAR     │  Page title                           ● live │
│  Top Queries │────────────────────────────────────────────│
│  Table Health│  Tables, metrics, cards                    │
│  ...         │                                            │
│  ↺ Refresh   │                                            │
└──────────────┴────────────────────────────────────────────┘</pre>
</div>

- **Sidebar** — switch views with one click
- **Green dot** (top right) — database connection is alive
- **↺ Refresh** — reload data for the current view (data does not auto-refresh)
- **Docs** link — opens this documentation site

## Load sample data (optional)

Scripts in `scripts/` populate the **`demo`** schema for live presentations:

```bash
python scripts/demo_init.py
python scripts/demo_run_sql.py demo_triggers.sql
python scripts/demo_run_sql.py demo_index_usage.sql
python scripts/demo_run_sql.py demo_db_sizes.sql
python scripts/demo_run_sql.py demo_extensions.sql
python scripts/demo_top_queries.py
python scripts/demo_table_health.py
python scripts/demo_locks.py
```

See **`scripts/README.md`** in the repository for the full per-panel demo guide (run → dashboard → docs keywords).
