// === Configuration ===
const CACHE_KEY = 'ctf_data_cache';

// Rows arrive from data-agent.js with both scoring modes precomputed by DuckDB:
//   rank_solve / pts_solve  = solve-order rank + rank-based points
//   rank_time  / pts_time   = time-based rank + time-based points
// pts_* already account for the hint malus; hints_used / hint_malus are
// carried through for the cell tooltip.
// This helper projects each row onto a uniform {rank, pts} shape for the
// active tab so the renderers don't need to know about modes.
function rowsForMode(mode, data) {
  const rankKey = mode === 'time' ? 'rank_time'  : 'rank_solve';
  const ptsKey  = mode === 'time' ? 'pts_time'   : 'pts_solve';
  return data.rows.map(r => ({ ...r, rank: r[rankKey], pts: r[ptsKey] }));
}

function fmtDuration(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(s / 60);
  return m ? `${m}m${String(s % 60).padStart(2, '0')}s` : `${s}s`;
}

function buildCellTooltip(data) {
  const lines = [];
  if (data.time_spent_ms != null) {
    lines.push(`<div class="cell-tip-line"><span class="cell-tip-label">Timer:</span> ${fmtDuration(data.time_spent_ms)}</div>`);
  }
  if (data.hints_detail?.length) {
    lines.push(`<div class="cell-tip-line"><span class="cell-tip-label">Hints:</span></div>`);
    const items = data.hints_detail.map(h => {
      const malusTxt = h.malus > 0 ? `−${h.malus} pts` : `gratuit`;
      return `<li><span class="cell-tip-hint-title">${escapeHtml(h.title)}</span><span class="cell-tip-hint-malus">${malusTxt}</span></li>`;
    }).join('');
    lines.push(`<ul class="cell-tip-hints">${items}</ul>`);
  }
  if (!lines.length) return '';
  return `<div class="cell-tip">${lines.join('')}</div>`;
}

// === DOM helpers ===
const status  = () => document.getElementById('status');
const thead   = () => document.querySelector('#leaderboard thead tr');
const tbody   = () => document.querySelector('#leaderboard tbody');
const updated = () => document.getElementById('updated');

function setStatus(msg) { const el = status(); if (el) el.textContent = msg; }

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// === Rendering ===

function computeScoreboard(rows) {
  const players = {};
  for (const r of rows) {
    const { pseudo, scenario, rank, pts, time_spent_ms, hints_used, hint_malus, hints_detail } = r;
    if (!players[pseudo]) players[pseudo] = { pseudo, totalScore: 0, scenarios: {} };
    players[pseudo].scenarios[scenario] = {
      rank, pts,
      time_spent_ms,
      hints_used,
      hint_malus,
      hints_detail: hints_detail ?? [],
    };
    players[pseudo].totalScore += pts;
  }
  return Object.values(players).sort(
    (a, b) => b.totalScore - a.totalScore || a.pseudo.localeCompare(b.pseudo)
  );
}

function renderPodium(scoreboard, rows, playerCount) {
  [1, 2, 3].forEach((place, i) => {
    const card = document.getElementById(`podium-${place}`);
    if (!card) return;
    const player = scoreboard[i];
    card.querySelector('.p-name').textContent  = player?.pseudo ?? '—';
    card.querySelector('.p-score').textContent = player ? `${player.totalScore} pts` : '0 pts';
  });
  const statPlayers = document.getElementById('stat-players');
  const statSolved  = document.getElementById('stat-solved');
  if (statPlayers) statPlayers.textContent = playerCount || scoreboard.length;
  if (statSolved)  statSolved.textContent  = rows.length;
}

function renderScoreboard(scoreboard, scenarios) {
  thead().innerHTML =
    `<th>Rang</th><th>Joueur</th><th>Score</th>` +
    scenarios.map(s => `<th>Scénario ${s}</th>`).join('');
  tbody().innerHTML = '';

  if (scoreboard.length === 0) {
    const cols = 3 + scenarios.length;
    tbody().innerHTML = `<tr><td colspan="${cols}" style="color:#64748b;padding:2rem">Aucun résultat pour l’instant — soyez le premier !</td></tr>`;
    return;
  }

  scoreboard.forEach((player, index) => {
    const tr = document.createElement('tr');
    const rankClass = index < 3 ? ` class="rank-${index + 1}"` : '';
    let cells = `<td${rankClass}>#${index + 1}</td>`;
    cells += `<td>${escapeHtml(player.pseudo)}</td>`;
    cells += `<td class="score">${player.totalScore}</td>`;
    for (const s of scenarios) {
      const data = player.scenarios[s];
      if (!data) {
        cells += `<td class="unsolved">—</td>`;
        continue;
      }
      cells += `<td class="solved">#${data.rank} (${data.pts}pts)${buildCellTooltip(data)}</td>`;
    }
    tr.innerHTML = cells;
    tbody().appendChild(tr);
  });
}

function renderFeed(events) {
  const list = document.getElementById('feed-list');
  if (!list) return;
  if (!events?.length) {
    list.innerHTML = `<div class="feed-empty">Aucune activité pour l'instant.</div>`;
    return;
  }
  list.innerHTML = events.map(ev => {
    const isSuccess      = ev.action === 'FLAG_SUBMISSION_SUCCESS';
    const isHint         = ev.action === 'HINT_EXPANDED';
    const isRegistration = ev.action === 'REGISTRATION';
    const time = ev.timestamp
      ? new Date(ev.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : '';
    let tag, detail, itemClass;
    if (isRegistration) {
      tag = `<span class="feed-tag feed-tag-register">REGISTER</span>`;
      detail = `<span class="feed-pseudo">${escapeHtml(ev.pseudo ?? '?')}</span> a rejoint la partie`;
      itemClass = 'feed-item-register';
    } else if (isHint) {
      tag = `<span class="feed-tag feed-tag-hint">HINT</span>`;
      detail = `<span class="feed-pseudo">${escapeHtml(ev.pseudo ?? '?')}</span> — Scénario <strong>${escapeHtml(ev.scenario ?? '?')}</strong>${ev.hint_title ? `<div class="feed-reason">${escapeHtml(ev.hint_title)}</div>` : ''}`;
      itemClass = 'feed-item-hint';
    } else if (isSuccess) {
      tag = `<span class="feed-tag feed-tag-success">SUCCESS</span>`;
      detail = `<span class="feed-pseudo">${escapeHtml(ev.pseudo ?? '?')}</span> — Scénario <strong>${escapeHtml(ev.scenario ?? '?')}</strong>`;
      itemClass = 'feed-item-success';
    } else {
      tag = `<span class="feed-tag feed-tag-rejected">REJECTED</span>`;
      detail = `<span class="feed-pseudo">${escapeHtml(ev.pseudo ?? '?')}</span> — Scénario <strong>${escapeHtml(ev.scenario ?? '?')}</strong>${ev.reason ? `<div class="feed-reason">${escapeHtml(ev.reason)}</div>` : ''}`;
      itemClass = 'feed-item-rejected';
    }
    return `<div class="feed-item ${itemClass}">
      <div class="feed-item-top">${tag}<span class="feed-time">${time}</span></div>
      <div class="feed-detail">${detail}</div>
    </div>`;
  }).join('');
}

// === Chart ===

const PLAYER_COLORS = [
  '#5b9cf6', '#3fb950', '#f0c000', '#f0883e',
  '#bc8cff', '#ff6b6b', '#56d364', '#ffa657',
  '#79c0ff', '#ffb3c6', '#aff5b4', '#ffd700',
];

function computeTimeSeries(rows) {
  const events = {};
  for (const { pseudo, rank, scenario, solved_at, pts } of rows) {
    if (!events[pseudo]) events[pseudo] = [];
    events[pseudo].push({ t: new Date(solved_at), pts, rank, scenario });
  }
  const series = {};
  for (const [pseudo, pts] of Object.entries(events)) {
    pts.sort((a, b) => a.t - b.t);
    let cumul = 0;
    series[pseudo] = pts.map(({ t, pts, rank, scenario }) => ({
      x: t, y: (cumul += pts), rank, scenario, pts,
    }));
  }
  return series;
}

function renderChart(rows) {
  const series  = computeTimeSeries(rows);
  const pseudos = Object.keys(series);

  const datasets = pseudos.map((pseudo, i) => {
    const color = PLAYER_COLORS[i % PLAYER_COLORS.length];
    return {
      label: pseudo, data: series[pseudo],
      borderColor: color, backgroundColor: color + '22',
      tension: 0.3, stepped: 'before', pointRadius: 5, pointHoverRadius: 7,
    };
  });

  const ctx = document.getElementById('progress-chart').getContext('2d');
  const existing = window.Chart.getChart('progress-chart');
  if (existing) existing.destroy();

  const highlightPlugin = {
    id: 'highlightOnHover',
    afterEvent(chart, { event }) {
      if (!['mousemove', 'mouseout'].includes(event.type)) return;
      const points = chart.getElementsAtEventForMode(event.native, 'nearest', { intersect: true }, true);
      const hovered = points.length ? points[0].datasetIndex : -1;
      let changed = false;
      chart.data.datasets.forEach((ds, i) => {
        const isHov   = i === hovered;
        const newW    = isHov ? 3 : hovered === -1 ? 2 : 1;
        const newA    = isHov ? 1 : hovered === -1 ? 1 : 0.25;
        const base    = PLAYER_COLORS[i % PLAYER_COLORS.length];
        const newC    = base + Math.round(newA * 255).toString(16).padStart(2, '0');
        if (ds.borderWidth !== newW || ds.borderColor !== newC) {
          ds.borderWidth = newW; ds.borderColor = newC;
          ds.pointRadius = isHov ? 6 : hovered === -1 ? 5 : 3;
          changed = true;
        }
      });
      if (changed) chart.update('none');
    },
  };

  new window.Chart(ctx, {
    type: 'line', data: { datasets }, plugins: [highlightPlugin],
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: {
        x: {
          type: 'time',
          time: { tooltipFormat: 'HH:mm:ss', displayFormats: { minute: 'HH:mm', hour: 'HH:mm' } },
          ticks: { color: '#4b6080', font: { size: 10, family: "'IBM Plex Mono', monospace" } },
          grid: { color: 'rgba(255,255,255,0.03)' }, border: { color: '#1e2d47' },
        },
        y: {
          beginAtZero: true,
          ticks: { color: '#4b6080', stepSize: 100, font: { size: 10, family: "'IBM Plex Mono', monospace" } },
          grid: { color: 'rgba(255,255,255,0.03)' }, border: { color: '#1e2d47' },
        },
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#7a9ab8', boxWidth: 10, boxHeight: 2, padding: 14, font: { size: 10, family: "'IBM Plex Mono', monospace" } },
        },
        tooltip: {
          backgroundColor: '#111827', borderColor: '#1e2d47', borderWidth: 1,
          titleColor: '#d4dff0', bodyColor: '#7a9ab8',
          titleFont: { family: "'IBM Plex Mono', monospace", size: 11 },
          bodyFont:  { family: "'IBM Plex Mono', monospace", size: 11 },
          callbacks: {
            label: (ctx) => {
              const { rank, scenario, pts } = ctx.raw;
              return ` ${ctx.dataset.label} — Scénario ${scenario} · #${rank} · +${pts} pts → ${ctx.parsed.y} pts`;
            },
          },
        },
      },
    },
  });
}

// === Render all ===

let currentMode = 'rank';
let lastData = null;

function renderAll(data) {
  lastData = data;
  const scored     = rowsForMode(currentMode, data);
  const scenarios  = [...new Set(scored.map(r => r.scenario))].sort((a, b) => a - b);
  const scoreboard = computeScoreboard(scored);
  renderPodium(scoreboard, scored, data.playerCount);
  renderScoreboard(scoreboard, scenarios);
  renderChart(scored);
  renderFeed(data.events);
  const _u = updated();
  if (_u) _u.textContent = `Mis à jour : ${new Date().toLocaleTimeString()}`;
}

function normalizeData(raw) {
  return {
    rows: raw?.rows ?? [],
    events: raw?.events ?? [],
    playerCount: raw?.playerCount ?? 0,
  };
}

function setupTabs() {
  const bar = document.getElementById('score-mode-tabs');
  if (!bar) return;
  bar.addEventListener('click', (e) => {
    const btn = e.target.closest('.helper-tab');
    if (!btn || !bar.contains(btn)) return;
    const mode = btn.dataset.mode;
    if (!mode || mode === currentMode) return;
    currentMode = mode;
    bar.querySelectorAll('.helper-tab').forEach(b => {
      const active = b.dataset.mode === currentMode;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    if (lastData) renderAll(lastData);
  });
}

// === Main ===

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();

  // Render from cache immediately if available
  const cached = (() => {
    try { return JSON.parse(localStorage.getItem(CACHE_KEY)); } catch { return null; }
  })();

  if (cached?.rows) {
    renderAll(normalizeData(cached));
    setStatus('');
  } else {
    setStatus('En attente des données...');
  }

  // Cas 1 : même onglet est le leader (CustomEvent direct)
  window.addEventListener('ctf:data-updated', ({ detail }) => {
    renderAll(normalizeData(detail));
    setStatus('');
  });

  // Cas 2 : un autre onglet est le leader (storage event cross-tab)
  window.addEventListener('storage', (e) => {
    if (e.key !== CACHE_KEY) return;
    try {
      renderAll(normalizeData(JSON.parse(e.newValue)));
      setStatus('');
    } catch {}
  });
});
