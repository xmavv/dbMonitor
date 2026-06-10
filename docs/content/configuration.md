# Configuration

## Database connection

Connection is built from environment variables in `db.py`:

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `POSTGRES_USER` | — | yes | Database user |
| `POSTGRES_PASSWORD` | — | yes | Password |
| `POSTGRES_DB` | — | yes | Database name |
| `POSTGRES_HOST` | `localhost` | no | Server host |
| `POSTGRES_PORT` | `5432` | no | Server port |

Connection string format:

```
postgresql://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB>
```

You can also pass `--db-url` on the CLI when starting `app.py`.

If required variables are missing, the app shows **No DB URL provided**.

## Anomaly log (background monitoring)

PG Inspector continuously samples the database and appends detected issues to `logs/db_anomalies.jsonl`. Tune sensitivity with:

| Variable | Default | Description |
|----------|---------|-------------|
| `DBMONITOR_LOG_INTERVAL_SECONDS` | `60` | How often to scan the database |
| `DBMONITOR_LOG_REPEAT_SECONDS` | `300` | Minimum interval before logging the same issue again |
| `DBMONITOR_LOG_MIN_SEVERITY` | `warning` | Minimum level: `debug`, `info`, `warning`, `error`, `critical` |
| `DBMONITOR_ANOMALY_LOG_FILE` | `logs/db_anomalies.jsonl` | Output file path |
| `DBMONITOR_LONG_QUERY_SECONDS` | `30` | Active query duration threshold |
| `DBMONITOR_LOCK_WAIT_SECONDS` | `2` | Lock wait duration threshold |
| `DBMONITOR_DEAD_TUPLE_RATIO_PCT` | `20` | Dead tuple ratio alert threshold |
| `DBMONITOR_MIN_DEAD_TUPLES` | `100` | Minimum dead tuples before ratio alert |
| `DBMONITOR_LOW_CACHE_HIT_PCT` | `90` | Cache hit ratio alert threshold |
| `DBMONITOR_MIN_CACHE_READS` | `100` | Minimum block reads before cache alert |
| `DBMONITOR_UNUSED_INDEX_MIN_BYTES` | `10485760` (10 MB) | Minimum index size for unused-index alert |
| `DBMONITOR_HIGH_INDEX_OVERHEAD_PCT` | `50` | Index size vs table size overhead threshold |

See [Anomaly Log](/docs/anomaly-log) for event types and how to use the log file.

## Docker environment

In `docker-compose.yml`, set variables under the `db-inspector` service `environment` block. Postgres uses `shared_preload_libraries=pg_stat_statements` in the compose file for Top Queries support.
