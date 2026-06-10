# Table Health

**Menu:** Storage → Table Health  
**API:** `GET /api/table-health`  
**Source:** `pg_stat_user_tables`, `pg_statio_user_tables`

## What this panel does

Shows the **health snapshot** of every user table: tuple bloat, scan patterns, write activity, maintenance history, and buffer cache effectiveness per table.

## Summary metrics

<div class="doc-mock">
<div class="metrics-grid doc-metrics">
<div class="metric-card"><div class="metric-label">Avg Cache Hit</div><div class="metric-value doc-color-ok">96.8%</div><div class="metric-sub">Across tables with data</div></div>
<div class="metric-card"><div class="metric-label">Bloated Tables</div><div class="metric-value doc-color-ok">0</div><div class="metric-sub">dead ratio &gt; 10%</div></div>
<div class="metric-card"><div class="metric-label">Seq Scan Heavy</div><div class="metric-value doc-color-ok">0</div><div class="metric-sub">seq &gt; 100, idx ratio &lt; 50%</div></div>
</div>
</div>

## Column guide

| Column | Healthy signal | Warning signal |
|--------|----------------|----------------|
| **Live / Dead** | Low dead count vs live | Dead approaching or exceeding live |
| **Dead %** | <span class="badge badge-ok">≤ 5%</span> green | <span class="badge badge-danger">&gt; 20%</span> red — bloat |
| **Scans** | High idx ratio badge | Many seq scans on large tables |
| **Cache Hit** | <span class="badge badge-ok">&gt; 95%</span> | <span class="badge badge-danger">&lt; 80%</span> — disk pressure |
| **Last Autovacuum** | Recent timestamp | Never, or very old on busy tables |

## Color meanings

See [Color Legend](/docs/color-legend) for exact thresholds. Key rules:

- **Dead ratio** uses reversed scale — lower is better
- **Idx scan ratio** and **cache hit** — higher is better
- Summary **Bloated Tables** turns red when any table has dead ratio **&gt; 10%**

## Fix: high dead tuple ratio (red badge)

**Symptom:** <span class="badge badge-danger">35.2%</span> dead ratio on a busy table

**Steps:**

1. Confirm autovacuum is enabled: `SELECT reloptions FROM pg_class WHERE relname = 'your_table';`
2. Run manual vacuum if urgent:
   ```sql
   VACUUM (VERBOSE, ANALYZE) public.your_table;
   ```
3. For severe bloat, consider `VACUUM FULL` (locks table) or `pg_repack`
4. Refresh the panel — dead ratio should drop over time

## Fix: seq scan heavy (yellow summary count)

**Symptom:** Large table, seq scans dominate, idx ratio badge yellow/red

**Steps:**

1. Identify queries via [Top Queries](/docs/top-queries)
2. Run **Analyze** — look for `Seq Scan` on large row estimates
3. Add a targeted index on filter/join columns
4. Run `ANALYZE your_table;` so the planner picks the new index

## Fix: low cache hit (red badge)

**Symptom:** <span class="badge badge-danger">68.0%</span> cache hit with significant read volume

**Steps:**

1. Check if table is larger than `shared_buffers` — some disk reads are normal
2. Reduce sequential scans (indexes)
3. Consider increasing `shared_buffers` (requires restart and tuning)
4. Verify hot queries aren't scanning unnecessary columns (`SELECT *`)

## Fix: stale statistics

**Symptom:** Odd plans despite indexes; old **Last Analyze** date

```sql
ANALYZE public.your_table;
-- or for entire schema:
ANALYZE;
```
