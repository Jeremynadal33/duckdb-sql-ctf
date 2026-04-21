// ── Lieux de l'enquête — affichage progressif selon la progression ─
// Chaque lieu est révélé après la completion du scénario indiqué (0 = toujours visible)
// Coordonnées chargées depuis locations.js (généré par: mise run generate:locations)
// Pour modifier les coordonnées, éditer constants.py puis relancer generate:locations
const C = typeof LOCATION_COORDS !== 'undefined' ? LOCATION_COORDS : {};

const LOCATIONS = [
  {
    unlockAfter: 0,
    lat: C.library?.lat ?? 44.87383720544609, lon: C.library?.lon ?? -0.5728187300381997,
    label: 'Bibliothèque du Lac',
    sublabel: C.library?.city ?? 'Bordeaux',
    note: 'Point de départ. Registres de prêts suspects découverts ici.',
    type: 'library',
  },
  {
    unlockAfter: 2,
    lat: C.city_hall?.lat ?? 44.84003190271778, lon: C.city_hall?.lon ?? -0.5788558745417992,
    label: 'Hotel de Ville',
    sublabel: C.city_hall?.city ?? 'Bordeaux',
    note: 'Mairie de Bordeaux. Registres nationaux consultés pour l\'identification du suspect',
    type: 'mairie',
  },
  {
    unlockAfter: 3,
    lat: C.quackie?.lat ?? 44.883994690921455, lon: C.quackie?.lon ?? -0.5783725032146239,
    label: 'Domicile de Quackie Chan',
    sublabel: C.quackie?.city ?? 'Bordeaux',
    note: 'Adresse relevée lors du géocodage inversé. Personne décédée — badge déjà usurpé.',
    type: 'victim',
  },
  {
    unlockAfter: 4,
    lat: 46.66676058512701, lon: 0.36749264120380337,
    label: 'Arret au Futuroscope parce qu\'il aime bien les parcs d\'attractions',
    sublabel: 'Poitiers',
    note: 'Petit kiffe perso pour le suspect, pas forcément pertinent pour l\'enquête mais ça nous a fait rire de le mettre dans le scénario alors on le laisse !',
    type: 'suspect',
  },
  {
    unlockAfter: 6,
    lat: C.target?.lat ?? 48.87971881975437, lon: C.target?.lon ?? 2.2835799241186945,
    label: 'Domicile de Hugh Quackman',
    sublabel: C.target?.city ?? 'Paris',
    note: 'Adresse du suspect final. Il était parmis nous depuis le début, surveiller bien votre entourage !',
    type: 'suspect',
  },
];

const COLORS = {
  text:     '#111',
  sublabel: '#4a90d9',
  note:     '#333',
};

const TYPE_COLORS = {
  library: '#4a90d9',
  archive: '#f0c000',
  mairie:  '#f0c000',
  victim:  '#e8956d',
  suspect: '#f85149',
};

const TYPE_LABELS = {
  library: 'Bibliothèque',
  archive: 'Archives',
  mairie:  'Mairie',
  victim:  'Victime',
  suspect: 'Suspect',
};

// ── Lecture de la progression depuis le cache ─────────────────────

function getUnlockedScenarios() {
  const pseudo = localStorage.getItem('ctf_agent');
  const unlocked = new Set([0]);
  if (!pseudo) return unlocked;
  if (typeof isAdminPseudo === 'function' && isAdminPseudo(pseudo)) {
    LOCATIONS.forEach(loc => unlocked.add(loc.unlockAfter));
    return unlocked;
  }
  try {
    const raw = localStorage.getItem('ctf_data_cache');
    if (!raw) return unlocked;
    const { rows } = JSON.parse(raw);
    for (const row of (rows ?? [])) {
      if (row.pseudo === pseudo && row.scenario) {
        unlocked.add(Number(row.scenario));
      }
    }
  } catch (_) {}
  return unlocked;
}

function getVisibleLocations() {
  const unlocked = getUnlockedScenarios();
  const max = unlocked.size > 1 ? Math.max(...unlocked) : 0;
  return LOCATIONS.filter(loc => loc.unlockAfter <= max);
}

// ── Leaflet ───────────────────────────────────────────────────────

function makeIcon(type) {
  const color = TYPE_COLORS[type] ?? '#8b949e';
  return L.divIcon({
    className: '',
    html: `<div style="width:14px;height:14px;background:${color};border:3px solid #0d1117;border-radius:50%;box-shadow:0 0 8px ${color}88"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

let leafletMap = null;
let markersLayer = null;
let routeLine    = null;

function renderMap(locations) {
  if (!leafletMap) {
    leafletMap = L.map('map', { center: [46.5, 1.8], zoom: 6 });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(leafletMap);
  }

  // Clear previous markers and route
  if (markersLayer) markersLayer.clearLayers();
  else markersLayer = L.layerGroup().addTo(leafletMap);
  if (routeLine) { routeLine.remove(); routeLine = null; }

  if (!locations.length) return;

  const markers = [];
  const coords  = [];

  for (const loc of locations) {
    const color = TYPE_COLORS[loc.type] ?? '#8b949e';
    const m = L.marker([loc.lat, loc.lon], { icon: makeIcon(loc.type) })
      .bindPopup(`
        <strong style="color:${COLORS.text}">${loc.label}</strong><br>
        <span style="color:${COLORS.sublabel};font-size:0.78rem">${loc.sublabel}</span><br><br>
        <span style="font-size:0.82rem;color:${COLORS.note}">${loc.note}</span><br>
        <code style="font-size:0.7rem;color:${color}">${loc.lat.toFixed(5)}, ${loc.lon.toFixed(5)}</code>
      `);
    markersLayer.addLayer(m);
    markers.push(m);
    coords.push([loc.lat, loc.lon]);
  }

  if (coords.length > 1) {
    routeLine = L.polyline(coords, { color: '#2a3f62', weight: 2, dashArray: '6 4' }).addTo(leafletMap);
  }

  leafletMap.invalidateSize();
  const group = L.featureGroup(markers);
  leafletMap.fitBounds(group.getBounds().pad(0.4));

  // Update legend
  renderLegend(locations);
}

function renderLegend(locations) {
  const legend = document.getElementById('map-legend');
  if (!legend) return;
  const types = [...new Set(locations.map(l => l.type))];
  legend.innerHTML = types.map(t =>
    `<span class="legend-item">
      <span class="legend-dot" style="background:${TYPE_COLORS[t]}"></span>
      ${TYPE_LABELS[t]}
    </span>`
  ).join('');
}

// ── Mise à jour réactive ──────────────────────────────────────────

function refresh() {
  renderMap(getVisibleLocations());
}

// Lancer immédiatement (le script est chargé après le DOM avec src normal)
refresh();

// Mise à jour si un scénario est débloqué dans le même onglet
window.addEventListener('ctf:data-updated', refresh);

// Mise à jour cross-onglet
window.addEventListener('storage', e => {
  if (e.key === 'ctf_data_cache') refresh();
});
