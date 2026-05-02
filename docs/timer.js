(function () {
  let _countdownInterval = null;

  function _formatCountdown(ms) {
    if (ms <= 0) return 'MISSION TERMINEE';
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function _renderTimer(endTimeMs) {
    const el = document.getElementById('mission-timer');
    if (!el) return;

    if (!endTimeMs) {
      el.textContent = '';
      el.className = 'mission-timer';
      if (_countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
      return;
    }

    const tick = () => {
      const rem = endTimeMs - Date.now();
      el.textContent = _formatCountdown(rem);
      el.className = 'mission-timer' + (rem <= 0 ? ' expired' : rem < 300_000 ? ' urgent' : '');
      if (rem <= 0 && _countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
    };

    if (_countdownInterval) clearInterval(_countdownInterval);
    tick();
    if (endTimeMs - Date.now() > 0) {
      _countdownInterval = setInterval(tick, 1000);
    }
  }

  function _refresh(endTimeMs) {
    _renderTimer(endTimeMs ?? null);
  }

  window.addEventListener('ctf:data-updated', (e) => {
    _refresh(e.detail.missionEndTime);
  });

  // ── Admin mission control modal ───────────────────────────────────

  function _injectAdminControls() {
    // Modal overlay
    if (document.getElementById('mission-control-overlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'mission-control-overlay';
    overlay.className = 'submit-overlay';
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="submit-modal" role="dialog" aria-modal="true">
        <div class="submit-modal-header">
          <div class="submit-modal-stamp">MISSION CONTROL</div>
          <button class="submit-modal-close" id="mc-close">&times;</button>
        </div>
        <div style="padding:1.5rem">
          <p class="submit-modal-desc">Definir la date et heure de fin de mission :</p>
          <div style="margin-bottom:1rem">
            <label style="display:block;font-size:0.65rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--c-muted);margin-bottom:0.4rem">DATE ET HEURE DE FIN</label>
            <input type="datetime-local" id="mc-end-time"
              style="background:var(--c-bg);border:1px solid var(--c-border);color:var(--c-text);font-family:inherit;font-size:0.8rem;padding:0.4rem 0.6rem;outline:none;width:100%;box-sizing:border-box">
          </div>
          <button id="mc-activate" class="submit-trigger" style="width:100%">ACTIVER LA MISSION</button>
          <p id="mc-status" style="margin-top:0.75rem;font-size:0.72rem;color:var(--c-muted);min-height:1.2em"></p>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    document.getElementById('mc-close').addEventListener('click', () => { overlay.hidden = true; });
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.hidden = true; });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') overlay.hidden = true; });

    document.getElementById('mc-activate').addEventListener('click', async () => {
      const input = document.getElementById('mc-end-time').value;
      const statusEl = document.getElementById('mc-status');
      if (!input) {
        statusEl.style.color = 'var(--c-red)';
        statusEl.textContent = 'Veuillez choisir une date de fin.';
        return;
      }
      const end_time_ms = new Date(input).getTime();
      if (isNaN(end_time_ms)) {
        statusEl.style.color = 'var(--c-red)';
        statusEl.textContent = 'Date invalide.';
        return;
      }

      const pseudo = typeof getPseudo === 'function' ? getPseudo() : '';
      const btn = document.getElementById('mc-activate');
      btn.disabled = true;
      btn.textContent = 'Activation...';
      statusEl.textContent = '';

      try {
        const resp = await fetch(API_URL + 'mission-control', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pseudo, end_time_ms }),
        });
        const data = await resp.json();
        if (resp.ok) {
          statusEl.style.color = 'var(--c-green)';
          statusEl.textContent = 'Mission activee ! Timer en cours de propagation...';
          _refresh(end_time_ms);
        } else {
          statusEl.style.color = 'var(--c-red)';
          statusEl.textContent = data.message || data.error || 'Erreur.';
        }
      } catch {
        statusEl.style.color = 'var(--c-red)';
        statusEl.textContent = 'Erreur reseau.';
      } finally {
        btn.disabled = false;
        btn.textContent = 'ACTIVER LA MISSION';
      }
    });
  }

  // ── Init ──────────────────────────────────────────────────────────

  function _init() {
    const pseudo = typeof getPseudo === 'function' ? getPseudo() : null;
    if (typeof isAdminPseudo === 'function' && pseudo && isAdminPseudo(pseudo)) {
      _injectAdminControls();
    }
    _refresh(null);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }
})();
