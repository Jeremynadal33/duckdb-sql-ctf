/**
 * CTF Data Agent — shared DuckDB instance across all tabs
 *
 * Uses the Web Locks API to elect one "leader" tab.
 * The leader initialises DuckDB WASM, polls S3 every 30s,
 * writes results to localStorage and broadcasts via BroadcastChannel.
 * All tabs (including the leader) listen to the channel and dispatch
 * a custom DOM event `ctf:data-updated` so pages can react.
 */

const CTF_BC       = new BroadcastChannel('ctf-data');
const CACHE_KEY    = 'ctf_data_cache';
const POLL_MS      = 30_000;
const S3_BUCKET    = 'duckdb-sql-ctf';
const S3_REGION    = 'eu-west-1';
const S3_BASE_URL  = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;
const S3_PREFIX    = 'leaderboard/ctf-events/';

// ── Broadcast receiver (all tabs including leader) ───────────────
CTF_BC.onmessage = ({ data }) => {
  if (data.type !== 'ctf-update') return;
  _applyUpdate(data.rows, data.events);
};

function _applyUpdate(rows, events) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ rows, events, ts: Date.now() }));
  } catch {}
  window.dispatchEvent(new CustomEvent('ctf:data-updated', { detail: { rows, events } }));
}

// ── Leader logic ─────────────────────────────────────────────────

async function _initDuckDB() {
  const duckdb    = await import('https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm');
  const bundle    = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: 'text/javascript' })
  );
  const worker = new Worker(workerUrl);
  const db     = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  return db;
}

async function _listParquetFiles() {
  const urls = [];
  let continuationToken = null;
  do {
    const params = new URLSearchParams({ 'list-type': '2', prefix: S3_PREFIX });
    if (continuationToken) params.set('continuation-token', continuationToken);
    const resp = await fetch(`${S3_BASE_URL}?${params}`);
    if (!resp.ok) throw new Error(`S3 listing failed: ${resp.status}`);
    const xml = await resp.text();
    const doc = new DOMParser().parseFromString(xml, 'application/xml');
    for (const el of doc.querySelectorAll('Contents > Key')) {
      const key = el.textContent;
      if (key.endsWith('.parquet')) urls.push(`${S3_BASE_URL}/${key}`);
    }
    const isTruncated = doc.querySelector('IsTruncated')?.textContent === 'true';
    continuationToken = isTruncated ? doc.querySelector('NextContinuationToken')?.textContent : null;
  } while (continuationToken);
  return urls;
}

function _getCacheAge() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return Infinity;
    return Date.now() - (JSON.parse(raw).ts ?? 0);
  } catch { return Infinity; }
}

async function _runLeader() {
  const db = await _initDuckDB();
  let _lastKeys = '';

  async function poll() {
    try {
      const urls = await _listParquetFiles();
      if (urls.length === 0) return;

      // Fingerprint the file list — skip DuckDB if nothing changed
      const keysFingerprint = urls.join('|');
      if (keysFingerprint === _lastKeys) return;
      _lastKeys = keysFingerprint;

      const conn = await db.connect();
      try { await conn.query(`LOAD httpfs;`); } catch {}
      try {
        await conn.query(`SET s3_region='eu-west-1'; SET s3_access_key_id=''; SET s3_secret_access_key='';`);
      } catch {}

      const urlList = urls.map(u => `'${u}'`).join(', ');
      let rows = [], events = [];

      try {
        const r = await conn.query(`
          WITH ev AS (
            SELECT json_extract_string(value, '$.pseudo') AS pseudo,
                   CAST(json_extract_string(value, '$.scenario') AS INTEGER) AS scenario,
                   timestamp AS solved_at
            FROM read_parquet([${urlList}])
            WHERE action = 'FLAG_SUBMISSION_SUCCESS'
          ),
          dedup AS (SELECT pseudo, scenario, MIN(solved_at) AS solved_at FROM ev GROUP BY pseudo, scenario),
          ranked AS (
            SELECT pseudo, scenario, solved_at,
                   ROW_NUMBER() OVER (PARTITION BY scenario ORDER BY solved_at ASC) AS rank
            FROM dedup
          )
          SELECT pseudo, scenario, rank, solved_at FROM ranked ORDER BY pseudo, scenario
        `);
        rows = r.toArray().map(row => ({
          pseudo:    row.pseudo,
          scenario:  Number(row.scenario),
          rank:      Number(row.rank),
          solved_at: row.solved_at,
        }));
      } catch (e) { console.warn('[data-agent] rows query error', e); }

      try {
        const r = await conn.query(`
          SELECT action,
                 json_extract_string(value, '$.pseudo')   AS pseudo,
                 json_extract_string(value, '$.scenario') AS scenario,
                 json_extract_string(value, '$.reason')   AS reason,
                 timestamp
          FROM read_parquet([${urlList}])
          WHERE action IN ('FLAG_SUBMISSION_SUCCESS', 'FLAG_SUBMISSION_REJECTED')
          ORDER BY timestamp DESC
          LIMIT 50
        `);
        events = r.toArray().map(row => ({
          action:    row.action,
          pseudo:    row.pseudo,
          scenario:  row.scenario,
          reason:    row.reason,
          timestamp: row.timestamp,
        }));
      } catch (e) { console.warn('[data-agent] events query error', e); }

      await conn.close();

      // Broadcast to all tabs (including self via _applyUpdate below)
      CTF_BC.postMessage({ type: 'ctf-update', rows, events });
      _applyUpdate(rows, events);

    } catch (e) {
      console.warn('[data-agent] poll error:', e);
    }
  }

  // If cache is fresh, delay first poll to avoid redundant fetch on page navigation
  const cacheAge = _getCacheAge();
  if (cacheAge < POLL_MS) {
    setTimeout(() => { poll(); setInterval(poll, POLL_MS); }, POLL_MS - cacheAge);
  } else {
    await poll();
    setInterval(poll, POLL_MS);
  }

  // Hold the lock forever (until tab closes)
  await new Promise(() => {});
}

// ── Leader election ───────────────────────────────────────────────
if ('locks' in navigator) {
  navigator.locks.request('ctf-data-leader', { mode: 'exclusive' }, _runLeader).catch(() => {});
} else {
  // Fallback: no multi-tab coordination, just run
  _runLeader().catch(() => {});
}
