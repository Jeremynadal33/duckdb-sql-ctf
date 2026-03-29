// === Configuration ===
// Update this URL after running `terraform apply` and getting the cloudfront_leaderboard_url output
const CLOUDFRONT_URL = "https://d3h7zfct4am98t.cloudfront.net";
const REFRESH_INTERVAL_MS = 60_000;
const SCENARIOS = [1, 2, 3, 4];

// Scoring: 1st = 100, 2nd = 90, ..., 10th+ = 50
function scoreForRank(rank) {
  return Math.max(50, 100 - (rank - 1) * 10);
}

// === DuckDB-WASM setup ===
import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";

const status = document.getElementById("status");
const tbody = document.querySelector("#leaderboard tbody");
const updated = document.getElementById("updated");

let db;

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
  const conn = await db.connect();

  try {
    await conn.query(`INSTALL httpfs; LOAD httpfs;`);
  } catch {
    // already installed
    await conn.query(`LOAD httpfs;`);
  }

  const result = await conn.query(`
    WITH results AS (
      SELECT pseudo, scenario, solved_at
      FROM read_parquet('${CLOUDFRONT_URL}/*.parquet')
    ),
    ranked AS (
      SELECT
        pseudo,
        scenario,
        solved_at,
        ROW_NUMBER() OVER (PARTITION BY scenario ORDER BY solved_at ASC) AS rank
      FROM results
    )
    SELECT pseudo, scenario, rank
    FROM ranked
    ORDER BY pseudo, scenario
  `);

  await conn.close();

  // Convert Arrow result to plain objects
  const rows = result.toArray().map((row) => ({
    pseudo: row.pseudo,
    scenario: row.scenario,
    rank: Number(row.rank),
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

function renderScoreboard(scoreboard) {
  tbody.innerHTML = "";

  if (scoreboard.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:#8b949e;padding:2rem">No results yet — be the first to solve a scenario!</td></tr>`;
    return;
  }

  scoreboard.forEach((player, index) => {
    const tr = document.createElement("tr");
    const rankClass = index < 3 ? ` class="rank-${index + 1}"` : "";

    let cells = `<td${rankClass}>#${index + 1}</td>`;
    cells += `<td>${escapeHtml(player.pseudo)}</td>`;
    cells += `<td class="score">${player.totalScore}</td>`;

    for (const s of SCENARIOS) {
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

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function refresh() {
  try {
    status.textContent = "Refreshing...";
    const rows = await fetchLeaderboard();
    const scoreboard = computeScoreboard(rows);
    renderScoreboard(scoreboard);
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
