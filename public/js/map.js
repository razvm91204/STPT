'use strict';
const MapModule = (function () {

  const CENTER   = [45.7489, 21.2087];
  const MAX_DIST = 500; // metri

  let _map        = null;
  let _mode       = 'from';
  let _fromMarker = null;
  let _toMarker   = null;

  // ── Haversine (metri) ─────────────────────────────────────────────────────
  function _dist(lat1, lon1, lat2, lon2) {
    const R  = 6371000;
    const f1 = lat1 * Math.PI / 180, f2 = lat2 * Math.PI / 180;
    const df = (lat2 - lat1) * Math.PI / 180;
    const dl = (lon2 - lon1) * Math.PI / 180;
    const a  = Math.sin(df/2) * Math.sin(df/2) +
               Math.cos(f1) * Math.cos(f2) * Math.sin(dl/2) * Math.sin(dl/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  // ── Cea mai apropiată stație față de un punct ─────────────────────────────
  function _nearest(lat, lon) {
    if (typeof STATIONS_COORDS === 'undefined') return null;
    let best = null, bestD = Infinity;
    for (const [name, coord] of Object.entries(STATIONS_COORDS)) {
      const d = _dist(lat, lon, coord[0], coord[1]);
      if (d < MAX_DIST && d < bestD) { bestD = d; best = { name, lat: coord[0], lon: coord[1], dist: Math.round(d) }; }
    }
    return best;
  }

  // ── Iconiță pin colorată ──────────────────────────────────────────────────
  function _icon(color) {
    return L.divIcon({
      className: '',
      html: `<div style="width:14px;height:14px;background:${color};border:2.5px solid #fff;border-radius:50%;box-shadow:0 1px 6px rgba(0,0,0,.45)"></div>`,
      iconSize: [14, 14], iconAnchor: [7, 7], popupAnchor: [0, -10]
    });
  }

  // ── Inițializare hartă ────────────────────────────────────────────────────
  function init() {
    if (typeof L === 'undefined') { console.warn('MapModule: Leaflet lipsă'); return; }
    if (typeof STATIONS_COORDS === 'undefined') { console.warn('MapModule: stations_coords.js lipsă'); return; }

    const TM_BOUNDS = L.latLngBounds(L.latLng(45.68, 21.10), L.latLng(45.83, 21.35));
    _map = L.map('map', {
      zoomControl: false,
      maxBounds: TM_BOUNDS,
      maxBoundsViscosity: 1.0,
      minZoom: 11,
    }).setView(CENTER, 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 18
    }).addTo(_map);

    _map.on('click', _onClick);
    _hint('from');
  }

  // ── Handler click hartă ───────────────────────────────────────────────────
  function _onClick(e) {
    const { lat, lng } = e.latlng;
    const stop = _nearest(lat, lng);

    if (_mode === 'from') {
      if (_fromMarker) _map.removeLayer(_fromMarker);
      _fromMarker = L.marker([lat, lng], { icon: _icon('#c2500a') }).addTo(_map);

      if (stop) {
        document.getElementById('from-input').value = stop.name;
        _fromMarker
          .bindPopup(`<b>${stop.name}</b><br><small>${stop.dist} m distanță</small>`)
          .openPopup();
      } else {
        const fallback = document.getElementById('from-input').value.trim();
        const msg = fallback
          ? `Nicio stație în 500 m<br><small>Se va folosi: <b>${fallback}</b></small>`
          : 'Nicio stație în 500 m';
        _fromMarker.bindPopup(msg).openPopup();
        _hint('fallback-from');
      }
      setMode('to');

    } else {
      if (_toMarker) _map.removeLayer(_toMarker);
      _toMarker = L.marker([lat, lng], { icon: _icon('#e74c3c') }).addTo(_map);

      if (stop) {
        document.getElementById('to-input').value = stop.name;
        _toMarker
          .bindPopup(`<b>${stop.name}</b><br><small>${stop.dist} m distanță</small>`)
          .openPopup();
        _hint('ready');
      } else {
        const fallback = document.getElementById('to-input').value.trim();
        const msg = fallback
          ? `Nicio stație în 500 m<br><small>Se va folosi: <b>${fallback}</b></small>`
          : 'Nicio stație în 500 m';
        _toMarker.bindPopup(msg).openPopup();
        _hint('fallback-to');
      }
    }
  }

  // ── Schimbă modul activ (plecare / destinație) ────────────────────────────
  function setMode(mode) {
    _mode = mode;
    const bf = document.getElementById('btn-set-from');
    const bt = document.getElementById('btn-set-to');
    if (bf) bf.className = 'map-pin-btn' + (mode === 'from' ? ' active-from' : '');
    if (bt) bt.className = 'map-pin-btn' + (mode === 'to'   ? ' active-to'   : '');
    _hint(mode);
  }

  function _hint(state) {
    const el = document.getElementById('map-hint');
    if (!el) return;
    const map = {
      from:          'Click pe hartă pentru a seta punctul de plecare',
      to:            'Click pe hartă pentru a seta destinația',
      'fallback-from': 'Nicio stație în 500 m — se va folosi câmpul de text pentru plecare',
      'fallback-to':   'Nicio stație în 500 m — se va folosi câmpul de text pentru destinație',
      ready:         'Ambele puncte setate — apasă Caută rute'
    };
    el.textContent = map[state] || '';
  }

  return { init, setMode };

})();
