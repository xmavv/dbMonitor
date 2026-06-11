# API Reference

All endpoints return **JSON**. On error: `{"error": "message"}`.

## Endpoints

| Method | Path | Description | Data source |
|--------|------|-------------|-------------|
| `GET` | `/` | Dashboard (HTML) | — |
| `GET` | `/docs` | Documentation (HTML) | — |
| `GET` | `/api/stats` | Top queries by total time | `pg_stat_statements` |
| `GET` | `/api/table-health` | Table health + cache hit | `pg_stat_user_tables`, `pg_statio_user_tables` |
| `GET` | `/api/sizes` | Table and index sizes | `pg_stat_user_tables` |
| `GET` | `/api/indexes` | Index usage + duplicates | `pg_stat_user_indexes`, `pg_index` |
| `GET` | `/api/locks` | Blocking locks + active queries | `pg_locks`, `pg_stat_activity` |
| `GET` | `/api/anomalies` | Background anomaly log entries | `logs/db_anomalies.jsonl` |
| `GET` | `/api/triggers` | Trigger list | `pg_trigger` |
| `GET` | `/api/extensions` | Installed extensions | `pg_extension` |
| `POST` | `/api/analyze` | Query execution plan (`EXPLAIN`) | — |

## `GET /api/stats`

Returns an array of query statistics:

```json
[
  {
    "queryid": 123456,
    "query": "SELECT ...",
    "calls": 1500,
    "mean_time": 12.345,
    "total_time": 18517.5,
    "rows": 45000
  }
]
```

## `GET /api/table-health`

Per-table metrics including `dead_ratio_pct`, `idx_ratio_pct`, `cache_hit_pct`, VACUUM/ANALYZE timestamps, and sizes.

## `GET /api/indexes`

```json
{
  "indexes": [
    {
      "schema": "public",
      "table": "student",
      "index": "idx_student_last_name",
      "scans": 4200,
      "size": "8192 kB",
      "size_bytes": 8388608,
      "is_duplicate": false
    }
  ],
  "duplicates": [
    {
      "table": "public.anomaly_test",
      "indexes": ["idx_dup1", "idx_dup2"],
      "sizes": ["2048 kB", "2048 kB"]
    }
  ]
}
```

## `GET /api/locks`

```json
{
  "locks": [
    {
      "blocked_pid": 102,
      "blocking_pid": 101,
      "wait_seconds": 5.2,
      "blocked_query": "UPDATE ...",
      "blocking_query": "UPDATE ..."
    }
  ],
  "active": [
    {
      "pid": 101,
      "duration_seconds": 45.0,
      "state": "active",
      "query": "SELECT ..."
    }
  ]
}
```

## `POST /api/analyze`

**Request:**

```json
{ "query": "SELECT * FROM student WHERE last_name = 'Kowalski'" }
```

Only **`SELECT`** queries are allowed. Parameterized queries (`$1`, `$2`, …) are supported via `PREPARE`.

**Response:**

```json
{
  "plan_json": [{ "Plan": { "...": "..." } }],
  "with_index": ["Seq Scan on student  ..."],
  "without_index": ["Seq Scan on student  ..."]
}
```

See [Query Plan Analysis](/docs/explain) for interpreting results.
