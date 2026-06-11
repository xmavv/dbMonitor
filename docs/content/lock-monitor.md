# Lock Monitor

**Menu:** Runtime → Lock Monitor  
**API:** `GET /api/locks`  
**Source:** `pg_locks`, `pg_stat_activity`

<div class="doc-callout doc-callout-info">
<strong>Live demo</strong><br>
<b>Run:</b> <code>python scripts/demo_locks.py --duration 45</code><br>
<b>Dashboard:</b> Lock Monitor → ↺ Refresh <em>while the script is running</em><br>
<b>Look for:</b> red lock cards (blocker → blocked), growing <b>Wait time</b>; yellow duration in Active Queries<br>
<b>Docs search:</b> <code>lock</code>, <code>blocked</code>, <code>idle in transaction</code>, <code>pg_cancel_backend</code>
</div>

## What this panel does

Surfaces **blocking lock chains** (who blocks whom) and **long-running active queries**. This is the first panel to open when users report freezes, timeouts, or "database hung."

<div class="doc-mock">
<div class="doc-mock-header">Blocking Locks (1)</div>
<div class="lock-item doc-lock-demo">
<div style="font-size:11px;color:var(--text3);margin-bottom:8px">Wait time: <span class="doc-color-warn">8.4s</span> | Lock: transactionid</div>
<div class="doc-lock-flow">
<div class="lock-pid"><span class="pid-num">PID 8421</span> <span class="pid-user">app_user</span></div>
<div class="lock-arrow-line"></div>
<div class="lock-pid doc-lock-blocked"><span class="pid-num">PID 8422</span> <span class="pid-user">app_user</span></div>
</div>
</div>
</div>

When healthy:

<div class="doc-callout doc-callout-ok">
<span class="doc-color-ok">✓ No blocking locks currently detected.</span>
</div>

## Blocking locks section

Each card shows:

| Field | Meaning |
|-------|---------|
| **Blocking PID** (left) | Session holding the lock |
| **Blocked PID** (right, red border) | Session waiting |
| **Wait time** | Seconds blocked — grows until resolved |
| **Lock type** | e.g. `relation`, `transactionid`, `row` |
| **Query text** | Last known statement for each session |

## Active queries section

Lists queries exceeding duration threshold with:

- **State / wait event** — e.g. `active`, `ClientRead`, `Lock`
- **Duration** — highlighted in <span class="doc-color-warn">yellow/warn</span> color

## What to watch for

| Signal | Severity | Action |
|--------|----------|--------|
| Any blocking lock | High | Identify blocker query immediately |
| Wait time &gt; few seconds | Critical | Users likely timing out |
| `idle in transaction` blocker | Common root cause | App left transaction open |
| Long SELECT in active list | Medium | May need index or cancel |

## Fix: resolve a blocking lock

**Step 1 — Identify the blocker**

Note the **blocking PID** and query text from the card.

**Step 2 — Inspect session**

```sql
SELECT pid, usename, state, query, xact_start, query_start
FROM pg_stat_activity WHERE pid = 8421;
```

**Step 3 — Resolve**

- If safe: `SELECT pg_cancel_backend(8421);` — cancels current statement
- Last resort: `SELECT pg_terminate_backend(8421);` — kills connection
- Fix app code: commit/rollback promptly, avoid long transactions

**Step 4 — Prevent recurrence**

- Shorten transactions holding row locks
- Use `LOCK TIMEOUT` or statement timeout
- Add missing indexes to shorten lock duration

## Test with simulator

```bash
python scripts/demo_locks.py --duration 45
```

Refresh Lock Monitor to see simulated blocking chains.
