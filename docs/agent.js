/* ── Agent pseudo — partagé sur toutes les pages ── */

const STORAGE_KEY = 'ctf_agent';
const API_URL = 'https://hn4qoatkok.execute-api.eu-west-1.amazonaws.com/';

function getPseudo()          { return localStorage.getItem(STORAGE_KEY); }
function setPseudo(p)         { localStorage.setItem(STORAGE_KEY, p); }

function renderBadge(pseudo) {
  document.querySelectorAll('.agent-badge').forEach(el => {
    el.textContent = `Agent : ${pseudo}`;
    el.style.display = 'block';
  });
}

async function registerPseudo(pseudo) {
  const resp = await fetch(`${API_URL}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pseudo }),
  });

  const data = await resp.json();

  if (resp.status === 201) {
    return { ok: true, pseudo: data.pseudo };
  }
  if (resp.status === 409) {
    return { ok: false, message: data.message || 'Ce pseudo est deja pris.' };
  }
  if (resp.status === 400) {
    return { ok: false, message: data.message || 'Pseudo invalide.' };
  }
  return { ok: false, message: 'Erreur inattendue. Reessayez.' };
}

function injectModal() {
  const overlay = document.createElement('div');
  overlay.id = 'agent-overlay';
  overlay.innerHTML = `
    <div id="agent-modal">
      <div class="modal-stamp">OPERATION DOSSIERS DISPARUS</div>
      <div class="modal-title">IDENTIFICATION AGENT</div>
      <p class="modal-desc">Entrez votre pseudo pour commencer l'enquête</p>
      <input id="agent-input" type="text" placeholder="Agent_Duck" maxlength="20" autocomplete="off" spellcheck="false">
      <p id="agent-error" style="font-size:0.72rem;color:var(--c-red);min-height:1.1em;margin:0"></p>
      <button id="agent-confirm">CONFIRMER &rarr;</button>
    </div>
  `;
  document.body.appendChild(overlay);

  const input   = document.getElementById('agent-input');
  const btn     = document.getElementById('agent-confirm');
  const error   = document.getElementById('agent-error');

  input.focus();

  async function submit() {
    const val = input.value.trim();
    if (!val) { input.classList.add('shake'); setTimeout(() => input.classList.remove('shake'), 400); return; }

    btn.disabled = true;
    btn.textContent = 'VERIFICATION...';
    error.textContent = '';

    try {
      const result = await registerPseudo(val);
      if (result.ok) {
        setPseudo(result.pseudo);
        overlay.remove();
        renderBadge(result.pseudo);
      } else {
        error.textContent = result.message;
        input.classList.add('shake');
        setTimeout(() => input.classList.remove('shake'), 400);
      }
    } catch {
      error.textContent = 'Erreur reseau. Reessayez.';
    } finally {
      btn.disabled = false;
      btn.innerHTML = 'CONFIRMER &rarr;';
    }
  }

  btn.addEventListener('click', submit);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') submit(); });
}

document.addEventListener('DOMContentLoaded', () => {
  const pseudo = getPseudo();
  if (pseudo) {
    renderBadge(pseudo);
  } else {
    injectModal();
  }
});
