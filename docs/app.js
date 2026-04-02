// === Configuration ===
const S3_BUCKET = "duckdb-sql-ctf";
const S3_REGION = "eu-west-1";
const S3_PREFIX = "leaderboard/results/";
const S3_BASE_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;
const IS_LOCAL = false; // bascule en local pour tests (doit être lancé depuis la racine du projet avec `python -m http.server`)
const LOCAL_RESULTS_URL = `${location.origin}/dev-data/results.parquet`;
const REFRESH_INTERVAL_MS = 30_000;

// Scoring: 1st = 100, 2nd = 90, ..., 10th+ = 50
function scoreForRank(rank) {
  return Math.max(50, 100 - (rank - 1) * 10);
}

// === S3 file listing (glob workaround for DuckDB-WASM) ===
async function listParquetFiles() {
  const urls = [];
  let continuationToken = null;

  if (IS_LOCAL) {
    // En mode local, on suppose qu'il n'y a qu'un seul fichier de résultats
    urls.push(LOCAL_RESULTS_URL);
    return urls;
  }

  do {
    const params = new URLSearchParams({
      "list-type": "2",
      prefix: S3_PREFIX,
    });
    if (continuationToken) {
      params.set("continuation-token", continuationToken);
    }

    const resp = await fetch(`${S3_BASE_URL}?${params}`);
    if (!resp.ok) throw new Error(`S3 listing failed: ${resp.status}`);

    const xml = await resp.text();
    const doc = new DOMParser().parseFromString(xml, "application/xml");

    for (const el of doc.querySelectorAll("Contents > Key")) {
      const key = el.textContent;
      if (key.endsWith(".parquet")) {
        urls.push(`${S3_BASE_URL}/${key}`);
      }
    }

    const isTruncated = doc.querySelector("IsTruncated")?.textContent === "true";
    continuationToken = isTruncated
      ? doc.querySelector("NextContinuationToken")?.textContent
      : null;
  } while (continuationToken);

  return urls;
}

// === DuckDB-WASM setup ===
import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";

const status = document.getElementById("status");
const thead = document.querySelector("#leaderboard thead tr");
const tbody = document.querySelector("#leaderboard tbody");
const updated = document.getElementById("updated");

let db;
window._db = () => db; // debug: accès depuis la console navigateur

async function initDB() {
  const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

  // Workers can't be loaded cross-origin — use an inline worker that imports the script
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
  );
  const worker = new Worker(workerUrl);
  const logger = new duckdb.ConsoleLogger();
  db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
}

async function fetchLeaderboard() {
  const urls = await listParquetFiles();
  if (urls.length === 0) return [];

  const conn = await db.connect();

  try {
    await conn.query(`INSTALL httpfs; LOAD httpfs;`);
  } catch {
    // already installed
    await conn.query(`LOAD httpfs;`);
  }

  const urlList = urls.map((u) => `'${u}'`).join(", ");
  let result;
  try {
    result = await conn.query(`
      WITH results AS (
        SELECT pseudo, scenario, solved_at
        FROM read_parquet([${urlList}])
      ),
      ranked AS (
        SELECT
          pseudo,
          scenario,
          solved_at,
          ROW_NUMBER() OVER (PARTITION BY scenario ORDER BY solved_at ASC) AS rank
        FROM results
      )
      SELECT pseudo, scenario, rank, solved_at
      FROM ranked
      ORDER BY pseudo, scenario
    `);
  } catch {
    // No results files yet
    await conn.close();
    return [];
  }

  await conn.close();

  // Convert Arrow result to plain objects
  const rows = result.toArray().map((row) => ({
    pseudo: row.pseudo,
    scenario: row.scenario,
    rank: Number(row.rank),
    solved_at: row.solved_at,
  }));

  return rows;
}

function computeScoreboard(rows) {
  // Group by player
  const players = {};
  for (const { pseudo, scenario, rank } of rows) {
    if (!players[pseudo]) {
      players[pseudo] = { pseudo, totalScore: 0, scenarios: {} };
    }
    const pts = scoreForRank(rank);
    players[pseudo].scenarios[scenario] = { rank, pts };
    players[pseudo].totalScore += pts;
  }

  // Sort by total score desc, then by name
  return Object.values(players).sort(
    (a, b) => b.totalScore - a.totalScore || a.pseudo.localeCompare(b.pseudo)
  );
}

function renderScoreboard(scoreboard, scenarios) {
  // En-têtes dynamiques
  thead.innerHTML =
    `<th>Rang</th><th>Joueur</th><th>Score</th>` +
    scenarios.map(s => `<th>Scénario ${s}</th>`).join("");

  tbody.innerHTML = "";

  if (scoreboard.length === 0) {
    const cols = 3 + scenarios.length;
    tbody.innerHTML = `<tr><td colspan="${cols}" style="color:#8b949e;padding:2rem">Aucun résultat pour l'instant — soyez le premier !</td></tr>`;
    return;
  }

  scoreboard.forEach((player, index) => {
    const tr = document.createElement("tr");
    const rankClass = index < 3 ? ` class="rank-${index + 1}"` : "";

    let cells = `<td${rankClass}>#${index + 1}</td>`;
    cells += `<td>${escapeHtml(player.pseudo)}</td>`;
    cells += `<td class="score">${player.totalScore}</td>`;

    for (const s of scenarios) {
      const data = player.scenarios[s];
      if (data) {
        cells += `<td class="solved">#${data.rank} (${data.pts}pts)</td>`;
      } else {
        cells += `<td class="unsolved">—</td>`;
      }
    }

    tr.innerHTML = cells;
    tbody.appendChild(tr);
  });
}

// Palette de couleurs pour les joueurs
const PLAYER_COLORS = [
  "#58a6ff", "#3fb950", "#f0c000", "#f0883e",
  "#bc8cff", "#79c0ff", "#56d364", "#ffa657",
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
      x: t,
      y: (cumul += pts),
      rank,
      scenario,
      pts,
    }));
  }
  return series;
}

function renderChart(rows) {
  const series = computeTimeSeries(rows);
  const pseudos = Object.keys(series);

  const datasets = pseudos.map((pseudo, i) => {
    const color = PLAYER_COLORS[i % PLAYER_COLORS.length];
    return {
      label: pseudo,
      data: series[pseudo],
      borderColor: color,
      backgroundColor: color + "22",
      tension: 0.3,
      stepped: "before",
      pointRadius: 5,
      pointHoverRadius: 7,
    };
  });

  const ctx = document.getElementById("progress-chart").getContext("2d");

  const existing = window.Chart.getChart("progress-chart");
  if (existing) existing.destroy();

  const highlightPlugin = {
    id: "highlightOnHover",
    afterEvent(chart, { event }) {
      const { type } = event;
      if (!["mousemove", "mouseout"].includes(type)) return;

      const points = chart.getElementsAtEventForMode(
        event.native, "nearest", { intersect: true }, true
      );
      const hoveredDatasetIndex = points.length ? points[0].datasetIndex : -1;

      let changed = false;
      chart.data.datasets.forEach((ds, i) => {
        const isHovered = i === hoveredDatasetIndex;
        const newWidth  = isHovered ? 3 : hoveredDatasetIndex === -1 ? 2 : 1;
        const newAlpha  = isHovered ? 1 : hoveredDatasetIndex === -1 ? 1 : 0.25;
        const base      = PLAYER_COLORS[i % PLAYER_COLORS.length];
        const newColor  = base + Math.round(newAlpha * 255).toString(16).padStart(2, "0");

        if (ds.borderWidth !== newWidth || ds.borderColor !== newColor) {
          ds.borderWidth = newWidth;
          ds.borderColor = newColor;
          ds.pointRadius = isHovered ? 6 : hoveredDatasetIndex === -1 ? 5 : 3;
          changed = true;
        }
      });
      if (changed) chart.update("none");
    },
  };

  new window.Chart(ctx, {
    type: "line",
    data: { datasets },
    plugins: [highlightPlugin],
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: {
          type: "time",
          time: { tooltipFormat: "HH:mm:ss", displayFormats: { minute: "HH:mm", hour: "HH:mm" } },
          ticks: { color: "#8b949e" },
          grid: { color: "#21262d" },
        },
        y: {
          beginAtZero: true,
          ticks: { color: "#8b949e", stepSize: 50 },
          grid: { color: "#21262d" },
          title: { display: true, text: "Score cumulé", color: "#8b949e" },
        },
      },
      plugins: {
        legend: { labels: { color: "#e6edf3" } },
        tooltip: {
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

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function refresh() {
  try {
    status.textContent = "Refreshing...";
    const rows = await fetchLeaderboard();
    const scenarios = [...new Set(rows.map(r => r.scenario))].sort((a, b) => a - b);
    const scoreboard = computeScoreboard(rows);
    renderScoreboard(scoreboard, scenarios);
    renderChart(rows);
    status.textContent = "";
    updated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
    console.error(err);
  }
}

async function main() {
  try {
    await initDB();
    status.textContent = "Fetching results...";
    await refresh();
    setInterval(refresh, REFRESH_INTERVAL_MS);
  } catch (err) {
    status.textContent = `Failed to initialize: ${err.message}`;
    console.error(err);
  }
}

main();
