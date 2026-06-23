'use strict';
// AppModule – bootstrap, inițializare, conexiune evenimente
const AppModule = (function () {

  let _initialized = false;

  function init() {
    if (_initialized) return;
    _initialized = true;

    // Inițializare date (construiește indexul stații→linii)
    DataModule.init();

    // Inițializare hartă
    MapModule.init();

    // Configurare autocomplete
    UiModule.setupAutocomplete('from-input', 'from-sug', val => {
      document.getElementById('from-input').value = val;
    });
    UiModule.setupAutocomplete('to-input', 'to-sug', val => {
      document.getElementById('to-input').value = val;
    });

    // Valori inițiale
    const allSt = DataModule.allStations;
    if (allSt.length >= 2) {
      document.getElementById('from-input').value = allSt.find(s => /gara de nord/i.test(s)) || allSt[0];
      document.getElementById('to-input').value   = allSt.find(s => /piata.*victori|victoriei/i.test(DataModule.normalize(s))) || allSt[1];
    }

    // Oră curentă
    const now = new Date();
    const hh  = String(now.getHours()).padStart(2, '0');
    const mm  = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('sel-time').value = `${hh}:${mm}`;

    // Prima căutare
    cauta();
  }

  // Index normalizat al coordonatelor (construit lazy)
  let _coordsIndex = null;
  function _getCoordIndex() {
    if (_coordsIndex) return _coordsIndex;
    _coordsIndex = new Map();
    if (typeof STATIONS_COORDS === 'undefined') return _coordsIndex;
    for (const [k, v] of Object.entries(STATIONS_COORDS)) {
      _coordsIndex.set(DataModule.normalize(k), v);
    }
    return _coordsIndex;
  }

  function _haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000, f1 = lat1*Math.PI/180, f2 = lat2*Math.PI/180;
    const df = (lat2-lat1)*Math.PI/180, dl = (lon2-lon1)*Math.PI/180;
    const a  = Math.sin(df/2)**2 + Math.cos(f1)*Math.cos(f2)*Math.sin(dl/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  }

  // Găsește coordonate pentru un nume de stație (inclusiv fără orar)
  function _coordFor(rawName) {
    const idx  = _getCoordIndex();
    const norm = DataModule.normalize(rawName);
    let coord  = idx.get(norm) || null;
    if (!coord) {
      for (const [k, v] of idx.entries()) {
        if (k.startsWith(norm) || k.includes(norm)) { coord = v; break; }
      }
    }
    return coord;
  }

  // Returnează lista stațiilor CU ORAR în raza maxDist (metri), sortate după distanță
  function _nearbyScheduled(rawName, maxDist) {
    const coord = _coordFor(rawName);
    if (!coord) return [];
    const normSelf = DataModule.normalize(rawName);
    const results  = [];
    for (const stName of DataModule.allStations) {
      if (DataModule.normalize(stName) === normSelf) continue; // sare stația însăși
      const c = _getCoordIndex().get(DataModule.normalize(stName));
      if (!c) continue;
      const d = _haversine(coord[0], coord[1], c[0], c[1]);
      if (d <= maxDist) results.push({ name: stName, dist: Math.round(d) });
    }
    return results.sort((a, b) => a.dist - b.dist);
  }

  // Găsește cea mai apropiată stație CU ORAR față de un nume de stație (chiar fără orar)
  function _nearestScheduled(rawName) {
    const list = _nearbyScheduled(rawName, Infinity);
    return list.length ? list[0] : null;
  }

  // Rezolvă un input → canonical + info "apropiată" dacă e cazul
  function _resolve(raw) {
    // 1. Canonical exact
    if (DataModule.getCanonical(raw)) return { name: DataModule.getCanonical(raw), nearby: null };
    // 2. Prima sugestie autocomplete
    const sugs = DataModule.getSuggestions(raw, 1);
    if (sugs.length) return { name: sugs[0], nearby: null };
    // 3. Cea mai apropiată stație cu orar (fallback geografic)
    const near = _nearestScheduled(raw);
    if (near) return { name: near.name, nearby: { original: raw, dist: near.dist } };
    return { name: raw, nearby: null };
  }

  function cauta() {
    let fromRaw = document.getElementById('from-input').value.trim();
    let toRaw   = document.getElementById('to-input').value.trim();
    const time  = document.getElementById('sel-time').value;
    const day   = document.getElementById('sel-day').value;
    const el    = document.getElementById('results');

    if (!fromRaw || !toRaw) {
      el.innerHTML = `<div class="card"><div class="empty-state">
        <div class="empty-icon">&#9432;</div>
        Selectează stațiile de plecare și destinație.
      </div></div>`;
      return;
    }

    const fromRes = _resolve(fromRaw);
    const toRes   = _resolve(toRaw);

    // Actualizează câmpurile dacă s-a găsit altceva
    if (fromRes.name !== fromRaw) document.getElementById('from-input').value = fromRes.name;
    if (toRes.name   !== toRaw)   document.getElementById('to-input').value   = toRes.name;

    const fromC = fromRes.name;
    const toC   = toRes.name;

    if (DataModule.normalize(fromC) === DataModule.normalize(toC)) {
      el.innerHTML = `<div class="card"><div class="empty-state">
        <div class="empty-icon">&#9888;</div>
        Stația de plecare și destinație sunt aceleași.
      </div></div>`;
      return;
    }

    const nowMin  = ScheduleModule.toMin(time);
    const WALK_M  = 200; // raza de mers pe jos acceptată

    // Candidați: stația exactă (dist=0) + vecine în raza de mers
    const fromCands = [{ name: fromC, dist: 0 }].concat(_nearbyScheduled(fromC, WALK_M)).slice(0, 6);
    const toCands   = [{ name: toC,   dist: 0 }].concat(_nearbyScheduled(toC,   WALK_M)).slice(0, 6);

    // Stațiile exacte au prioritate; vecinele sunt fallback dacă exact nu are rute
    let result   = { direct: [], transfers: [] };
    let usedFrom = { name: fromC, dist: 0 };
    let usedTo   = { name: toC,   dist: 0 };
    let bestArrival = Infinity;

    const exactR = RoutingModule.search(fromC, toC, nowMin, day);
    if (exactR.direct.length || exactR.transfers.length) {
      result = exactR;
    } else {
      for (const fn of fromCands) {
        for (const tn of toCands) {
          if (fn.dist === 0 && tn.dist === 0) continue; // deja încercat
          if (DataModule.normalize(fn.name) === DataModule.normalize(tn.name)) continue;
          const r = RoutingModule.search(fn.name, tn.name, nowMin, day);
          const top = r.direct[0] || (r.transfers[0] ? r.transfers[0].leg2 : null);
          if (top && top.arrival < bestArrival) {
            bestArrival = top.arrival;
            result      = r;
            usedFrom    = fn;
            usedTo      = tn;
          }
        }
      }
    }

    const nearby = {
      from: (fromRes.nearby || usedFrom.dist > 0)
              ? { original: fromRaw, station: usedFrom.name, dist: usedFrom.dist || fromRes.nearby?.dist }
              : null,
      to:   (toRes.nearby   || usedTo.dist > 0)
              ? { original: toRaw,   station: usedTo.name,   dist: usedTo.dist   || toRes.nearby?.dist   }
              : null
    };

    UiModule.renderResults(result, usedFrom.name, usedTo.name, nowMin, day, nearby);
  }

  function loadFav(from, to) {
    document.getElementById('from-input').value = from;
    document.getElementById('to-input').value   = to;
    UiModule.showTab('plan');
    cauta();
  }

  return { init, cauta, loadFav };

})();

// Pornire după încărcarea DOM
document.addEventListener('DOMContentLoaded', () => AppModule.init());
