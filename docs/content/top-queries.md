# Top Queries

**Menu:** Queries → Top Queries  
**API:** `GET /api/stats`  
**Source:** `pg_stat_statements`

## What this panel does

Ranks SQL statements by **total execution time** — the product of how often a query runs and how long each run takes. This is the best starting point when the database feels slow but you don't know which queries to blame.

<div class="doc-callout doc-callout-info">
<strong>Requires</strong> the <code>pg_stat_statements</code> extension loaded via <code>shared_preload_libraries</code>. Docker setup handles this automatically.
</div>

## Columns explained

| Column | Description |
|--------|-------------|
| **Query** | Normalized query text (parameters replaced with placeholders) |
| **Calls** | Number of executions since stats were reset |
| **Mean (ms)** | Average time per execution |
| **Total (ms)** | Cumulative time — primary sort key |
| **Rows** | Total rows returned |
| **Analyze** | Opens EXPLAIN plan (SELECT only) |

## What to watch for

<div class="doc-mock">
<div class="doc-mock-header">Example ranking</div>
<table class="data-table doc-table-compact">
<tr><th>#</th><th>Query</th><th>Calls</th><th>Mean</th><th>Total</th></tr>
<tr><td>1</td><td class="query-cell">SELECT * FROM enrollment WHERE …</td><td>45K</td><td>2.1 ms</td><td><strong>94,500 ms</strong></td></tr>
<tr><td>2</td><td class="query-cell">SELECT s.*, p.name FROM student s JOIN …</td><td>120</td><td><span class="doc-color-warn">850 ms</span></td><td>102,000 ms</td></tr>
</table>
</div>

- **High total time + high calls** — small per-call cost adds up; optimize or cache at app layer
- **High mean time** — each execution is slow; check plan, indexes, bloat
- **High rows** — may indicate missing `LIMIT` or inefficient filters

## Recommended actions

### 1. Analyze the plan

Click **Analyze** on any `SELECT` row. Compare [With Indexes vs Without Indexes](/docs/explain) to see whether an index helps.

### 2. Check related tables

Open [Table Health](/docs/table-health) for tables referenced in the query — look for red dead-ratio badges or low cache hit.

### 3. Reset stats (optional)

After fixing a query, reset `pg_stat_statements` to verify improvement:

```sql
SELECT pg_stat_statements_reset();
```

## Empty panel?

- Extension not loaded — restart Postgres with `shared_preload_libraries = 'pg_stat_statements'`
- No traffic yet — run some queries and refresh
- Stats reset recently — accumulate usage over time
