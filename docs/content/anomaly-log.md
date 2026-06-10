# Anomaly Log

PG Inspector runs a **background monitor** from app startup. It periodically scans the database and appends structured events to a JSON Lines log file — no manual refresh required.

**Log file:** `logs/db_anomalies.jsonl` (configurable)

## What gets detected

| Event type | Meaning | Default severity |
|------------|---------|------------------|
| `blocked_query` | Session waiting on a lock beyond threshold | warning / critical |
| `long_running_query` | Active query exceeds duration | warning / critical |
| `dead_tuples` | Table dead ratio above threshold | warning |
| `low_table_cache_hit` | Heap cache hit below threshold | warning |
| `low_index_cache_hit` | Index cache hit below threshold | warning |
| `duplicate_indexes` | Redundant indexes on same columns | warning |
| `unused_large_index` | Zero scans, size ≥ 10 MB | info |
| `high_index_overhead` | Index size ≥ 50% of table | info |
| `monitoring_error` | Logger itself failed | error |

## Sample log entry

```json
{
  "timestamp": "2026-06-11T14:32:01+00:00",
  "type": "dead_tuples",
  "severity": "warning",
  "message": "Table public.anomaly_test has 48.3% dead tuples",
  "details": {
    "schema": "public",
    "table": "anomaly_test",
    "dead_ratio_pct": 48.3,
    "dead_tuples": 100000
  }
}
```

## Configuration

All thresholds are environment variables — see [Configuration](/docs/configuration).

Common tuning:

```bash
# More aggressive lock detection
export DBMONITOR_LOCK_WAIT_SECONDS=1

# Log only errors and above
export DBMONITOR_LOG_MIN_SEVERITY=error

# Scan every 30 seconds
export DBMONITOR_LOG_INTERVAL_SECONDS=30
```

## How to use the log

### Manual review

```bash
tail -f logs/db_anomalies.jsonl | jq .
```

### Correlate with dashboard

| Log event | Dashboard panel |
|-----------|-----------------|
| `blocked_query` | [Lock Monitor](/docs/lock-monitor) |
| `dead_tuples` | [Table Health](/docs/table-health) |
| `duplicate_indexes` | [Index Usage](/docs/index-usage) |
| `long_running_query` | Lock Monitor → Active Queries |

### Generate test events

```bash
python scrpts/simulate_anomalies.py
# wait ~60s for next scan cycle
cat logs/db_anomalies.jsonl | tail -5
```

## Fix patterns by event type

**dead_tuples** → `VACUUM ANALYZE schema.table`  
**low_*_cache_hit** → indexes + memory tuning — see [Table Health](/docs/table-health)  
**duplicate_indexes / unused_large_index** → drop indexes — see [Index Usage](/docs/index-usage)  
**blocked_query** → cancel blocker — see [Lock Monitor](/docs/lock-monitor)

## Integration ideas

- Ship file to ELK / Loki / CloudWatch via agent
- Alert on `"severity": "critical"` with `jq` + cron
- Archive daily; dedupe uses fingerprint + `DBMONITOR_LOG_REPEAT_SECONDS`
