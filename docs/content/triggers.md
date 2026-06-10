# Triggers

**Menu:** Trgrs → Triggers  
**API:** `GET /api/triggers`  
**Source:** `pg_trigger`, `pg_proc`

## What this panel does

Lists all user-defined triggers: which table they fire on, enabled/disabled status, and full PL/pgSQL definition. Hidden triggers are a frequent cause of "slow writes nobody explained."

<div class="doc-mock">
<div class="doc-mock-header">Configured triggers</div>
<table class="data-table doc-table-compact">
<tr><th>Table</th><th>Trigger</th><th>Status</th></tr>
<tr><td>employee</td><td>employee_audit_trigger</td><td><span class="badge badge-ok">ENABLED</span></td></tr>
<tr><td>student</td><td>student_program_trigger</td><td><span class="badge badge-ok">ENABLED</span></td></tr>
<tr><td>legacy_table</td><td>old_sync_trigger</td><td><span class="badge badge-danger">DISABLED</span></td></tr>
</table>
</div>

## Demo triggers

The sample schema (`scrpts/triggers_and_idx.sql`) includes:

| Trigger | Table | Purpose |
|---------|-------|---------|
| `employee_audit_trigger` | `employee` | Logs INSERT/UPDATE/DELETE to `employee_audit` |
| `student_program_trigger` | `student` | Updates `program.student_count` on enrollments |

## What to watch for

- **ENABLED trigger + slow INSERT/UPDATE** — read the definition; nested queries and extra writes add latency
- **Audit triggers on hot tables** — necessary for compliance but costly at scale
- **DISABLED triggers** — may indicate incomplete migration or manual debugging

## Fix: write performance investigation

1. Note triggers on the slow table in this panel
2. Check [Index Usage](/docs/index-usage) — indexes + triggers compound write cost
3. Temporarily disable for isolated test (non-production only):
   ```sql
   ALTER TABLE employee DISABLE TRIGGER employee_audit_trigger;
   -- run benchmark
   ALTER TABLE employee ENABLE TRIGGER employee_audit_trigger;
   ```
4. Optimize trigger body — batch audit writes, use `WHEN` clauses, avoid full-table scans

## Fix: unexpected side effects

If row counts or related tables change "magically", check triggers here before assuming application bugs.
