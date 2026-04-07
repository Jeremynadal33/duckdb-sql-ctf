// === Configuration ===
const CACHE_KEY = 'ctf_data_cache';

// Scoring: 1st = 100, 2nd = 90, ..., 10th+ = 50
function scoreForRank(rank) {
  return Math.max(50, 100 - (rank - 1) * 10);
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
  for (const { pseudo, scenario, rank } of rows) {
    if (!players[pseudo]) players[pseudo] = { pseudo, totalScore: 0, scenarios: {} };
    const pts = scoreForRank(rank);
    players[pseudo].scenarios[scenario] = { rank, pts };
    players[pseudo].totalScore += pts;
  }
  return Object.values(players).sort(
    (a, b) => b.totalScore - a.totalScore || a.pseudo.localeCompare(b.pseudo)
  );
}

function renderPodium(scoreboard, rows) {
  [1, 2, 3].forEach((place, i) => {
    const card = document.getElementById(`podium-${place}`);
    if (!card) return;
    const player = scoreboard[i];
    card.querySelector('.p-name').textContent  = player?.pseudo ?? '\u2014';
    card.querySelector('.p-score').textContent = player ? `${player.totalScore} pts` : '0 pts';
  });
  const statPlayers = document.getElementById('stat-players');
  const statSolved  = document.getElementById('stat-solved');
  if (statPlayers) statPlayers.textContent = scoreboard.length;
  if (statSolved)  statSolved.textContent  = rows.length;
}

function renderScoreboard(scoreboard, scenarios) {
  thead().innerHTML =
    `<th>Rang</th><th>Joueur</th><th>Score</th>` +
    scenarios.map(s => `<th>Sc\u00e9nario ${s}</th>`).join('');
  tbody().innerHTML = '';

  if (scoreboard.length === 0) {
    const cols = 3 + scenarios.length;
    tbody().innerHTML = `<tr><td colspan="${cols}" style="color:#64748b;padding:2rem">Aucun r\u00e9sultat pour l\u2019instant \u2014 soyez le premier\u00a0!</td></tr>`;
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
      cells += data
        ? `<td class="solved">#${data.rank} (${data.pts}pts)</td>`
        : `<td class="unsolved">\u2014</td>`;
    }
    tr.innerHTML = cells;
    tbody().appendChild(tr);
  });
}

function renderFeed(events) {
  const list = document.getElementById('feed-list');
  if (!list) return;
  if (!events?.length) {
    list.innerHTML = `<div class="feed-empty">Aucune activit\u00e9 pour l'instant.</div>`;
    return;
  }
  list.innerHTML = events.map(ev => {
    const isSuccess = ev.action === 'FLAG_SUBMISSION_SUCCESS';
    const time = ev.timestamp
      ? new Date(ev.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : '';
    const tag = isSuccess
      ? `<span class="feed-tag feed-tag-success">SUCCESS</span>`
      : `<span class="feed-tag feed-tag-rejected">REJECTED</span>`;
    const detail = isSuccess
      ? `<span class="feed-pseudo">${escapeHtml(ev.pseudo ?? '?')}</span> \u2014 Sc\u00e9nario <strong>${escapeHtml(ev.scenario ?? '?')}</strong>`
      : `<span class="feed-pseudo">${escapeHtml(ev.pseudo ?? '?')}</span> \u2014 Sc\u00e9nario <strong>${escapeHtml(ev.scenario ?? '?')}</strong>${ev.reason ? `<div class="feed-reason">${escapeHtml(ev.reason)}</div>` : ''}`;
    return `<div class="feed-item ${isSuccess ? 'feed-item-success' : 'feed-item-rejected'}">
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
  for (const { pseudo, rank, scenario, solved_at } of rows) {
    if (!events[pseudo]) events[pseudo] = [];
    events[pseudo].push({ t: new Date(solved_at), pts: scoreForRank(rank), rank, scenario });
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
              return ` ${ctx.dataset.label} \u2014 Sc\u00e9nario ${scenario} \u00b7 #${rank} \u00b7 +${pts} pts \u2192 ${ctx.parsed.y} pts`;
            },
          },
        },
      },
    },
  });
}

// === Render all ===

function renderAll(rows, events) {
  const scenarios  = [...new Set(rows.map(r => r.scenario))].sort((a, b) => a - b);
  const scoreboard = computeScoreboard(rows);
  renderPodium(scoreboard, rows);
  renderScoreboard(scoreboard, scenarios);
  renderChart(rows);
  renderFeed(events);
  const _u = updated();
  if (_u) _u.textContent = `Mis \u00e0 jour : ${new Date().toLocaleTimeString()}`;
}

// === Main ===

document.addEventListener('DOMContentLoaded', () => {
  // Render from cache immediately if available
  const cached = (() => {
    try { return JSON.parse(localStorage.getItem(CACHE_KEY)); } catch { return null; }
  })();

  if (cached?.rows) {
    renderAll(cached.rows, cached.events ?? []);
    setStatus('');
  } else {
    setStatus('En attente des donn\u00e9es...');
  }

  // Cas 1 : même onglet est le leader (CustomEvent direct)
  window.addEventListener('ctf:data-updated', ({ detail }) => {
    renderAll(detail.rows, detail.events ?? []);
    setStatus('');
  });

  // Cas 2 : un autre onglet est le leader (storage event cross-tab)
  window.addEventListener('storage', (e) => {
    if (e.key !== CACHE_KEY) return;
    try {
      const { rows, events } = JSON.parse(e.newValue);
      renderAll(rows, events ?? []);
      setStatus('');
    } catch {}
  });
});
