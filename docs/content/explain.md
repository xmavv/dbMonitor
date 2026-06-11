# Query Plan Analysis (EXPLAIN)

Available from **Top Queries** → **Analyze** button on any `SELECT` statement.  
**API:** `POST /api/analyze`

<div class="doc-callout doc-callout-info">
<strong>Live demo</strong><br>
<b>Run:</b> <code>python scripts/demo_top_queries.py --fresh</code>, then click <b>Analyze</b> on the slow <code>demo.student</code> query<br>
<b>Dashboard:</b> Top Queries → Analyze → Tree / With Indexes / Without Indexes<br>
<b>Look for:</b> red/yellow tree nodes (high cost); Seq Scan in Tree; cost drop With vs Without Indexes<br>
<b>Docs search:</b> <code>explain</code>, <code>analyze</code>, <code>sequential scan</code>, <code>index</code>
</div>

## What this feature does

Runs `EXPLAIN` on your query and presents three views:

| Tab | Purpose |
|-----|---------|
| **Tree View** | Interactive JSON plan tree with cost highlighting |
| **With Indexes** | Text plan — normal planner behavior |
| **Without Indexes** | Text plan with index scans disabled — shows baseline cost |

<div class="doc-callout doc-callout-info">
Only <strong>SELECT</strong> queries are accepted — prevents accidental data modification.
</div>

## Tree node colors

<div class="doc-mock">
<div class="doc-mock-header">Plan tree nodes</div>
<div class="tree-node"><span class="tree-node-header"><span class="node-type scan">Seq Scan</span> <span class="node-cost">cost=0..450</span></span></div>
<div class="tree-node"><span class="tree-node-header warn"><span class="node-type">Index Scan</span> <span class="node-cost">cost=12..2400</span></span></div>
<div class="tree-node"><span class="tree-node-header critical"><span class="node-type join">Hash Join</span> <span class="node-cost">cost=500..42000</span></span></div>
</div>

| Border | Planner total cost |
|--------|-------------------|
| Default | ≤ 1000 |
| Yellow | &gt; 1000 |
| Red | &gt; 10000 |

Node type colors: **scan** (green tint), **join** (purple), **sort** (orange).

## How to interpret plans

### Sequential scan on a large table

```
Seq Scan on student  (cost=0.00..18234 rows=500000)
```

Often means missing index on `WHERE`/`JOIN` columns. Compare **Without Indexes** — if both look similar, an existing index isn't being used (stats stale or wrong data types).

### Index scan

```
Index Scan using idx_student_last_name on student
```

Good sign when filtering small fraction of rows.

### Nested Loop + high row estimate

May indicate missing join index or bad statistics — run `ANALYZE`.

## Workflow: should I add an index?

1. Open **Analyze** on slow SELECT from [Top Queries](/docs/top-queries)
2. Note expensive nodes (red/yellow in tree)
3. Switch to **Without Indexes** — if much worse, indexes matter here
4. Add candidate index, run `ANALYZE`, re-analyze query
5. Confirm **With Indexes** cost dropped

## Parameterized queries

Queries with `$1`, `$2` are prepared with dummy values based on parameter types (see `db.py` `TYPE_DEFAULTS`). Plans may differ slightly from production values — substitute realistic literals when possible.

## Example index creation

After seeing seq scan on `last_name`:

```sql
CREATE INDEX CONCURRENTLY idx_student_last_name ON student (last_name);
ANALYZE student;
```

Re-run **Analyze** to verify index usage.
