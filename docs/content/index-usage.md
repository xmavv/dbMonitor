# Index Usage

**Menu:** Indexes → Index Usage  
**API:** `GET /api/indexes`  
**Source:** `pg_stat_user_indexes`, duplicate detection via `pg_index`

## What this panel does

Lists every index with scan counts and automatically highlights **unused** and **duplicate** indexes — common sources of wasted disk and slower writes.

<div class="doc-mock">
<div class="doc-mock-header">⚠ Duplicate Indexes Detected</div>
<table class="data-table doc-table-compact">
<tr><th>Table</th><th>Indexes</th><th>Sizes</th></tr>
<tr><td>public.anomaly_test</td><td>idx_dup1, idx_dup2</td><td>2048 kB, 2048 kB</td></tr>
</table>
</div>

## Status badges

| Badge | Condition | Impact |
|-------|-----------|--------|
| <span class="badge badge-danger">Unused</span> | `scans = 0` | Every INSERT/UPDATE/DELETE still maintains the index |
| <span class="badge badge-warn">Duplicate</span> | Same indexed columns | Redundant maintenance + storage |

<div class="doc-mock">
<div class="doc-mock-header">Index table excerpt</div>
<table class="data-table doc-table-compact">
<tr><th>Index</th><th>Scans</th><th>Size</th><th>Status</th></tr>
<tr><td>idx_student_last_name</td><td>12.4K</td><td>8192 kB</td><td></td></tr>
<tr><td>idx_student_gender_unused</td><td>0</td><td>4096 kB</td><td><span class="badge badge-danger">Unused</span></td></tr>
<tr><td>idx_dup2</td><td>0</td><td>2048 kB</td><td><span class="badge badge-warn">Duplicate</span></td></tr>
</table>
</div>

## What to watch for

- **Large + unused** — highest priority to drop (anomaly log uses 10 MB default threshold)
- **Duplicate groups** — keep the index with most scans; drop others after verification
- **Zero scans on new index** — normal briefly; wait for production traffic before dropping

## Fix: remove unused index

**Before dropping**, confirm the planner won't need it:

1. Check [Top Queries](/docs/top-queries) for filters on indexed columns
2. Run **Analyze** on representative SELECTs
3. Drop safely in production:

```sql
DROP INDEX CONCURRENTLY public.idx_student_gender_unused;
```

## Fix: resolve duplicates

1. Compare definitions: `\d+ table_name` in psql
2. Keep the index used by foreign keys or unique constraints
3. Drop redundant copy with `DROP INDEX CONCURRENTLY`

## Fix: slow writes on a table

If INSERT/UPDATE is slow:

1. Count indexes on the table in this panel
2. Cross-check [Triggers](/docs/triggers) for extra work per row
3. Remove indexes you don't need — each index adds write amplification

## Sample schema note

The demo database intentionally includes unused indexes (`idx_student_gender_unused`, `idx_phd_student_year_unused`) for training — see `scrpts/triggers_and_idx.sql`.
