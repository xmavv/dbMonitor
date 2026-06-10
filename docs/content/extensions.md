# Extensions

**Menu:** System → Extensions  
**API:** `GET /api/extensions`  
**Source:** `pg_extension`

## What this panel does

Shows PostgreSQL **extensions** installed in the current database — name, version, and schema. Informational panel for verifying monitoring prerequisites.

<div class="doc-mock">
<div class="doc-mock-header">Installed Extensions</div>
<table class="data-table doc-table-compact">
<tr><th>Name</th><th>Version</th><th>Schema</th></tr>
<tr><td style="color:var(--accent);font-weight:600">pg_stat_statements</td><td>1.10</td><td>public</td></tr>
<tr><td style="color:var(--accent);font-weight:600">plpgsql</td><td>1.0</td><td>pg_catalog</td></tr>
</table>
</div>

## Extensions PG Inspector relies on

| Extension | Required for | Notes |
|-----------|--------------|-------|
| **pg_stat_statements** | Top Queries | Must be in `shared_preload_libraries` + `CREATE EXTENSION` |
| **plpgsql** | Triggers in demo schema | Standard in most databases |

Setup creates `pg_stat_statements` automatically on first run when privileges allow.

## What to watch for

- **Missing pg_stat_statements** — Top Queries panel empty or errors
- **Version mismatch** after major PG upgrade — re-run `CREATE EXTENSION ... UPDATE`
- **Unexpected extensions** — review for security (e.g. `dblink`, custom FDWs)

## Fix: Top Queries empty

```sql
-- As superuser:
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- postgresql.conf (requires restart):
-- shared_preload_libraries = 'pg_stat_statements'
```

Restart PostgreSQL, then refresh the dashboard.

## Install additional extension

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Refresh Extensions panel to confirm.
