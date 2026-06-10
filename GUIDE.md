# PG Inspector — User Guide

This guide explains **how to use** PG Inspector in day-to-day database work. For installation, architecture, and API details see [`README.md`](README.md).

> **Full interactive documentation:** [http://localhost:5001/docs](http://localhost:5001/docs) — searchable, with color examples and step-by-step fixes.

---

## Table of contents

- [First steps](#first-steps)
- [Dashboard layout](#dashboard-layout)
- [Color legend (quick reference)](#color-legend-quick-reference)
- [Panels overview](#panels-overview)
- [Query plan analysis (EXPLAIN)](#query-plan-analysis-explain)
- [Anomaly log (background monitoring)](#anomaly-log-background-monitoring)
- [Common scenarios](#common-scenarios)
- [Tips & FAQ](#tips--faq)

---

## First steps

1. Start the stack (Docker recommended — see `README.md`):

   ```bash
   docker compose up
   ```

2. Open the dashboard: [http://localhost:5001](http://localhost:5001)

3. Open docs: [http://localhost:5001/docs](http://localhost:5001/docs)

4. Click **↺ Refresh** on any panel to load the latest data.

On first run the app enables `pg_stat_statements` and sets up a read-only monitoring user when privileges allow.

---

## Dashboard layout

- **Left sidebar** — switch between views
- **Green dot** (top right) — database connection is alive
- **Docs** link — opens the documentation site
- **↺ Refresh** — reloads the current view (panels do not auto-refresh)

---

## Color legend (quick reference)

PG Inspector uses **green → yellow → red** badges consistently. Full details: [/docs/color-legend](/docs/color-legend).

| Signal | Meaning | Typical action |
|--------|---------|----------------|
| <span style="color:#22c55e">Green</span> | Healthy at current thresholds | Monitor; no immediate action |
| <span style="color:#f59e0b">Yellow</span> | Worth investigating | Plan optimization before it worsens |
| <span style="color:#ef4444">Red</span> | Likely user-visible problem | Act soon — see panel-specific steps below |

**Percentage badges (normal — higher is better):** green ≥ 95%, yellow 80–95%, red < 80%  
**Dead tuple ratio (reversed — lower is better):** green ≤ 5%, yellow 5–20%, red > 20%

**Table Health summary cards:**
- **Avg Cache Hit** — red when ≤ 80%
- **Bloated Tables** — red when any table has dead ratio > 10%
- **Seq Scan Heavy** — yellow when tables have seq scans > 100 and idx ratio < 50%

**Index Usage:** red **Unused** (0 scans), yellow **Duplicate**

**Lock Monitor:** red lock cards = active blocking; green “No blocking locks” = healthy

---

## Panels overview

Each panel: **what it shows**, **what colors mean**, **what to do**.

### Top Queries

**Shows:** Most expensive queries from `pg_stat_statements` (calls, mean/total time, rows).

**Watch for:** High **total time** (frequent queries) or high **mean time** (slow individual runs).

**Red flags:** Queries dominating total time with high mean — click **Analyze** for EXPLAIN.

**Fix:** Optimize query, add indexes, reduce calls at app layer. See [/docs/top-queries](/docs/top-queries).

---

### Table Health

**Shows:** Live/dead tuples, scan ratios, INSERT/UPDATE/DELETE stats, VACUUM/ANALYZE dates, cache hit per table.

| Metric | Red means | Fix |
|--------|-----------|-----|
| Dead % badge | Bloat > 20% | `VACUUM ANALYZE schema.table` |
| Cache hit badge | < 80% hits | Indexes, memory tuning, reduce seq scans |
| Seq scan heavy (summary) | Large tables scanned without indexes | Add index, run ANALYZE |

See [/docs/table-health](/docs/table-health).

---

### DB Sizes

**Shows:** Table vs index disk usage with stacked bars (cyan = data, purple = indexes).

**Watch for:** Index bar larger than data bar — too many indexes.

**Fix:** Cross-check Index Usage, drop unused/duplicate indexes. See [/docs/db-sizes](/docs/db-sizes).

---

### Index Usage

**Shows:** Index scan counts; flags **Unused** (0 scans) and **Duplicate** indexes.

**Red Unused:** Index costs writes but never helps reads — drop after verification.

**Yellow Duplicate:** Keep one index, drop redundant copies.

**Fix:** `DROP INDEX CONCURRENTLY idx_name;` See [/docs/index-usage](/docs/index-usage).

---

### Lock Monitor

**Shows:** Blocking lock chains and long-running active queries.

**Red lock cards:** Session A blocks session B — classic “app frozen” cause.

**Fix steps:**
1. Note blocking PID and query text
2. `SELECT pg_cancel_backend(pid);` if safe
3. Fix long transactions / missing indexes in app

See [/docs/lock-monitor](/docs/lock-monitor).

---

### Triggers

**Shows:** All triggers with ENABLED/DISABLED status and full definition.

**Watch for:** Unexpected triggers on hot tables — extra work on every write.

**Fix:** Review trigger body, disable only for testing, optimize or batch audit logic. See [/docs/triggers](/docs/triggers).

---

### Extensions

**Shows:** Installed PostgreSQL extensions (informational).

**Watch for:** Missing `pg_stat_statements` when Top Queries is empty.

See [/docs/extensions](/docs/extensions).

---

## Query plan analysis (EXPLAIN)

From **Top Queries** → **Analyze** on any `SELECT`:

| Tab | Purpose |
|-----|---------|
| Tree View | Interactive plan; red/yellow nodes = high planner cost |
| With Indexes | Normal plan |
| Without Indexes | Baseline without index scans — compare impact |

Tree node colors: yellow cost > 1000, red cost > 10000.

See [/docs/explain](/docs/explain).

---

## Anomaly log (background monitoring)

PG Inspector continuously scans the database and writes events to `logs/db_anomalies.jsonl`.

**Detects:** blocked queries, long-running queries, dead tuples, low cache hit, duplicate/unused indexes, high index overhead.

**Tune via env vars:** `DBMONITOR_LOG_INTERVAL_SECONDS`, `DBMONITOR_LONG_QUERY_SECONDS`, `DBMONITOR_LOCK_WAIT_SECONDS`, `DBMONITOR_LOG_MIN_SEVERITY`, and others — see [/docs/configuration](/docs/configuration).

**Test:** `python scrpts/simulate_anomalies.py`

See [/docs/anomaly-log](/docs/anomaly-log).

---

## Common scenarios

| Symptom | Start here | Then |
|---------|------------|------|
| App slow, no obvious block | Top Queries | Analyze → Table Health |
| Users can't save / hangs | Lock Monitor | Cancel blocker, fix transactions |
| Disk too large | DB Sizes | Index Usage → drop dead indexes |
| Slow writes to one table | Index Usage + Triggers | Drop indexes, review triggers |
| Proactive alerts | Anomaly log config | Ship `db_anomalies.jsonl` to alerts |

Full walkthroughs: [/docs/scenarios](/docs/scenarios).

---

## Tips & FAQ

- **Can it break my database?** No data changes — reads stats only; EXPLAIN allows SELECT only.
- **Data doesn't auto-refresh** — click ↺ Refresh (except background anomaly log).
- **Empty panels** — normal on fresh DBs or when nothing is happening (e.g. no locks).
- **Test with synthetic load** — scripts in `scrpts/` (see `README.md`).
- **Technical details** — `README.md` and [/docs/api](/docs/api).
