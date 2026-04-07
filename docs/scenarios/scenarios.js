// ── Cache ─────────────────────────────────────────────────────────

function getUnlockedFromCache(pseudo) {
  const unlocked = new Set([1]);
  if (!pseudo) return unlocked;
  try {
    const raw = localStorage.getItem('ctf_data_cache');
    if (!raw) return unlocked;
    const { rows } = JSON.parse(raw);
    for (const row of (rows ?? [])) {
      if (row.pseudo === pseudo) {
        const sc = Number(row.scenario);
        unlocked.add(sc);
        unlocked.add(sc + 1);
      }
    }
  } catch {}
  return unlocked;
}

// ── Scenario rendering ────────────────────────────────────────────

function showScenario(n) {
  document.querySelectorAll('.chain-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.scenario === String(n))
  );
  document.querySelectorAll('.sc-panel').forEach(p => {
    p.style.display = p.id === 'scenario-panel-' + n ? 'flex' : 'none';
  });
}

function parseFm(text) {
  const meta = {};
  for (const line of text.trim().split('\n')) {
    const m = line.match(/^(\w+):\s*(.+)$/);
    if (m) meta[m[1]] = m[2].trim();
  }
  return meta;
}

function buildHints(md) {
  if (!md?.trim()) return '';
  return md.split(/(?=^### )/m).filter(p => p.trim()).map(part => {
    const nl    = part.indexOf('\n');
    const title = part.slice(4, nl).trim();
    const body  = marked.parse(part.slice(nl + 1).trim());
    return `<details><summary>${title}</summary><div>${body}</div></details>`;
  }).join('');
}

function buildSteps(md) {
  if (!md?.trim()) return '';
  return md.split('\n')
    .filter(l => /^\s*\d+\./.test(l))
    .map(l => `<li>${marked.parseInline(l.replace(/^\s*\d+\.\s*/, ''))}</li>`)
    .join('');
}

function mdToPanel(raw) {
  const fmMatch = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!fmMatch) return `<div class="sc-body"><p>Erreur de format</p></div>`;

  const meta = parseFm(fmMatch[1]);
  const body = fmMatch[2];

  const sections = {};
  let cur = '__context__';
  for (const line of body.split('\n')) {
    if (/^## /.test(line)) { cur = line.slice(3).trim(); sections[cur] = []; }
    else (sections[cur] ??= []).push(line);
  }

  const numStr     = String(meta.numero || '?').padStart(2, '0');
  const techniques = (meta.techniques || '').split(',').map(t => `<code>${t.trim()}</code>`).join('');
  const contextHTML  = marked.parse((sections['__context__'] || []).join('\n').trim());
  const stepsHTML    = buildSteps((sections['Objectifs'] || []).join('\n'));
  const hintsHTML    = buildHints((sections['Indices'] || []).join('\n'));
  const flagNote     = meta.flag_note ? `<p>${meta.flag_note}</p>` : '';
  const epilogueKey  = Object.keys(sections).find(k => /épilogue|epilogue/i.test(k));
  const epilogueHTML = epilogueKey
    ? `<div class="sc-epilogue">${marked.parse(sections[epilogueKey].join('\n').trim())}</div>`
    : '';

  return `
    <div class="sc-aside">
      <div class="sc-index">${numStr}</div>
      <div class="sc-tags">
        <div class="sc-tags-label">TECHNIQUES</div>
        ${techniques}
      </div>
    </div>
    <div class="sc-body">
      <h2 class="sc-title">${meta.titre || ''}</h2>
      <div class="sc-context">${contextHTML}</div>
      <div class="sc-section">OBJECTIFS</div>
      <ol class="sc-steps">${stepsHTML}</ol>
      <div class="sc-flag">
        <div class="sc-flag-label">${meta.flag_label || 'FLAG ATTENDU'}</div>
        <code>${meta.flag || ''}</code>
        ${flagNote}
      </div>
      <div class="sc-section">INDICES</div>
      <div class="sc-hints">${hintsHTML}</div>
      ${epilogueHTML}
    </div>`;
}

// ── Dynamic scenario loading ──────────────────────────────────────

const SCENARIO_FILES = [1, 2, 3, 4].map(n => `scenario-${n}.md`);

let _loadedRaw = null; // cache the markdown files (no need to re-fetch)

async function loadScenarios() {
  const pseudo   = localStorage.getItem('ctf_agent');
  const unlocked = getUnlockedFromCache(pseudo);

  // Fetch markdown files only once
  if (!_loadedRaw) {
    _loadedRaw = await Promise.all(SCENARIO_FILES.map(async file => {
      try {
        const res = await fetch(file);
        if (!res.ok) return null;
        const raw     = await res.text();
        const fmMatch = raw.match(/^---\n([\s\S]*?)\n---/);
        const meta    = fmMatch ? parseFm(fmMatch[1]) : {};
        return { raw, meta };
      } catch { return null; }
    }));
  }

  const scenarios = _loadedRaw
    .filter(Boolean)
    .sort((a, b) => Number(a.meta.numero || 0) - Number(b.meta.numero || 0));

  const chain           = document.getElementById('scenario-chain');
  const panelsContainer = document.getElementById('scenario-panels');
  chain.innerHTML           = '';
  panelsContainer.innerHTML = '';

  let firstUnlocked = null;
  let activeScenario = null;

  // Preserve currently visible scenario if still unlocked
  const currentActive = document.querySelector('.chain-btn.active');
  if (currentActive) activeScenario = Number(currentActive.dataset.scenario);

  scenarios.forEach(({ raw, meta }, i) => {
    const num        = Number(meta.numero || (i + 1));
    const numStr     = String(num).padStart(2, '0');
    const label      = meta.label || numStr;
    const isUnlocked = unlocked.has(num);

    if (i > 0) {
      const sep = document.createElement('span');
      sep.className = 'chain-line';
      chain.appendChild(sep);
    }

    const btn = document.createElement('button');
    btn.dataset.scenario = num;

    if (isUnlocked) {
      btn.className = 'chain-btn';
      btn.innerHTML = `<span class="cbtn-num">${numStr}</span><span class="cbtn-lbl">${label}</span>`;
      if (firstUnlocked === null) firstUnlocked = num;

      const panel = document.createElement('div');
      panel.className = 'sc-panel';
      panel.id        = 'scenario-panel-' + num;
      panel.innerHTML = mdToPanel(raw);
      panelsContainer.appendChild(panel);
    } else {
      btn.className = 'chain-btn chain-btn-locked';
      btn.disabled  = true;
      btn.title     = 'Complétez le scénario précédent pour débloquer';
      btn.innerHTML = `<span class="cbtn-num">${numStr}</span><span class="cbtn-lbl cbtn-lock">&#x1F512;</span>`;
    }

    chain.appendChild(btn);
  });

  document.querySelectorAll('.chain-btn:not([disabled])').forEach(b =>
    b.addEventListener('click', () => {
      document.querySelectorAll('.chain-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      showScenario(b.dataset.scenario);
    })
  );

  // Restore active scenario if still unlocked, else show first
  const targetScenario = (activeScenario && unlocked.has(activeScenario))
    ? activeScenario
    : firstUnlocked;

  if (targetScenario !== null) {
    document.querySelector(`.chain-btn[data-scenario="${targetScenario}"]`)?.classList.add('active');
    showScenario(String(targetScenario));
  }
}

// ── Boot ─────────────────────────────────────────────────────────

let _currentUnlocked = new Set([1]);
let _updating = false;

function setsEqual(a, b) {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}

async function checkAndUpdate() {
  if (_updating) return;
  _updating = true;
  try {
    const pseudo      = localStorage.getItem('ctf_agent');
    const newUnlocked = getUnlockedFromCache(pseudo);
    if (!setsEqual(newUnlocked, _currentUnlocked)) {
      _currentUnlocked = newUnlocked;
      await loadScenarios();
    }
  } finally {
    _updating = false;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadScenarios();
  _currentUnlocked = getUnlockedFromCache(localStorage.getItem('ctf_agent'));

  // Cas 1 : même onglet est le leader (CustomEvent direct)
  window.addEventListener('ctf:data-updated', checkAndUpdate);

  // Cas 2 : un autre onglet est le leader (storage event cross-tab)
  window.addEventListener('storage', (e) => {
    if (e.key === 'ctf_data_cache') checkAndUpdate();
  });
});
