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
  _applyUpdate(data.rows, data.events, data.playerCount, data.missionEndTime);
};

function _applyUpdate(rows, events, playerCount, missionEndTime) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ rows, events, playerCount, missionEndTime, ts: Date.now() }));
  } catch {}
  window.dispatchEvent(new CustomEvent('ctf:data-updated', { detail: { rows, events, playerCount, missionEndTime } }));
}

// ── Bootstrap from cache (all tabs, instant render without waiting for leader) ──
(function _bootstrapFromCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return;
    const { rows, events, playerCount, missionEndTime } = JSON.parse(raw);
    window.dispatchEvent(new CustomEvent('ctf:data-updated', {
      detail: { rows: rows ?? [], events: events ?? [], playerCount: playerCount ?? 0, missionEndTime: missionEndTime ?? null },
    }));
  } catch {}
  // Ask the current leader to broadcast fresh data immediately
  CTF_BC.postMessage({ type: 'ctf-wake' });
})();

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
  let rows = [], events = [], playerCount = 0, missionEndTime = null;

  // Rows carry both scoring modes precomputed:
  //   rank_solve / pts_solve  = solve-order rank (1st finisher = #1, 100→50 pts)
  //   rank_time  / pts_time   = time-based rank (fastest time_spent = #1,
  //                             linear 100→50 pts over a 10-min window,
  //                             50 pts flat after)
  // time_spent on scenario N = solved_at(N) − solved_at(N−1); for scenario 1
  // the prev anchor is the user's own REGISTRATION timestamp.
  // Hint malus (applied to both pts_solve and pts_time, floor 0):
  //   Δ = hint_open_time - prev_time (time elapsed in solve window)
  //   Δ <  3 min → -15,  3 ≤ Δ <  6 min → -10,
  //   6 ≤ Δ < 15 min →  -5,  Δ ≥ 15 min → 0
  //   Hints opened after solved_at are ignored.
  try {
    const r = await conn.query(`
      WITH ev AS (
        SELECT json_extract_string(value, '$.pseudo') AS pseudo,
               CAST(json_extract_string(value, '$.scenario') AS INTEGER) AS scenario,
               timestamp AS solved_at
        FROM read_parquet('${url}')
        WHERE action = 'FLAG_SUBMISSION_SUCCESS'
      ),
      dedup AS (
        SELECT pseudo, scenario, MIN(solved_at) AS solved_at
        FROM ev GROUP BY pseudo, scenario
      ),
      reg AS (
        SELECT json_extract_string(value, '$.pseudo') AS pseudo,
               MIN(timestamp) AS registered_at
        FROM read_parquet('${url}')
        WHERE action = 'REGISTRATION'
        GROUP BY pseudo
      ),
      with_prev AS (
        SELECT d.pseudo, d.scenario, d.solved_at,
               CASE WHEN d.scenario = 1 THEN r.registered_at
                    ELSE LAG(d.solved_at) OVER (PARTITION BY d.pseudo ORDER BY d.scenario)
               END AS prev_time
        FROM dedup d LEFT JOIN reg r USING (pseudo)
      ),
      with_time AS (
        SELECT pseudo, scenario, solved_at, prev_time,
               CASE WHEN prev_time IS NULL THEN NULL
                    ELSE GREATEST(0, EPOCH_MS(solved_at) - EPOCH_MS(prev_time))
               END AS time_spent_ms
        FROM with_prev
      ),
      hints_raw AS (
        SELECT json_extract_string(value, '$.pseudo') AS pseudo,
               CAST(json_extract_string(value, '$.scenario') AS INTEGER) AS scenario,
               json_extract_string(value, '$.hint_title') AS hint_title,
               MIN(timestamp) AS hint_at
        FROM read_parquet('${url}')
        WHERE action = 'HINT_EXPANDED'
        GROUP BY pseudo, scenario, hint_title
      ),
      hints_scoped AS (
        SELECT w.pseudo, w.scenario, h.hint_title, h.hint_at,
          CASE
            WHEN EPOCH_MS(h.hint_at) - EPOCH_MS(w.prev_time) < 180000  THEN 15
            WHEN EPOCH_MS(h.hint_at) - EPOCH_MS(w.prev_time) < 360000  THEN 10
            WHEN EPOCH_MS(h.hint_at) - EPOCH_MS(w.prev_time) < 900000  THEN 5
            ELSE 0
          END AS malus
        FROM with_time w
        INNER JOIN hints_raw h
          ON h.pseudo = w.pseudo AND h.scenario = w.scenario
         AND h.hint_at < w.solved_at
      ),
      hint_malus AS (
        SELECT pseudo, scenario,
          COUNT(*) AS hints_used,
          CAST(SUM(malus) AS INTEGER) AS malus_pts,
          to_json(array_agg({title: hint_title, malus: malus} ORDER BY hint_at)) AS hints_detail
        FROM hints_scoped
        GROUP BY pseudo, scenario
      ),
      scored AS (
        SELECT pseudo, scenario, solved_at, time_spent_ms,
          ROW_NUMBER() OVER (PARTITION BY scenario ORDER BY solved_at ASC) AS rank_solve,
          ROW_NUMBER() OVER (PARTITION BY scenario
                             ORDER BY time_spent_ms ASC NULLS LAST, solved_at ASC) AS rank_time,
          MIN(time_spent_ms) OVER (PARTITION BY scenario) AS fastest_ms
        FROM with_time
      ),
      with_pts_raw AS (
        SELECT s.*,
          GREATEST(50, 100 - (s.rank_solve - 1) * 10) AS pts_solve_raw,
          CASE
            WHEN s.time_spent_ms IS NULL THEN 0
            WHEN s.time_spent_ms <= s.fastest_ms THEN 100
            WHEN s.time_spent_ms - s.fastest_ms >= 600000 THEN 50
            ELSE CAST(ROUND(100 - (s.time_spent_ms - s.fastest_ms) / 600000.0 * 50) AS INTEGER)
          END AS pts_time_raw
        FROM scored s
      )
      SELECT p.pseudo, p.scenario, p.solved_at, p.time_spent_ms,
             p.rank_solve, p.rank_time,
             CAST(COALESCE(m.hints_used, 0) AS INTEGER) AS hints_used,
             CAST(COALESCE(m.malus_pts, 0) AS INTEGER) AS hint_malus,
             COALESCE(CAST(m.hints_detail AS VARCHAR), '[]') AS hints_detail,
             GREATEST(0, p.pts_solve_raw - COALESCE(m.malus_pts, 0)) AS pts_solve,
             GREATEST(0, p.pts_time_raw  - COALESCE(m.malus_pts, 0)) AS pts_time
      FROM with_pts_raw p
      LEFT JOIN hint_malus m USING (pseudo, scenario)
      ORDER BY pseudo, scenario
    `);
    rows = r.toArray().map(row => {
      let hintsDetail = [];
      try { hintsDetail = JSON.parse(row.hints_detail ?? '[]'); } catch {}
      return {
        pseudo:        row.pseudo,
        scenario:      Number(row.scenario),
        solved_at:     row.solved_at,
        time_spent_ms: row.time_spent_ms == null ? null : Number(row.time_spent_ms),
        rank_solve:    Number(row.rank_solve),
        rank_time:     Number(row.rank_time),
        pts_solve:     Number(row.pts_solve),
        pts_time:      Number(row.pts_time),
        hints_used:    Number(row.hints_used),
        hint_malus:    Number(row.hint_malus),
        hints_detail:  hintsDetail,
      };
    });
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

  try {
    const r = await conn.query(`
      SELECT CAST(json_extract_string(value, '$.end_time_ms') AS BIGINT) AS end_time_ms
      FROM read_parquet('${url}')
      WHERE action = 'MISSION_CONTROL'
      ORDER BY timestamp DESC
      LIMIT 1
    `);
    const mc = r.toArray();
    if (mc.length > 0 && mc[0].end_time_ms != null) {
      missionEndTime = Number(mc[0].end_time_ms);
    }
  } catch (e) { console.warn('[data-agent] missionEndTime query error', e); }

  return { rows, events, playerCount, missionEndTime };
}

// If the cached payload was written by an older code version (missing a
// field we now rely on), ignore the stored fingerprint so the leader runs a
// fresh query even when snapshot.parquet's ETag hasn't changed.
function _cachedPayloadLooksStale() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    if (!parsed?.rows?.length) return false;
    return parsed.rows[0].hints_detail === undefined;
  } catch { return false; }
}

async function _runLeader() {
  console.log('[data-agent] elected leader tab');
  const db = await _initDuckDB();
  let _lastFingerprint = _cachedPayloadLooksStale()
    ? ''
    : (localStorage.getItem(FINGERPRINT_KEY) ?? '');
  if (_cachedPayloadLooksStale()) {
    console.log('[data-agent] cached payload lacks new fields, forcing re-query');
  }
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
      const { rows, events, playerCount, missionEndTime } = await _queryAll(conn, SNAPSHOT_URL);
      await conn.close();
      console.log(`[data-agent] poll: query complete in ${Math.round(performance.now() - t0)}ms — ${rows.length} rows, ${events.length} events, ${playerCount} players`);

      // Broadcast + update cache FIRST, then persist fingerprint. Advancing the
      // fingerprint before the cache is written would let a mid-query tab close
      // leave the next leader skipping the work with stale cached data.
      CTF_BC.postMessage({ type: 'ctf-update', rows, events, playerCount, missionEndTime });
      _applyUpdate(rows, events, playerCount, missionEndTime);
      _lastFingerprint = fingerprint;
      localStorage.setItem(FINGERPRINT_KEY, fingerprint);

    } catch (e) {
      console.warn('[data-agent] poll error:', e);
    }
  }

  // Respond to wake requests from newly-opened tabs
  CTF_BC.addEventListener('message', ({ data }) => {
    if (data.type === 'ctf-wake') poll();
  });

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
