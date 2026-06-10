# Color Legend

PG Inspector uses a consistent **green → yellow → red** visual language across panels. This page maps every badge and highlight to its meaning so you can read the dashboard at a glance.

## Badge colors (percentage metrics)

The `badgeForPct()` helper drives most percentage badges:

| Color | Normal metrics (higher is better) | Reversed metrics (lower is better, e.g. dead tuple ratio) |
|-------|-----------------------------------|-------------------------------------------------------------|
| <span class="badge badge-ok">Green</span> | ≥ 95% | ≤ 5% |
| <span class="badge badge-warn">Yellow</span> | 80–95% | 5–20% |
| <span class="badge badge-danger">Red</span> | &lt; 80% | &gt; 20% |
| <span class="badge badge-info">N/A</span> | No data yet | No data yet |

<div class="doc-mock">
<div class="doc-mock-header">Example — cache hit badges</div>
<table class="data-table doc-table-compact">
<tr><th>Table</th><th>Cache Hit</th><th>Meaning</th></tr>
<tr><td>student</td><td><span class="badge badge-ok">97.2%</span></td><td>Healthy — most reads from RAM</td></tr>
<tr><td>enrollment</td><td><span class="badge badge-warn">84.1%</span></td><td>Watch — consider more memory or query tuning</td></tr>
<tr><td>employee_audit</td><td><span class="badge badge-danger">61.5%</span></td><td>Problem — frequent disk reads</td></tr>
</table>
</div>

<div class="doc-mock">
<div class="doc-mock-header">Example — dead tuple ratio (reversed scale)</div>
<table class="data-table doc-table-compact">
<tr><th>Table</th><th>Dead %</th><th>Meaning</th></tr>
<tr><td>course</td><td><span class="badge badge-ok">2.1%</span></td><td>Normal bloat level</td></tr>
<tr><td>employee</td><td><span class="badge badge-warn">12.8%</span></td><td>Elevated — plan VACUUM</td></tr>
<tr><td>anomaly_test</td><td><span class="badge badge-danger">48.3%</span></td><td>Heavy bloat — VACUUM urgently</td></tr>
</table>
</div>

## Table Health summary cards

Top-of-panel metrics use inline colors:

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| **Avg Cache Hit** | &gt; 95% | 80–95% | ≤ 80% |
| **Bloated Tables** (dead ratio &gt; 10%) | count = 0 | — | count &gt; 0 |
| **Seq Scan Heavy** (seq &gt; 100 and idx ratio &lt; 50%) | count = 0 | count &gt; 0 | — |

<div class="doc-mock">
<div class="metrics-grid doc-metrics">
<div class="metric-card"><div class="metric-label">Avg Cache Hit</div><div class="metric-value doc-color-danger">72.3%</div></div>
<div class="metric-card"><div class="metric-label">Bloated Tables</div><div class="metric-value doc-color-danger">3</div></div>
<div class="metric-card"><div class="metric-label">Seq Scan Heavy</div><div class="metric-value doc-color-warn">2</div></div>
</div>
</div>

## Index Usage status badges

| Badge | Meaning |
|-------|---------|
| <span class="badge badge-danger">Unused</span> | Index has **0 scans** — costs writes, gives no reads |
| <span class="badge badge-warn">Duplicate</span> | Multiple indexes cover the same columns |

## Lock Monitor

| Visual | Meaning |
|--------|---------|
| Green text *"No blocking locks"* | No lock chains detected |
| Red-bordered lock cards | Active blocking situation — investigate immediately |
| Yellow duration in Active Queries | Long-running query (shown in warn color) |

## EXPLAIN tree nodes

| Node border | Planner cost (relative) |
|-------------|-------------------------|
| Default | cost ≤ 1000 |
| Yellow border | cost &gt; 1000 |
| Red border | cost &gt; 10000 |

## Triggers

| Badge | Status |
|-------|--------|
| <span class="badge badge-ok">ENABLED</span> | Trigger is active |
| <span class="badge badge-danger">DISABLED</span> | Trigger exists but is off |
| <span class="badge badge-warn">other</span> | Unusual state — verify in catalog |

## When in doubt

1. **Red** — act soon; likely user-visible impact
2. **Yellow** — investigate when you have time; may become red under load
3. **Green** — healthy for current thresholds; still verify against your SLA

Thresholds for the background [Anomaly Log](/docs/anomaly-log) may differ slightly from UI badge cutoffs — see [Configuration](/docs/configuration).
