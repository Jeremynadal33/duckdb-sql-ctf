// === Configuration ===
const IS_LOCAL = false;
const LOCATIONS_URL = IS_LOCAL
  ? `${location.origin}/dev-data/locations.parquet`
  : null; // TODO: URL CloudFront/S3 en prod

const ROLE_COLORS = { target: "#f85149", decoy: "#f0c000", library: "#58a6ff" };

// === DuckDB-WASM setup ===
import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";

let db;
window._db = () => db;

async function initDB() {
  const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" })
  );
  const worker = new Worker(workerUrl);
  const logger = new duckdb.ConsoleLogger();
  db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
}

// === Map ===

function setStatus(msg) {
  const el = document.getElementById("status");
  if (el) el.textContent = msg;
}

function makeLeafletIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;background:${color};border:3px solid #0d1117;border-radius:50%;box-shadow:0 0 8px ${color}99"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

async function loadMap() {
  if (!LOCATIONS_URL) {
    setStatus("URL carte non configur\u00e9e.");
    return;
  }

  const leafletMap = L.map("map", { center: [46.8, 1.7], zoom: 6 });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '\u00a9 <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(leafletMap);

  const response = await fetch(LOCATIONS_URL);
  await db.registerFileBuffer("locations.parquet", new Uint8Array(await response.arrayBuffer()));
  const conn = await db.connect();
  const result = await conn.query("SELECT * FROM read_parquet('locations.parquet')");
  await conn.close();

  const rows = result.toArray().map(r => r.toJSON());
  const markers = [];
  const routeCoords = [];

  for (const row of rows) {
    const color = ROLE_COLORS[row.role] ?? "#8b949e";
    const m = L.marker([row.lat, row.lon], { icon: makeLeafletIcon(color) })
      .addTo(leafletMap)
      .bindPopup(`<strong>${row.person}</strong><br><span style="color:#888;font-size:0.8rem">${row.city}</span><br><br>${row.note}<br><code style="font-size:0.75rem">${row.lat.toFixed(6)}, ${row.lon.toFixed(6)}</code>`);
    markers.push(m);
    routeCoords.push([row.lat, row.lon]);
  }

  if (routeCoords.length > 1) {
    L.polyline(routeCoords, { color: "#484f58", weight: 2, dashArray: "6 4" }).addTo(leafletMap);
  }

  leafletMap.invalidateSize();
  leafletMap.fitBounds(L.featureGroup(markers).getBounds().pad(0.3));

  window._leafletMap = () => leafletMap;
}

// === Main ===

async function main() {
  try {
    await initDB();
    await loadMap();
  } catch (err) {
    setStatus(`Erreur carte : ${err.message}`);
    console.error(err);
  }
}

main();
