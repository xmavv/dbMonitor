# Common Scenarios

Step-by-step flows linking dashboard panels, colors, and fixes. Start with the symptom that matches your situation.

---

## "The app is slow but nothing is blocked"

<div class="doc-scenario">
<div class="doc-scenario-step"><span class="doc-step-num">1</span><div><strong>Top Queries</strong> — sort mentally by Total (ms). Find queries with high total or high mean time.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">2</span><div><strong>Analyze</strong> — click Analyze on the worst SELECT. Red/yellow tree nodes = expensive operations.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">3</span><div><strong>Table Health</strong> — check tables from the query for <span class="badge badge-danger">red</span> dead % or cache hit badges.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">4</span><div><strong>Fix</strong> — add index, VACUUM/ANALYZE, or rewrite query. Re-check Top Queries after <code>pg_stat_statements_reset()</code> if needed.</div></div>
</div>

**Green light:** Top queries show low mean times, Table Health summary all green.

---

## "Users can't save — everything hangs"

<div class="doc-scenario">
<div class="doc-scenario-step"><span class="doc-step-num">1</span><div><strong>Lock Monitor</strong> immediately. Any red lock card = active blocking.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">2</span><div>Note <strong>blocking PID</strong> and query. Check for <code>idle in transaction</code> in Active Queries.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">3</span><div><strong>Fix now:</strong> <code>pg_cancel_backend(pid)</code> or fix app transaction handling.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">4</span><div><strong>Prevent:</strong> statement timeouts, shorter transactions, better indexes to reduce lock hold time.</div></div>
</div>

**Green light:** "No blocking locks currently detected."

---

## "Database disk usage exploded"

<div class="doc-scenario">
<div class="doc-scenario-step"><span class="doc-step-num">1</span><div><strong>DB Sizes</strong> — identify largest tables and index-heavy bars (purple &gt; cyan).</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">2</span><div><strong>Index Usage</strong> — drop <span class="badge badge-danger">Unused</span> and <span class="badge badge-warn">Duplicate</span> indexes.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">3</span><div><strong>Table Health</strong> — high dead % → VACUUM; may reclaim bloat.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">4</span><div>Re-check DB Sizes after maintenance.</div></div>
</div>

---

## "Writes to one table are unusually slow"

<div class="doc-scenario">
<div class="doc-scenario-step"><span class="doc-step-num">1</span><div><strong>Index Usage</strong> — count indexes on the table; many unused indexes hurt writes.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">2</span><div><strong>Triggers</strong> — ENABLED triggers firing extra INSERTs/UPDATEs?</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">3</span><div><strong>Lock Monitor</strong> — rule out concurrent lock contention on same table.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">4</span><div><strong>Fix</strong> — drop dead indexes, simplify triggers, batch writes.</div></div>
</div>

---

## "I want alerts before users notice"

<div class="doc-scenario">
<div class="doc-scenario-step"><span class="doc-step-num">1</span><div>Configure anomaly log env vars — see <a href="/docs/configuration">Configuration</a>.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">2</span><div>Lower <code>DBMONITOR_LOCK_WAIT_SECONDS</code> and <code>DBMONITOR_LONG_QUERY_SECONDS</code> for your SLA.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">3</span><div>Ship <code>logs/db_anomalies.jsonl</code> to your alerting stack — see <a href="/docs/anomaly-log">Anomaly Log</a>.</div></div>
<div class="doc-scenario-step"><span class="doc-step-num">4</span><div>Use dashboard for investigation when alert fires.</div></div>
</div>

---

## "I'm learning PostgreSQL performance"

Recommended exploration order:

1. [Getting Started](/docs/getting-started) + sample scripts
2. [Color Legend](/docs/color-legend) — learn to read badges
3. [Top Queries](/docs/top-queries) + [Explain](/docs/explain)
4. [Table Health](/docs/table-health) + [Index Usage](/docs/index-usage)
5. Run `python scripts/demo_table_health.py` and watch panels + log react

---

## Quick reference: red badge → action

| Panel | Red signal | First action |
|-------|------------|--------------|
| Table Health | Dead % | `VACUUM ANALYZE` |
| Table Health | Cache hit | Index tuning / memory |
| Index Usage | Unused | Verify, then `DROP INDEX` |
| Lock Monitor | Lock card | Cancel blocking session |
| Summary cards | Bloated count &gt; 0 | Find table in list, vacuum |

Yellow = investigate before it becomes red. Green = healthy at current thresholds.
