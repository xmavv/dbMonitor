let currentView = 'queries';
let planData = null;
let currentPlanTab = 'tree';
const loaded = {};

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
    event.currentTarget.classList.add('active');
    document.getElementById('page-title').textContent = {
        queries: 'Top Queries', tables: 'Table Health',
        sizes: 'Database Sizes', indexes: 'Index Usage', locks: 'Lock Monitor',
        triggers: 'Triggers', cache: 'Buffer Cache', extensions: 'Extensions'
    }[name];
    currentView = name;
    if (!loaded[name]) loadView(name);
}

function refreshCurrent() { loaded[currentView] = false; loadView(currentView); }

function loadView(name) {
    loaded[name] = true;
    const loaders = {
        queries: loadQueries, tables: loadTables,
        sizes: loadSizes, indexes: loadIndexes, locks: loadLocks,
        triggers: loadTriggers, cache: loadCache, extensions: loadExtensions
    };
    loaders[name]?.();
}

async function loadTriggers() {
    const container = document.getElementById('triggers-content');
    try {
        const res = await fetch('/api/triggers');
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<div class="empty-state">Błąd: ${data.error}</div>`;
            return;
        }

        if (!data.length) {
            container.innerHTML = `<div class="empty-state">No triggers defined in database.</div>`;
            return;
        }

        let html = `
      <div class="card">
        <div class="card-header">Configured triggers</div>
        <table class="data-table">
          <tr>
            <th>Schemat</th>
            <th>Tabela</th>
            <th>Nazwa Triggera</th>
            <th>Status</th>
            <th>Definicja (Kod)</th>
          </tr>`;

        data.forEach(t => {
            const statusClass = t.status === 'ENABLED' ? 'badge-ok' : (t.status === 'DISABLED' ? 'badge-danger' : 'badge-warn');
            html += `<tr>
        <td>${t.schema}</td>
        <td><strong>${t.table}</strong></td>
        <td>${t.trigger}</td>
        <td><span class="badge ${statusClass}">${t.status}</span></td>
        <td class="wrap" style="font-size: 11px;">${t.definition}</td>
      </tr>`;
        });

        html += `</table></div>`;
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div class="empty-state">Błąd połączenia z API.</div>`;
    }
}
window.addEventListener('load', () => loadView('queries'));

const $ = id => document.getElementById(id);
function fmt(n, dec=2) { return n == null ? '—' : Number(n).toFixed(dec); }
function fmtNum(n) { if (n == null) return '—'; if (n >= 1e6) return (n/1e6).toFixed(1)+'M'; if (n >= 1e3) return (n/1e3).toFixed(1)+'K'; return n; }

function badgeForPct(pct, reverse=false) {
    if (pct == null) return '<span class="badge badge-info">N/A</span>';
    const hi = reverse ? pct < 5 : pct > 95;
    const mid = reverse ? pct < 20 : pct > 80;
    const cls = hi ? 'badge-ok' : mid ? 'badge-warn' : 'badge-danger';
    return `<span class="badge ${cls}">${fmt(pct,1)}%</span>`;
}

function elapsed(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    const s = Math.floor((Date.now() - d) / 1000);
    if (s < 60) return s + 's ago';
    if (s < 3600) return Math.floor(s/60) + 'm ago';
    if (s < 86400) return Math.floor(s/3600) + 'h ago';
    return Math.floor(s/86400) + 'd ago';
}

async function loadQueries() {
    const el = $('queries-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    const maxTotal = Math.max(...data.map(r => r.total_time));

    let html = `<div class="card">
    <div class="card-header">Top Queries by Total Time</div>
    <div style="overflow-x: auto;">
    <table class="data-table">
    <thead><tr>
      <th>#</th><th>Query</th><th>Calls</th>
      <th>Mean (ms)</th><th>Total (ms)</th><th>Rows</th><th>Action</th>
    </tr></thead><tbody>`;

    data.forEach((r, i) => {
        const pct = (r.total_time / maxTotal * 100).toFixed(1);
        const isSelect = r.query.trim().toUpperCase().startsWith('SELECT');
        html += `<tr>
      <td style="color:var(--text3);font-family:var(--mono)">${i+1}</td>
      <td><div class="query-cell" title="${escHtml(r.query)}" onclick="showQueryFull('${escAttr(r.query)}')">${escHtml(r.query)}</div></td>
      <td style="font-family:var(--mono)">${fmtNum(r.calls)}</td>
      <td style="font-family:var(--mono)">${fmt(r.mean_time,2)}</td>
      <td style="font-family:var(--mono)">${fmt(r.total_time,0)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.rows)}</td>
      <td>${isSelect ? `<button class="btn" onclick="analyzePlan('${escAttr(r.query)}')">Analyze</button>` : ''}</td>
    </tr>`;
    });

    html += '</tbody></table></div></div>';
    el.innerHTML = html;
}

function showQueryFull(q) {
    alert(q);
}

async function analyzePlan(query) {
    planData = null;
    currentPlanTab = 'tree';
    $('plan-modal').classList.add('open');
    $('plan-content').innerHTML = '<div class="loader"><div class="spinner"></div>Running EXPLAIN…</div>';
    switchPlanTab('tree', true);

    const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query})
    });
    planData = await res.json();
    renderPlanTab(currentPlanTab);
}

function closePlan() { $('plan-modal').classList.remove('open'); }

function switchPlanTab(tab, noRender=false) {
    currentPlanTab = tab;
    document.querySelectorAll('.plan-tab').forEach((t,i) => {
        t.classList.toggle('active', ['tree','with','without'][i] === tab);
    });
    if (!noRender && planData) renderPlanTab(tab);
}

function renderPlanTab(tab) {
    const el = $('plan-content');
    if (!planData) return;
    if (planData.error) {
        el.innerHTML = `<pre style="color:var(--danger)">${escHtml(planData.error)}</pre>`; return;
    }
    if (tab === 'tree') {
        if (planData.plan_json) {
            const plan = planData.plan_json[0] || planData.plan_json;
            el.innerHTML = '';
            el.appendChild(renderTreeNode(plan['Plan'], 0));
        } else {
            el.innerHTML = '<pre class="plan-text">' + escHtml((planData.with_index||[]).join('\n')) + '</pre>';
        }
    } else if (tab === 'with') {
        el.innerHTML = '<pre class="plan-text">' + escHtml((planData.with_index||[]).join('\n')) + '</pre>';
    } else {
        const txt = planData.without_index_error
            ? planData.without_index_error
            : (planData.without_index||[]).join('\n');
        el.innerHTML = '<pre class="plan-text">' + escHtml(txt) + '</pre>';
    }
}

function renderTreeNode(node, depth) {
    if (!node) return document.createElement('div');
    const wrap = document.createElement('div');
    wrap.className = 'tree-node';

    const type = node['Node Type'] || '?';
    const startCost = node['Startup Cost'] || 0;
    const totalCost = node['Total Cost'] || 0;
    const planRows = node['Plan Rows'] || 0;
    const actualRows = node['Actual Rows'];
    const actualTime = node['Actual Total Time'];
    const relation = node['Relation Name'] ? ` on ${node['Relation Name']}` : '';
    const alias = node['Alias'] && node['Alias'] !== node['Relation Name'] ? ` (${node['Alias']})` : '';
    const indexName = node['Index Name'] ? ` [${node['Index Name']}]` : '';
    const filter = node['Filter'] || node['Join Filter'] || node['Hash Cond'] || node['Index Cond'] || '';

    let severity = '';
    if (totalCost > 10000) severity = 'critical';
    else if (totalCost > 1000) severity = 'warn';

    let typeClass = '';
    if (type.includes('Join') || type.includes('Loop')) typeClass = 'join';
    else if (type.includes('Scan')) typeClass = 'scan';
    else if (type.includes('Sort') || type.includes('Aggregate')) typeClass = 'sort';

    const rowDiff = actualRows != null ? Math.abs(actualRows - planRows) / (planRows || 1) : 0;

    const header = document.createElement('div');
    header.className = `tree-node-header ${severity}`;
    header.innerHTML = `
    <span class="node-type ${typeClass}">${type}${relation}${alias}${indexName}</span>
    <span class="node-cost">cost=${startCost.toFixed(2)}..${totalCost.toFixed(2)}</span>
    <span class="node-rows">${rowDiff > 2 ? '⚠ ' : ''}rows=${fmtNum(planRows)}${actualRows != null ? '→'+fmtNum(actualRows) : ''}</span>
    ${actualTime != null ? `<span class="node-time">${actualTime.toFixed(2)}ms</span>` : ''}
    ${filter ? `<span style="color:var(--text3);font-size:10px">${escHtml(filter.substring(0,60))}${filter.length>60?'…':''}</span>` : ''}
  `;
    wrap.appendChild(header);

    const plans = node['Plans'];
    if (plans && plans.length) {
        const childrenWrap = document.createElement('div');
        childrenWrap.className = 'tree-children';
        plans.forEach(child => childrenWrap.appendChild(renderTreeNode(child, depth+1)));
        wrap.appendChild(childrenWrap);
    }
    return wrap;
}

async function loadTables() {
    const el = $('tables-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/table-health');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    const avgCache = data.filter(r => r.cache_hit_pct != null);
    const avgCacheVal = avgCache.length ? (avgCache.reduce((s,r)=>s+r.cache_hit_pct,0)/avgCache.length).toFixed(1) : 'N/A';
    const bloatTables = data.filter(r => r.dead_ratio_pct > 10).length;
    const seqScanHeavy = data.filter(r => r.seq_scan > 100 && r.idx_ratio_pct < 50).length;

    let html = `<div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Tables</div>
      <div class="metric-value">${data.length}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg Cache Hit</div>
      <div class="metric-value" style="color:${avgCacheVal>95?'var(--success)':avgCacheVal>80?'var(--warn)':'var(--danger)'}">${avgCacheVal}%</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">High Bloat Tables</div>
      <div class="metric-value" style="color:${bloatTables>0?'var(--danger)':'var(--success)'}">${bloatTables}</div>
      <div class="metric-sub">&gt;10% dead tuples</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Seq Scan Heavy</div>
      <div class="metric-value" style="color:${seqScanHeavy>0?'var(--warn)':'var(--success)'}">${seqScanHeavy}</div>
      <div class="metric-sub">low index ratio</div>
    </div>
  </div>`;

    html += `<div class="card">
    <div class="card-header">Table Health Dashboard</div>
    <div style="overflow-x: auto;">
    <table class="data-table"><thead><tr>
      <th>Schema</th><th>Table</th><th>Size</th>
      <th>Live Tup</th><th>Dead Tup</th>
      <th>Ins</th><th>Upd</th><th>Del</th>
      <th>Seq/Idx Scans</th><th>Bloat %</th>
      <th>Cache Hit</th><th>Last Autovacuum</th>
    </tr></thead><tbody>`;

    data.forEach(r => {
        html += `<tr>
      <td>${r.schema}</td>
      <td style="font-weight:600;color:var(--accent)">${r.table}</td>
      <td style="font-family:var(--mono)">${r.total_size}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.live_tup)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.dead_tup)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.ins)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.upd)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.del)}</td>
      <td>Seq: ${fmtNum(r.seq_scan)} <br> Idx: ${fmtNum(r.idx_scan)} (${badgeForPct(r.idx_ratio_pct)})</td>
      <td>${badgeForPct(r.dead_ratio_pct, true)}</td>
      <td>${badgeForPct(r.cache_hit_pct)}</td>
      <td>${elapsed(r.last_autovacuum || r.last_vacuum)}</td>
    </tr>`;
    });

    html += '</tbody></table></div></div>';
    el.innerHTML = html;
}

async function loadSizes() {
    const el = $('sizes-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/sizes');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    let html = `<div class="card"><div class="card-header">Database Sizes</div><div class="card-body">`;
    data.forEach(r => {
        const tblPct = r.total_size_bytes ? (r.table_size_bytes / r.total_size_bytes) * 100 : 0;
        const idxPct = r.total_size_bytes ? (r.indexes_size_bytes / r.total_size_bytes) * 100 : 0;
        html += `
      <div class="size-bar-row">
        <div class="size-bar-label">
          <span class="size-bar-name">${r.schema}.${r.table}</span>
          <span class="size-bar-val">${r.total_size} (Idx: ${r.indexes_size})</span>
        </div>
        <div class="size-bar-full">
          <div class="size-bar-data" style="width:${tblPct}%" title="Table Data: ${r.table_size}"></div>
          <div class="size-bar-idx" style="width:${idxPct}%" title="Indexes: ${r.indexes_size}"></div>
        </div>
      </div>
    `;
    });
    html += `</div></div>`;
    el.innerHTML = html;
}

async function loadIndexes() {
    const el = $('indexes-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/indexes');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    let html = '';

    if (data.duplicates && data.duplicates.length > 0) {
        html += `<div class="card"><div class="card-header" style="color:var(--warn)">⚠ Duplicate Indexes Detected</div>
    <table class="data-table"><thead><tr><th>Table</th><th>Indexes</th><th>Sizes</th></tr></thead><tbody>`;
        data.duplicates.forEach(d => {
            html += `<tr>
        <td style="font-weight:600">${d.table}</td>
        <td>${d.indexes.join(', ')}</td>
        <td style="font-family:var(--mono)">${d.sizes.join(', ')}</td>
      </tr>`;
        });
        html += `</tbody></table></div>`;
    }

    html += `<div class="card"><div class="card-header">Index Usage & Statistics</div>
  <table class="data-table"><thead><tr>
    <th>Schema</th><th>Table</th><th>Index</th>
    <th>Size</th><th>Scans</th><th>Tup Read</th>
    <th>Tup Fetch</th><th>Status</th>
  </tr></thead><tbody>`;

    data.indexes.forEach(r => {
        const isUnused = r.scans === 0;
        const dupBadge = r.is_duplicate ? '<span class="badge badge-warn">Duplicate</span>' : '';
        const unusedBadge = isUnused ? '<span class="badge badge-danger">Unused</span>' : '';
        html += `<tr>
      <td>${r.schema}</td>
      <td style="font-weight:600">${r.table}</td>
      <td>${r.index}</td>
      <td style="font-family:var(--mono)">${r.size}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.scans)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.tup_read)}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.tup_fetch)}</td>
      <td>${dupBadge} ${unusedBadge}</td>
    </tr>`;
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;
}

async function loadLocks() {
    const el = $('locks-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/locks');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    let html = '';

    html += `<div class="card"><div class="card-header">Blocking Locks (${data.locks.length})</div><div class="card-body">`;
    if (data.locks.length === 0) {
        html += `<div style="color:var(--success)">No blocking locks currently detected.</div>`;
    } else {
        data.locks.forEach(l => {
            html += `<div class="lock-item">
        <div style="font-size:11px;color:var(--text3);margin-bottom:8px">Wait time: ${fmt(l.wait_seconds,1)}s | Lock: ${l.locktype} on ${l.relation||'N/A'}</div>
        <div style="display:flex;gap:16px;align-items:center;">
          <div style="flex:1">
            <div class="lock-pid"><span class="pid-num">PID ${l.blocking_pid}</span> <span class="pid-user">${l.blocking_user}</span></div>
            <div class="query-cell" style="margin-top:8px" title="${escAttr(l.blocking_query)}" onclick="showQueryFull('${escAttr(l.blocking_query)}')">${escHtml(l.blocking_query)}</div>
          </div>
          <div class="lock-arrow"><div class="lock-arrow-line"></div></div>
          <div style="flex:1">
            <div class="lock-pid" style="border-color:var(--danger)"><span class="pid-num">PID ${l.blocked_pid}</span> <span class="pid-user">${l.blocked_user}</span></div>
            <div class="query-cell" style="margin-top:8px" title="${escAttr(l.blocked_query)}" onclick="showQueryFull('${escAttr(l.blocked_query)}')">${escHtml(l.blocked_query)}</div>
          </div>
        </div>
      </div>`;
        });
    }
    html += `</div></div>`;

    html += `<div class="card"><div class="card-header">Active Queries</div>
  <table class="data-table"><thead><tr>
    <th>PID</th><th>User / App</th><th>State / Wait Event</th>
    <th>Duration</th><th>Query</th>
  </tr></thead><tbody>`;
    if (data.active.length === 0) {
        html += `<tr><td colspan="5" class="empty-state">No long running queries found.</td></tr>`;
    } else {
        data.active.forEach(q => {
            const wait = q.wait_event ? `${q.wait_event_type}: ${q.wait_event}` : '—';
            html += `<tr>
        <td style="font-family:var(--mono)">${q.pid}</td>
        <td>${q.user}<br><span style="font-size:10px;color:var(--text3)">${q.app}</span></td>
        <td>${q.state}<br><span style="font-size:10px;color:var(--text3)">${wait}</span></td>
        <td style="color:var(--warn);font-weight:600;font-family:var(--mono)">${fmt(q.duration_seconds,1)}s</td>
        <td><div class="query-cell" style="max-width:300px" title="${escAttr(q.query)}" onclick="showQueryFull('${escAttr(q.query)}')">${escHtml(q.query)}</div></td>
      </tr>`;
        });
    }
    html += '</tbody></table></div>';
    el.innerHTML = html;
}

async function loadCache() {
    const el = $('cache-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/cache');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    if (!data.length) {
        el.innerHTML = `<div class="empty-state">No relations currently in the buffer cache.</div>`;
        return;
    }

    const maxBuffers = Math.max(...data.map(r => r.buffers));

    let html = `<div class="card">
    <div class="card-header">Buffer Cache Usage (pg_buffercache)</div>
    <table class="data-table"><thead><tr>
      <th>Table</th><th>Buffers</th><th>Cached Size</th>
      <th>% of shared_buffers</th><th></th>
    </tr></thead><tbody>`;

    data.forEach(r => {
        const pct = (r.buffers / maxBuffers * 100).toFixed(1);
        html += `<tr>
      <td style="font-weight:600;color:var(--accent)">${r.table}</td>
      <td style="font-family:var(--mono)">${fmtNum(r.buffers)}</td>
      <td style="font-family:var(--mono)">${r.cached_size}</td>
      <td>${badgeForPct(r.pct_of_cache)}</td>
      <td style="width:160px"><div class="size-bar-full"><div class="size-bar-data" style="width:${pct}%"></div></div></td>
    </tr>`;
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;
}

async function loadExtensions() {
    const el = $('extensions-content');
    el.innerHTML = '<div class="loader"><div class="spinner"></div>Loading…</div>';
    const res = await fetch('/api/extensions');
    const data = await res.json();
    if (data.error) { el.innerHTML = `<pre style="color:var(--danger)">${data.error}</pre>`; return; }

    if (!data.length) {
        el.innerHTML = `<div class="empty-state">No extensions installed.</div>`;
        return;
    }

    let html = `<div class="card">
    <div class="card-header">Installed Extensions</div>
    <table class="data-table"><thead><tr>
      <th>Name</th><th>Version</th><th>Schema</th>
    </tr></thead><tbody>`;

    data.forEach(r => {
        html += `<tr>
      <td style="font-weight:600;color:var(--accent)">${escHtml(r.name)}</td>
      <td style="font-family:var(--mono)">${escHtml(r.version)}</td>
      <td style="font-family:var(--mono)">${escHtml(r.schema)}</td>
    </tr>`;
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;
}

function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
function escAttr(str) { return escHtml(str); }