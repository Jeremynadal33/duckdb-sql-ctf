/**
 * CTF Data Agent — shared DuckDB instance across all tabs
 *
 * Uses the Web Locks API to elect one "leader" tab.
 * The leader initialises DuckDB WASM, polls S3 every 15s,
 * writes results to localStorage and broadcasts via BroadcastChannel.
 * All tabs (including the leader) listen to the channel and dispatch
 * a custom DOM event `ctf:data-updated` so pages can react.
 *
 * Read strategy: snapshot-only. A scheduled + S3-triggered Lambda publishes a
 * compacted `snapshot.parquet` with a short-TTL Cache-Control. The frontend
 * fingerprints on the snapshot's ETag and re-queries only when it changes.
 */

const CTF_BC        = new BroadcastChannel('ctf-data');
const CACHE_KEY     = 'ctf_data_cache';
const FINGERPRINT_KEY = 'ctf_data_fingerprint';
const POLL_MS       = 15_000;
const S3_BUCKET    = 'duckdb-sql-ctf';
const S3_REGION    = 'eu-west-1';
const S3_BASE_URL  = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;
const SNAPSHOT_KEY  = 'leaderboard/snapshot.parquet';
const SNAPSHOT_URL  = `${S3_BASE_URL}/${SNAPSHOT_KEY}`;

// ── Broadcast receiver (all tabs including leader) ───────────────
CTF_BC.onmessage = ({ data }) => {
  if (data.type !== 'ctf-update') return;
  console.log(`[data-agent] broadcast received: ${data.rows.length} rows, ${data.events.length} events, ${data.playerCount} players`);
  _applyUpdate(data.rows, data.events, data.playerCount);
};

function _applyUpdate(rows, events, playerCount) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ rows, events, playerCount, ts: Date.now() }));
  } catch {}
  window.dispatchEvent(new CustomEvent('ctf:data-updated', { detail: { rows, events, playerCount } }));
}

// ── Leader logic ─────────────────────────────────────────────────

async function _initDuckDB() {
  console.log('[data-agent] initialising DuckDB WASM…');
  const t0 = performance.now();
  const duckdb    = await import('https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm');
  const bundle    = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: 'text/javascript' })
  );
  const worker = new Worker(workerUrl);
  const db     = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  console.log(`[data-agent] DuckDB ready in ${Math.round(performance.now() - t0)}ms`);
  return db;
}

async function _headSnapshot() {
  const resp = await fetch(SNAPSHOT_URL, { method: 'HEAD', cache: 'no-store' });
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(`snapshot HEAD failed: ${resp.status}`);
  return { etag: resp.headers.get('ETag') ?? '' };
}

function _getCacheAge() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return Infinity;
    return Date.now() - (JSON.parse(raw).ts ?? 0);
  } catch { return Infinity; }
}

async function _queryAll(conn, url) {
  let rows = [], events = [], playerCount = 0;

  try {
    const r = await conn.query(`
      WITH ev AS (
        SELECT json_extract_string(value, '$.pseudo') AS pseudo,
               CAST(json_extract_string(value, '$.scenario') AS INTEGER) AS scenario,
               timestamp AS solved_at
        FROM read_parquet('${url}')
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
      WITH raw AS (
        SELECT action,
               json_extract_string(value, '$.pseudo')     AS pseudo,
               json_extract_string(value, '$.scenario')   AS scenario,
               json_extract_string(value, '$.reason')     AS reason,
               json_extract_string(value, '$.hint_title') AS hint_title,
               timestamp
        FROM read_parquet('${url}')
        WHERE action IN ('FLAG_SUBMISSION_SUCCESS', 'FLAG_SUBMISSION_REJECTED', 'HINT_EXPANDED', 'REGISTRATION')
      ),
      deduped_hints AS (
        SELECT * FROM raw WHERE action != 'HINT_EXPANDED'
        UNION ALL
        SELECT action, pseudo, scenario, reason, hint_title, MIN(timestamp) AS timestamp
        FROM raw WHERE action = 'HINT_EXPANDED'
        GROUP BY action, pseudo, scenario, hint_title, reason
      )
      SELECT * FROM deduped_hints
      ORDER BY timestamp DESC
      LIMIT 50
    `);
    events = r.toArray().map(row => ({
      action:     row.action,
      pseudo:     row.pseudo,
      scenario:   row.scenario,
      reason:     row.reason,
      hint_title: row.hint_title,
      timestamp:  row.timestamp,
    }));
  } catch (e) { console.warn('[data-agent] events query error', e); }

  try {
    const r = await conn.query(`
      SELECT COUNT(DISTINCT json_extract_string(value, '$.pseudo')) AS cnt
      FROM read_parquet('${url}')
      WHERE action = 'REGISTRATION'
    `);
    playerCount = Number(r.toArray()[0]?.cnt ?? 0);
  } catch (e) { console.warn('[data-agent] playerCount query error', e); }

  return { rows, events, playerCount };
}

async function _runLeader() {
  console.log('[data-agent] elected leader tab');
  const db = await _initDuckDB();
  let _lastFingerprint = localStorage.getItem(FINGERPRINT_KEY) ?? '';
  console.log(`[data-agent] restored fingerprint from localStorage: ${_lastFingerprint || '(none)'}`);

  async function poll() {
    try {
      const snapshot = await _headSnapshot();
      if (!snapshot) {
        console.log('[data-agent] poll: snapshot.parquet not found yet (compactor has not run)');
        return;
      }

      const fingerprint = `snap:${snapshot.etag}`;
      if (fingerprint === _lastFingerprint) {
        console.log(`[data-agent] poll: snapshot unchanged (etag=${snapshot.etag}), skipping query`);
        return;
      }
      console.log(`[data-agent] poll: snapshot changed (etag=${snapshot.etag}), querying…`);

      const conn = await db.connect();
      try { await conn.query(`LOAD httpfs;`); } catch {}
      try {
        await conn.query(`SET s3_region='eu-west-1'; SET s3_access_key_id=''; SET s3_secret_access_key='';`);
      } catch {}

      const t0 = performance.now();
      const { rows, events, playerCount } = await _queryAll(conn, SNAPSHOT_URL);
      await conn.close();
      console.log(`[data-agent] poll: query complete in ${Math.round(performance.now() - t0)}ms — ${rows.length} rows, ${events.length} events, ${playerCount} players`);

      // Broadcast + update cache FIRST, then persist fingerprint. Advancing the
      // fingerprint before the cache is written would let a mid-query tab close
      // leave the next leader skipping the work with stale cached data.
      CTF_BC.postMessage({ type: 'ctf-update', rows, events, playerCount });
      _applyUpdate(rows, events, playerCount);
      _lastFingerprint = fingerprint;
      localStorage.setItem(FINGERPRINT_KEY, fingerprint);

    } catch (e) {
      console.warn('[data-agent] poll error:', e);
    }
  }

  // If cache is fresh, delay first poll to avoid redundant fetch on page navigation
  const cacheAge = _getCacheAge();
  if (cacheAge < POLL_MS) {
    const delay = POLL_MS - cacheAge;
    console.log(`[data-agent] cache is fresh (age ${Math.round(cacheAge)}ms), delaying first poll by ${Math.round(delay)}ms`);
    setTimeout(() => { poll(); setInterval(poll, POLL_MS); }, delay);
  } else {
    await poll();
    setInterval(poll, POLL_MS);
  }

  // Hold the lock forever (until tab closes)
  await new Promise(() => {});
}

// ── Leader election ───────────────────────────────────────────────
if ('locks' in navigator) {
  console.log('[data-agent] requesting leader lock…');
  navigator.locks.request('ctf-data-leader', { mode: 'exclusive' }, _runLeader).catch((e) => {
    console.warn('[data-agent] leader lock failed:', e);
  });
} else {
  console.log('[data-agent] Web Locks API unavailable, running standalone');
  _runLeader().catch((e) => console.warn('[data-agent] leader run failed:', e));
}
