/* ============================================================
   GDC Directorate Dashboard — app.js
   All API calls, state management, rendering logic
   ============================================================ */

const API_BASE = 'http://127.0.0.1:8000';
let TOKEN = '';
let ALL_COLLEGES = [];
let CHARTS = {};
let AUTO_REFRESH_TIMER = null;

/* ─────────────────────────────────────────────
   AUTH
───────────────────────────────────────────── */
async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const errEl = document.getElementById('login-error');
  const btnText = document.getElementById('login-btn-text');
  const spinner = document.getElementById('login-spinner');

  errEl.classList.add('hidden');
  btnText.textContent = 'Signing in…';
  spinner.classList.remove('hidden');

  try {
    const resp = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Login failed');

    TOKEN = data.access_token;
    sessionStorage.setItem('gdc_token', TOKEN);
    sessionStorage.setItem('gdc_user', JSON.stringify(data.user));

    document.getElementById('sidebar-user-name').textContent = data.user.name;

    showPage('dashboard');
    startClock();
    refreshAll();
    startAutoRefresh();

  } catch (e) {
    errEl.textContent = '⚠️ ' + e.message;
    errEl.classList.remove('hidden');
  } finally {
    btnText.textContent = 'Sign In to Dashboard';
    spinner.classList.add('hidden');
  }
}

function doLogout() {
  TOKEN = '';
  sessionStorage.clear();
  stopAutoRefresh();
  showPage('login');
}

/* ─────────────────────────────────────────────
   PAGE & VIEW ROUTING
───────────────────────────────────────────── */
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(name + '-page').classList.add('active');
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    if (item.getAttribute('onclick')?.includes(name)) item.classList.add('active');
  });

  const titles = {
    overview: 'Network Overview', colleges: 'College Status',
    alerts: 'Active Alerts', transfers: 'Book Transfers', reports: 'Reports'
  };
  document.getElementById('view-title').textContent = titles[name] || name;

  if (name === 'alerts') loadAlerts();
  if (name === 'transfers') loadTransfers();
  if (name === 'reports') loadReportPreview();
}

/* ─────────────────────────────────────────────
   API HELPERS
───────────────────────────────────────────── */
async function api(endpoint, opts = {}) {
  const resp = await fetch(API_BASE + endpoint, {
    headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json', ...opts.headers },
    ...opts
  });
  if (!resp.ok) {
    if (resp.status === 401) { doLogout(); return null; }
    return null;
  }
  return resp.json();
}

/* ─────────────────────────────────────────────
   MAIN DATA LOADING
───────────────────────────────────────────── */
async function refreshAll() {
  setSyncBadge('syncing');
  try {
    const [agg, colleges, alerts] = await Promise.all([
      api('/api/aggregate'),
      api('/api/colleges'),
      api('/api/alerts')
    ]);

    if (agg)      renderAggregate(agg);
    if (colleges) { ALL_COLLEGES = colleges; renderCollegesTable(colleges); renderCollegeGrid(colleges); }
    if (alerts)   renderAlertBadge(alerts);

    const comparison = await api('/api/comparison');
    if (comparison) renderCharts(comparison);

    setSyncBadge('live');
  } catch {
    setSyncBadge('offline');
  }
}

/* ─────────────────────────────────────────────
   RENDER FUNCTIONS
───────────────────────────────────────────── */
function renderAggregate(agg) {
  setText('kpi-total-books',   fmtNum(agg.total_books));
  setText('kpi-available-books', `${fmtNum(agg.available_books)} Available`);
  setText('kpi-total-members', fmtNum(agg.total_members));
  setText('kpi-issued-books',  `${fmtNum(agg.issued_books)} Books Issued`);
  setText('kpi-overdue-count', fmtNum(agg.overdue_count));
  setText('kpi-fines',         `Rs. ${fmtNum(agg.total_fines)} Fines`);
  setText('kpi-college-count', agg.college_count);
}

function renderAlertBadge(alerts) {
  const badge = document.getElementById('alert-badge');
  if (alerts.length > 0) {
    badge.textContent = alerts.length;
    badge.classList.add('show');
    setText('kpi-alert-count', `${alerts.length} Active Alert${alerts.length > 1 ? 's' : ''}`);
  } else {
    badge.classList.remove('show');
    setText('kpi-alert-count', '0 Active Alerts');
  }
}

function renderCollegesTable(colleges) {
  const tbody = document.getElementById('overview-college-tbody');
  tbody.innerHTML = '';
  colleges.forEach(col => {
    const lastSync = col.last_sync_at
      ? timeAgo(col.last_sync_at)
      : '<span class="badge badge-red">Never</span>';
    const alertBadge = col.alert_count > 0
      ? `<span class="badge badge-red">⚠ ${col.alert_count}</span>`
      : `<span class="badge badge-green">✓ Clear</span>`;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${col.name}</strong></td>
      <td style="color: var(--text-muted)">${col.location || '—'}</td>
      <td>${fmtNum(col.total_books || 0)}</td>
      <td>${fmtNum(col.total_members || 0)}</td>
      <td>${lastSync}</td>
      <td>${alertBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCollegeGrid(colleges) {
  const grid = document.getElementById('college-grid');
  grid.innerHTML = '';
  colleges.forEach(col => {
    const isOnline = col.last_sync_at && (Date.now() - col.last_sync_at < 7 * 24 * 3600 * 1000);
    const syncClass = isOnline ? 'sync-green' : 'sync-red';
    const syncText = isOnline ? '● Online' : '● Offline';
    const card = document.createElement('div');
    card.className = 'college-card';
    card.innerHTML = `
      <div class="college-card-title">🏫 ${col.name}</div>
      <div class="college-card-loc">📍 ${col.location || 'Unknown'}</div>
      <div class="college-card-stats">
        <div class="college-stat">
          <div class="college-stat-val">${fmtNum(col.total_books || 0)}</div>
          <div class="college-stat-lbl">Books</div>
        </div>
        <div class="college-stat">
          <div class="college-stat-val">${fmtNum(col.total_members || 0)}</div>
          <div class="college-stat-lbl">Members</div>
        </div>
      </div>
      <div class="college-sync-indicator">
        <span class="${syncClass}">${syncText}</span>
        <span style="color: var(--text-muted); margin-left: 4px">· Last sync: ${col.last_sync_at ? timeAgo(col.last_sync_at) : 'Never'}</span>
        ${col.alert_count > 0 ? `<span class="badge badge-red" style="margin-left:auto">⚠ ${col.alert_count} Alert${col.alert_count > 1 ? 's' : ''}</span>` : ''}
      </div>
    `;
    card.addEventListener('click', () => showCollegeModal(col.id));
    grid.appendChild(card);
  });
}

function filterColleges() {
  const q = document.getElementById('college-search').value.toLowerCase();
  renderCollegeGrid(ALL_COLLEGES.filter(c =>
    c.name.toLowerCase().includes(q) || (c.location || '').toLowerCase().includes(q)
  ));
}

function renderCharts(comparison) {
  const names = comparison.map(c => c.name);
  const books = comparison.map(c => c.total_books || 0);
  const overduePct = comparison.map(c => {
    // We don't have issued in comparison endpoint; use overdue raw count for now
    return c.overdue_count || 0;
  });

  // Destroy old charts
  if (CHARTS.comparison) CHARTS.comparison.destroy();
  if (CHARTS.overdue) CHARTS.overdue.destroy();

  const chartDefaults = {
    font: { family: 'Inter, system-ui', size: 11 },
    color: '#A0B0C8'
  };
  Chart.defaults.color = chartDefaults.color;
  Chart.defaults.font.family = chartDefaults.font.family;

  CHARTS.comparison = new Chart(document.getElementById('chart-comparison'), {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Total Books',
        data: books,
        backgroundColor: 'rgba(14,165,233,0.7)',
        borderColor: 'rgba(14,165,233,1)',
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(30,48,80,0.4)' }, ticks: { color: '#6B8CAE' } },
        y: { grid: { color: 'rgba(30,48,80,0.4)' }, ticks: { color: '#6B8CAE' } }
      }
    }
  });

  CHARTS.overdue = new Chart(document.getElementById('chart-overdue'), {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Overdue Books',
        data: overduePct,
        backgroundColor: 'rgba(245,158,11,0.7)',
        borderColor: 'rgba(245,158,11,1)',
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(30,48,80,0.4)' }, ticks: { color: '#6B8CAE' } },
        y: { grid: { color: 'rgba(30,48,80,0.4)' }, ticks: { color: '#6B8CAE' } }
      }
    }
  });
}

/* ─────────────────────────────────────────────
   ALERTS VIEW
───────────────────────────────────────────── */
async function loadAlerts() {
  const container = document.getElementById('alerts-list');
  container.innerHTML = '<div style="color:var(--text-muted);padding:20px">Loading alerts…</div>';
  const alerts = await api('/api/alerts');
  if (!alerts || alerts.length === 0) {
    container.innerHTML = `
      <div style="text-align:center;padding:48px;color:var(--text-muted)">
        <div style="font-size:48px;margin-bottom:16px">✅</div>
        <div style="font-size:16px;font-weight:600;color:var(--green)">All Clear</div>
        <div style="font-size:13px;margin-top:8px">No active alerts across the network.</div>
      </div>`;
    return;
  }
  container.innerHTML = '';
  alerts.forEach(alert => {
    const cls = alert.severity === 'critical' ? 'alert-critical' : 'alert-warning';
    const icon = alert.severity === 'critical' ? '🚨' : '⚠️';
    const div = document.createElement('div');
    div.className = `alert-item ${cls}`;
    div.id = `alert-${alert.id}`;
    div.innerHTML = `
      <div class="alert-icon">${icon}</div>
      <div class="alert-body">
        <div class="alert-college">🏫 ${alert.college_name}</div>
        <div class="alert-msg">${alert.message}</div>
        <div class="alert-time">${new Date(alert.created_at).toLocaleString()}</div>
      </div>
      <button class="alert-ack" onclick="ackAlert(${alert.id})">✓ Acknowledge</button>
    `;
    container.appendChild(div);
  });
}

async function ackAlert(alertId) {
  await api(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' });
  const el = document.getElementById(`alert-${alertId}`);
  if (el) { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }
  const alerts = await api('/api/alerts');
  if (alerts) renderAlertBadge(alerts);
}

/* ─────────────────────────────────────────────
   TRANSFERS VIEW
───────────────────────────────────────────── */
async function loadTransfers() {
  const tbody = document.getElementById('transfers-tbody');
  tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px">Loading…</td></tr>';
  const transfers = await api('/api/transfers');
  if (!transfers || transfers.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px">No transfers recorded.</td></tr>';
    return;
  }
  tbody.innerHTML = '';
  const statusBadge = { requested: 'badge-orange', 'in-transit': 'badge-blue', received: 'badge-green', rejected: 'badge-red' };
  transfers.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${t.book_title}</strong></td>
      <td style="color:var(--text-muted)">${t.book_isbn || '—'}</td>
      <td>${t.from_college_name || t.from_college}</td>
      <td>${t.to_college_name || t.to_college}</td>
      <td><span class="badge ${statusBadge[t.status] || 'badge-gold'}">${t.status.toUpperCase()}</span></td>
      <td style="color:var(--text-muted)">${new Date(t.requested_at).toLocaleDateString()}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ─────────────────────────────────────────────
   REPORTS VIEW
───────────────────────────────────────────── */
async function loadReportPreview() {
  const [agg, colleges] = await Promise.all([api('/api/aggregate'), api('/api/colleges')]);
  if (!agg || !colleges) return;

  const preview = document.getElementById('report-preview');
  const lines = [
    `GDC LIBRARY NETWORK — DIRECTORATE SUMMARY REPORT`,
    `Generated: ${new Date().toLocaleString()}`,
    `═══════════════════════════════════════════════`,
    ``,
    `NETWORK-WIDE STATISTICS`,
    `  Total Books     : ${fmtNum(agg.total_books)}`,
    `  Available Books : ${fmtNum(agg.available_books)}`,
    `  Issued Books    : ${fmtNum(agg.issued_books)}`,
    `  Total Members   : ${fmtNum(agg.total_members)}`,
    `  Overdue Books   : ${fmtNum(agg.overdue_count)}`,
    `  Fines Outstanding: Rs. ${fmtNum(agg.total_fines)}`,
    `  Colleges Online  : ${agg.college_count}`,
    ``,
    `PER-COLLEGE BREAKDOWN`,
    ...colleges.map(c =>
      `  ${c.name.padEnd(35)} Books: ${String(c.total_books || 0).padStart(5)}  Members: ${String(c.total_members || 0).padStart(4)}`
    ),
    ``,
    `═══════════════════════════════════════════════`,
    `KPK Directorate of Archives & Libraries — CONFIDENTIAL`
  ];
  preview.textContent = lines.join('\n');
}

async function exportReport(format) {
  const [agg, colleges] = await Promise.all([api('/api/aggregate'), api('/api/colleges')]);

  if (format === 'json') {
    const blob = new Blob([JSON.stringify({ aggregate: agg, colleges }, null, 2)], { type: 'application/json' });
    download(blob, `directorate_report_${datestamp()}.json`);
  } else if (format === 'excel') {
    // Simple CSV export since we don't have server-side xlsx in the browser
    const rows = [
      ['College', 'Location', 'Books', 'Members', 'Last Sync'],
      ...colleges.map(c => [c.name, c.location || '', c.total_books || 0, c.total_members || 0, c.last_sync_at ? new Date(c.last_sync_at).toLocaleString() : 'Never'])
    ];
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    download(blob, `directorate_report_${datestamp()}.csv`);
  } else if (format === 'pdf') {
    // Print the preview as a simple text window
    const preview = document.getElementById('report-preview').textContent;
    const w = window.open('', '_blank');
    w.document.write(`<pre style="font-family:monospace;padding:40px;font-size:13px;line-height:1.7">${preview}</pre>`);
    w.print();
  }
}

/* ─────────────────────────────────────────────
   COLLEGE DRILL-DOWN MODAL
───────────────────────────────────────────── */
async function showCollegeModal(collegeId) {
  const modal = document.getElementById('college-modal');
  const modalBody = document.getElementById('modal-body');
  const data = await api(`/api/colleges/${collegeId}/stats`);
  if (!data) return;

  const { college, snapshot } = data;
  document.getElementById('modal-college-name').textContent = `🏫 ${college.name}`;

  if (!snapshot) {
    modalBody.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:40px">No data received from this college yet.</div>';
  } else {
    const overduePct = snapshot.issued_books > 0
      ? ((snapshot.overdue_count / snapshot.issued_books) * 100).toFixed(1) : '0.0';
    modalBody.innerHTML = `
      <p style="color:var(--text-muted);margin-bottom:16px">📍 ${college.location || 'Unknown'} · Last Sync: ${timeAgo(college.last_sync_at)}</p>
      <div class="modal-stat-row">
        <div class="modal-stat">
          <div class="modal-stat-val">${fmtNum(snapshot.total_books)}</div>
          <div class="modal-stat-lbl">Total Books</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-val">${fmtNum(snapshot.total_members)}</div>
          <div class="modal-stat-lbl">Members</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-val">${fmtNum(snapshot.issued_books)}</div>
          <div class="modal-stat-lbl">Books Issued</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-val" style="color:var(--orange)">${fmtNum(snapshot.overdue_count)}</div>
          <div class="modal-stat-lbl">Overdue</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-val" style="color:var(--red)">${overduePct}%</div>
          <div class="modal-stat-lbl">Overdue Rate</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-val" style="color:var(--gold)">Rs.${fmtNum(snapshot.total_fines)}</div>
          <div class="modal-stat-lbl">Fines</div>
        </div>
      </div>
      ${snapshot.top_borrowed_books?.length ? `
        <h4 style="margin-bottom:12px;color:var(--text-secondary)">🔥 Top Borrowed Books</h4>
        <div style="display:flex;flex-direction:column;gap:8px">
          ${snapshot.top_borrowed_books.map((b, i) => `
            <div style="display:flex;justify-content:space-between;padding:8px 12px;background:rgba(30,48,80,0.4);border-radius:6px">
              <span>${i + 1}. ${b.title}</span>
              <span class="badge badge-blue">${b.count} times</span>
            </div>
          `).join('')}
        </div>
      ` : ''}
    `;
  }
  modal.classList.remove('hidden');
}

function closeModal() {
  document.getElementById('college-modal').classList.add('hidden');
}

/* ─────────────────────────────────────────────
   UTILS
───────────────────────────────────────────── */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function fmtNum(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString();
}

function timeAgo(tsMs) {
  if (!tsMs) return 'Never';
  const diff = Date.now() - tsMs;
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function datestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  a.click(); URL.revokeObjectURL(url);
}

function setSyncBadge(state) {
  const dot = document.querySelector('.sync-dot');
  const text = document.getElementById('sync-text');
  if (!dot) return;
  const states = {
    live:    { color: '#10B981', text: 'Live' },
    syncing: { color: '#F59E0B', text: 'Syncing…' },
    offline: { color: '#EF4444', text: 'Offline' }
  };
  const s = states[state] || states.live;
  dot.style.background = s.color;
  text.textContent = s.text;
}

function startClock() {
  const el = document.getElementById('time-display');
  const update = () => {
    if (el) el.textContent = new Date().toLocaleTimeString('en-PK');
  };
  update();
  setInterval(update, 1000);
}

function startAutoRefresh() {
  AUTO_REFRESH_TIMER = setInterval(refreshAll, 30000);
}

function stopAutoRefresh() {
  if (AUTO_REFRESH_TIMER) clearInterval(AUTO_REFRESH_TIMER);
}

/* ─────────────────────────────────────────────
   INIT — restore session if already logged in
───────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  const saved = sessionStorage.getItem('gdc_token');
  const user = sessionStorage.getItem('gdc_user');
  if (saved) {
    TOKEN = saved;
    if (user) {
      const u = JSON.parse(user);
      setText('sidebar-user-name', u.name);
    }
    showPage('dashboard');
    startClock();
    refreshAll();
    startAutoRefresh();
  }

  // Enter key on password field
  document.getElementById('login-password')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });

  // Close modal on overlay click
  document.getElementById('college-modal')?.addEventListener('click', e => {
    if (e.target.id === 'college-modal') closeModal();
  });
});
