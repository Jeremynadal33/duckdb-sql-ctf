/* ── CTF Graph — DuckDB WASM + Cytoscape.js ── */

const DUCKDB_VERSION = '1.29.0';
const DUCKDB_CDN     = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${DUCKDB_VERSION}`;

const COLORS = {
  bg:      '#0f1117', surface: '#151c2c', border: '#1d2940',
  muted:   '#3d5278', text:    '#c8d8f0', accent: '#f0c000',
  red:     '#e74c3c', green:   '#27ae60', blue:   '#4a90d9',
};

let cy  = null;
let db  = null;
let con = null;

// ── DuckDB WASM init ──────────────────────────────────────────────

async function initDuckDB() {
  const duckdb = await import(`${DUCKDB_CDN}/+esm`);
  const bundles = duckdb.getJsDelivrBundles();
  const bundle  = await duckdb.selectBundle(bundles);

  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: 'text/javascript' })
  );
  const worker = new Worker(workerUrl);
  const logger = new duckdb.VoidLogger();

  db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);

  con = await db.connect();
}

// ── Query via GRAPH_TABLE (DuckPGQ) ──────────────────────────────

async function queryGraph(graphName = 'social_network') {
  // All edges with both endpoint properties
  const r = await con.query(`
    FROM GRAPH_TABLE (${graphName}
      MATCH (p1:persons)-[r:relationships]->(p2:persons)
      COLUMNS (
        p1.id           AS src_id,
        p1.first_name   AS src_first_name,
        p1.last_name    AS src_last_name,
        p1.occupation   AS src_occupation,
        p1.notes        AS src_notes,
        p2.id           AS dst_id,
        p2.first_name   AS dst_first_name,
        p2.last_name    AS dst_last_name,
        p2.occupation   AS dst_occupation,
        p2.notes        AS dst_notes,
        r.id            AS rel_id,
        r.relationship_type,
        r.notes         AS rel_notes
      )
    )
  `);

  const rows = r.toArray();

  // Deduplicate nodes from both endpoints
  const nodesMap = new Map();
  const edges = [];

  for (const row of rows) {
    for (const [id, fn, ln, occ, notes] of [
      [row.src_id, row.src_first_name, row.src_last_name, row.src_occupation, row.src_notes],
      [row.dst_id, row.dst_first_name, row.dst_last_name, row.dst_occupation, row.dst_notes],
    ]) {
      if (!nodesMap.has(String(id))) {
        nodesMap.set(String(id), {
          id: String(id), first_name: fn, last_name: ln,
          occupation: occ ?? '', notes: notes ?? '',
        });
      }
    }
    edges.push({
      id:                String(row.rel_id),
      person_id_1:       String(row.src_id),
      person_id_2:       String(row.dst_id),
      relationship_type: row.relationship_type,
      notes:             row.rel_notes ?? '',
    });
  }

  return { persons: [...nodesMap.values()], relationships: edges };
}

// ── Load from uploaded .duckdb file ──────────────────────────────

async function loadFromFile(file) {
  setStatus('loading', `Chargement de ${file.name}…`);
  try {
    if (!db) await initDuckDB();

    const buf = await file.arrayBuffer();
    await db.registerFileBuffer(file.name, new Uint8Array(buf));

    // Drop previous attach if re-loading
    try { await con.query('DETACH social'); } catch (_) {}

    await con.query(`ATTACH '${file.name}' AS social (READ_ONLY)`);

    const { persons, relationships } = await queryGraph('social.social_network');
    buildGraph(persons, relationships);
    setStatus('ok', `${persons.length} noeuds · ${relationships.length} liens`);
  } catch (e) {
    setStatus('err', 'Erreur : ' + e.message);
    console.error(e);
  }
}

// ── Load from S3 (reads graph_data.json) ─────────────────────────

async function loadFromS3(keyId, secret, bucket) {
  setStatus('loading', 'Connexion S3…');
  try {
    if (!db) await initDuckDB();

    await con.query('INSTALL httpfs; LOAD httpfs;');
    // Drop previous secret if any
    try { await con.query('DROP SECRET IF EXISTS ctf_s3'); } catch (_) {}
    await con.query(`
      CREATE SECRET ctf_s3 (
        TYPE S3,
        KEY_ID '${keyId}',
        SECRET '${secret}',
        REGION 'eu-west-1'
      )
    `);

    setStatus('loading', 'Chargement du graphe S3…');

    try { await con.query('DETACH social'); } catch (_) {}
    await con.query(`ATTACH 's3://${bucket}/data/social_network.duckdb' AS social (READ_ONLY)`);

    const { persons, relationships } = await queryGraph('social.social_network');
    buildGraph(persons, relationships);
    setStatus('ok', `${persons.length} noeuds · ${relationships.length} liens`);
  } catch (e) {
    setStatus('err', 'Erreur : ' + e.message);
    console.error(e);
  }
}

// ── Cytoscape graph builder ───────────────────────────────────────

const VICTIM_ID  = '42';
const SUSPECT_ID = '43';

function buildGraph(persons, relationships) {
  const nodes = persons.map(p => ({
    data: {
      id:         p.id,
      label:      `${p.first_name} ${p.last_name}`,
      occupation: p.occupation,
      notes:      p.notes,
      isVictim:   p.isVictim  ?? p.id === VICTIM_ID,
      isSuspect:  p.isSuspect ?? p.id === SUSPECT_ID,
    },
  }));

  const edges = relationships.map(r => ({
    data: {
      id:        `rel-${r.id}`,
      source:    r.person_id_1,
      target:    r.person_id_2,
      label:     r.relationship_type,
      notes:     r.notes,
      isKeyEdge: Boolean(r.notes && r.notes.startsWith('FLAG')),
    },
  }));

  // Show canvas, hide empty state
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('cy').style.display = 'block';
  document.getElementById('node-count').textContent =
    `${nodes.length} noeuds · ${edges.length} liens`;

  if (cy) cy.destroy();

  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: [...nodes, ...edges],
    style: [
      {
        selector: 'node',
        style: {
          'background-color':   COLORS.surface,
          'border-width': 1, 'border-color': COLORS.muted,
          'label': 'data(label)',
          'color': COLORS.text,
          'font-family': '"Courier New", Courier, monospace',
          'font-size': 9,
          'text-valign': 'bottom', 'text-margin-y': 4,
          'text-wrap': 'ellipsis', 'text-max-width': 80,
          'width': 26, 'height': 26,
        },
      },
      {
        selector: 'node:selected, node.active',
        style: {
          'background-color': 'rgba(74,144,217,0.2)',
          'border-color': COLORS.blue, 'border-width': 2,
          'color': COLORS.blue, 'font-weight': 'bold',
          'width': 34, 'height': 34,
        },
      },
      {
        selector: 'edge',
        style: {
          'width': 1, 'line-color': COLORS.muted,
          'target-arrow-color': COLORS.muted, 'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)', 'color': COLORS.muted,
          'font-family': '"Courier New", Courier, monospace', 'font-size': 8,
          'text-background-opacity': 0.85, 'text-background-color': COLORS.bg,
          'text-background-padding': '2px',
        },
      },
      {
        selector: 'edge:selected',
        style: {
          'line-color': COLORS.blue, 'target-arrow-color': COLORS.blue,
          'color': COLORS.blue,
        },
      },
      {
        selector: '.faded',
        style: { 'opacity': 0.08 },
      },
    ],
    layout: { name: 'cose', animate: true, animationDuration: 700, randomize: true },
  });

  cy.on('tap', 'node', e => {
    cy.nodes().removeClass('active');
    e.target.addClass('active');
    showDetail(e.target);
  });
  cy.on('tap',    'edge', e => showDetail(e.target));
  cy.on('tap',    e => { if (e.target === cy) { cy.nodes().removeClass('active'); hideDetail(); } });
  cy.on('dbltap', 'node', e => isolateNode(e.target));
}

// ── Isolate / search ─────────────────────────────────────────────

function isolateNode(node) {
  if (!cy) return;
  const neighborhood = node.closedNeighborhood();
  cy.elements().addClass('faded');
  neighborhood.removeClass('faded');
  neighborhood.layout({
    name: 'cose', animate: true, animationDuration: 400,
    fit: true, padding: 60, randomize: false,
  }).run();
  document.getElementById('btn-reset-view').style.display = 'inline-block';
  showDetail(node);
}

function resetView() {
  if (!cy) return;
  cy.elements().removeClass('faded');
  cy.layout({ name: 'cose', animate: true, animationDuration: 400 }).run();
  document.getElementById('btn-reset-view').style.display = 'none';
}

function searchNodes(query) {
  if (!cy) return;
  if (!query.trim()) { cy.elements().removeClass('faded'); return; }
  const q = query.toLowerCase();
  const matches = cy.nodes().filter(n => n.data('label').toLowerCase().includes(q));
  if (!matches.length) return;
  cy.elements().addClass('faded');
  matches.closedNeighborhood().removeClass('faded');
  cy.animate({ fit: { eles: matches, padding: 80 }, duration: 400 });
  document.getElementById('btn-reset-view').style.display = 'inline-block';
}

// ── Detail panel ──────────────────────────────────────────────────

function showDetail(el) {
  const d = el.data();
  const title = el.isNode() ? d.label : `${el.source().data('label')} → ${el.target().data('label')}`;
  const rows = el.isNode()
    ? [['Occupation', d.occupation], ['Notes', d.notes]]
    : [['Type de relation', d.label], ['Notes', d.notes]];

  document.getElementById('detail-title').textContent = title;
  document.getElementById('detail-body').innerHTML = rows
    .filter(([, v]) => v)
    .map(([k, v]) => `
      <div class="detail-row">
        <span class="detail-key">${k}</span>
        <span class="detail-val${v.startsWith('FLAG') ? ' flag' : ''}">${v}</span>
      </div>`)
    .join('');
  document.getElementById('detail-panel').classList.add('visible');
}

function hideDetail() {
  document.getElementById('detail-panel').classList.remove('visible');
}

// ── Status helper ─────────────────────────────────────────────────

function setStatus(state, msg) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  dot.className  = `status-dot ${state}`;
  text.textContent = msg;
  document.getElementById('node-count').textContent = msg;
}

// ── Event listeners ───────────────────────────────────────────────

document.getElementById('btn-upload').addEventListener('click', () => {
  document.getElementById('file-input').click();
});

document.getElementById('file-input').addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) loadFromFile(file);
});

document.getElementById('btn-s3').addEventListener('click', () => {
  const keyId  = document.getElementById('s3-key').value.trim();
  const secret = document.getElementById('s3-secret').value.trim();
  const bucket = document.getElementById('s3-bucket').value.trim();
  if (!keyId || !secret || !bucket) {
    alert('Renseignez KEY_ID, SECRET et le nom du bucket.');
    return;
  }
  loadFromS3(keyId, secret, bucket);
});

document.getElementById('detail-close').addEventListener('click', hideDetail);
document.getElementById('btn-reset-view').addEventListener('click', resetView);

let searchTimer;
document.getElementById('search-input').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => searchNodes(e.target.value), 250);
});

document.getElementById('search-input').addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    e.target.value = '';
    resetView();
  }
});

document.querySelectorAll('[data-layout]').forEach(btn => {
  btn.addEventListener('click', () => {
    if (!cy) return;
    document.querySelectorAll('[data-layout]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    cy.layout({ name: btn.dataset.layout, animate: true, animationDuration: 400 }).run();
  });
});
