/* ── Agent pseudo — partagé sur toutes les pages ── */

const STORAGE_KEY = 'ctf_agent';

function getPseudo()          { return localStorage.getItem(STORAGE_KEY); }
function setPseudo(p)         { localStorage.setItem(STORAGE_KEY, p); }

function renderBadge(pseudo) {
  document.querySelectorAll('.agent-badge').forEach(el => {
    el.textContent = `Agent : ${pseudo}`;
    el.style.display = 'block';
  });
}

function injectModal() {
  const overlay = document.createElement('div');
  overlay.id = 'agent-overlay';
  overlay.innerHTML = `
    <div id="agent-modal">
      <div class="modal-stamp">OPERATION CANARDS DISPARUS</div>
      <div class="modal-title">IDENTIFICATION AGENT</div>
      <p class="modal-desc">Entrez votre pseudo pour commencer l'enquête</p>
      <input id="agent-input" type="text" placeholder="Agent_Duck" maxlength="24" autocomplete="off" spellcheck="false">
      <button id="agent-confirm">CONFIRMER &rarr;</button>
    </div>
  `;
  document.body.appendChild(overlay);

  const input   = document.getElementById('agent-input');
  const confirm = document.getElementById('agent-confirm');

  input.focus();

  function submit() {
    const val = input.value.trim();
    if (!val) { input.classList.add('shake'); setTimeout(() => input.classList.remove('shake'), 400); return; }
    setPseudo(val);
    overlay.remove();
    renderBadge(val);
  }

  confirm.addEventListener('click', submit);
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
