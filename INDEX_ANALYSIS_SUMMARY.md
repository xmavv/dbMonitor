# Index Analysis Feature — Summary

## What was built

An extension to the existing DB Inspector tool that lets you analyze how PostgreSQL indexes affect query performance. Two new pages were added:

1. **Index Usage page** (`/indexes`) — shows all user-created indexes and how often they are actually used
2. **Query Analysis page** (`/analyze`) — compares the execution plan of a SELECT query with and without indexes, side by side

## How it works

### Index Usage table

The `/indexes` page queries the `pg_stat_user_indexes` system view, which PostgreSQL maintains automatically. It tracks every index on user-created tables (excludes system/internal indexes).

#### Column definitions

| Column | What it means |
|---|---|
| **Schema** | The database schema the table belongs to (usually `public`) |
| **Table** | The table the index is built on |
| **Index** | The name of the index |
| **Scans** (`idx_scan`) | How many times PostgreSQL has used this index to look up data since the last stats reset. **0 means the index is never used** — it takes up disk space and slows down writes (INSERT/UPDATE/DELETE) for no benefit |
| **Tuples Read** (`idx_tup_read`) | Number of index entries returned by scans on this index. This is how many rows the index pointed to |
| **Tuples Fetched** (`idx_tup_fetch`) | Number of actual table rows fetched using this index. Can be lower than Tuples Read if some rows were filtered out or already in memory |
| **Size** | Disk space the index occupies |

Rows with 0 scans are highlighted in red — these are candidates for removal.

### Query Analysis (EXPLAIN comparison)

From the main page, each SELECT query captured by `pg_stat_statements` has an "Analyze" button. Clicking it runs `EXPLAIN` on the query twice:

1. **With indexes** — normal execution, PostgreSQL planner chooses the optimal strategy
2. **Without indexes** — session-level settings `enable_indexscan = off` and `enable_bitmapscan = off` force the planner to ignore all indexes

This produces two execution plans side by side. Key things to look for:

| With Indexes | Without Indexes | Interpretation |
|---|---|---|
| Index Scan | Seq Scan | Index is helping — it avoids reading the whole table |
| Seq Scan | Seq Scan | No useful index exists, or the planner chose not to use one anyway |
| Nested Loop + Index Scan | Hash Join + Seq Scan | Index enables a more efficient join strategy |
| Bitmap Index Scan | Seq Scan | Index is used for range queries or conditions matching many rows |

## Why this approach (and not dropping indexes)

The initial idea was to drop indexes, re-run queries, and compare times. This approach was rejected because:

- **Dropping indexes is destructive** — affects all connections, not just the test
- **Rebuilding indexes is slow** — can take minutes to hours on large tables
- **Caching pollutes results** — the second run is always faster because data is in memory

Instead, PostgreSQL provides session-level planner settings (`SET enable_indexscan = off`) that simulate the absence of indexes **without modifying the schema**. These settings only affect the current database session — other users and connections are not impacted.

## Technical implementation

### Backend (`db.py`)

Three functions were added:

- `load_indexes(conn)` — queries `pg_stat_user_indexes` for index usage statistics
- `explain_query(conn, query)` — runs EXPLAIN with and without index scans using session-level `SET` commands, returns both plans
- `load_stats(conn)` — updated to also return `queryid` for query identification

### Frontend (`app.py`)

Two new routes:

- `GET /indexes` — renders the index usage table
- `POST /analyze` — accepts a query, runs the dual EXPLAIN, renders side-by-side comparison

The main page (`/`) was updated to show an "Analyze" button on each SELECT query and a link to the indexes page.

### Safety measures

- Only SELECT queries can be analyzed (the button only appears on SELECTs, and the endpoint rejects anything else)
- `EXPLAIN` without `ANALYZE` is used — it shows the plan without actually executing the query, which matters because `pg_stat_statements` stores parameterized queries ($1, $2) that cannot be executed without values
- Planner settings are always reset to defaults after comparison, even if an error occurs

## Infrastructure changes (`docker-compose.yml`)

- Added a named volume (`pgdata`) for PostgreSQL data persistence — database survives container restarts
- Added source code mount (`.:/app`) for the Flask app — code changes are reflected immediately without rebuilding
- Flask runs in debug mode for auto-reload during development

## Tools and technologies used

| Component | Technology |
|---|---|
| Query capture | `pg_stat_statements` PostgreSQL extension |
| Index monitoring | `pg_stat_user_indexes` system view |
| Plan comparison | `EXPLAIN` with session-level planner settings |
| Backend | Python 3.11, Flask, psycopg2 |
| Database | PostgreSQL 15 |
| Test data | Pagila sample database |
| Deployment | Docker, Docker Compose |
