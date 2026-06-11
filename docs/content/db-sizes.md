# DB Sizes

**Menu:** Storage → DB Sizes  
**API:** `GET /api/sizes`  
**Source:** `pg_stat_user_tables` (size functions)

<div class="doc-callout doc-callout-info">
<strong>Live demo</strong><br>
<b>Run:</b> setup only — <code>demo_init.py</code> + <code>python scripts/demo_run_sql.py demo_db_sizes.sql</code><br>
<b>Dashboard:</b> DB Sizes → ↺ Refresh<br>
<b>Look for:</b> <code>demo.size_data</code> — purple (indexes) bar larger than cyan (data); large <code>demo.student</code><br>
<b>Docs search:</b> <code>DB sizes</code>, <code>index overhead</code>, <code>disk</code>
</div>

## What this panel does

Visualizes **disk footprint** per table: how much space is raw heap data vs indexes. Helps answer "why is my database so big?" and "are indexes eating more space than data?"

<div class="doc-mock">
<div class="doc-mock-header">Size bar example</div>
<div class="size-bar-row">
<div class="size-bar-label"><span class="size-bar-name">public.student</span><span class="size-bar-val">128 MB (Idx: 64 MB)</span></div>
<div class="size-bar-full"><div class="size-bar-data" style="width:66%"></div><div class="size-bar-idx" style="width:34%"></div></div>
</div>
<div class="size-bar-row">
<div class="size-bar-label"><span class="size-bar-name">public.enrollment</span><span class="size-bar-val">48 MB (Idx: <span class="doc-color-warn">52 MB</span>)</span></div>
<div class="size-bar-full"><div class="size-bar-data" style="width:48%"></div><div class="size-bar-idx" style="width:52%"></div></div>
</div>
</div>

**Cyan** segment = table data · **Purple** segment = indexes

## What to watch for

| Pattern | Possible issue |
|---------|----------------|
| One table dominates total size | Archiving, partitioning, or cleanup candidate |
| Index bar &gt; data bar | Too many or oversized indexes |
| Sudden growth | Bulk load, missing VACUUM, audit/log table |

The anomaly logger flags tables where **index overhead ≥ 50%** (`DBMONITOR_HIGH_INDEX_OVERHEAD_PCT`).

## Recommended actions

### Indexes larger than data

1. Open [Index Usage](/docs/index-usage) — find <span class="badge badge-danger">Unused</span> and <span class="badge badge-warn">Duplicate</span> indexes
2. Drop confirmed dead indexes:
   ```sql
   DROP INDEX CONCURRENTLY idx_name;
   ```
3. Re-check sizes after `VACUUM`

### Table unexpectedly large

1. Check [Table Health](/docs/table-health) for bloat (high dead %)
2. Inspect row counts: `SELECT count(*) FROM schema.table;`
3. Consider retention policy or partitioning for append-only tables

### Planning capacity

Export sizes periodically and track growth. Pair with `pg_database_size()` for total database footprint:

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```
