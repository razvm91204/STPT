'use strict';
// DataModule – încărcare date, normalizare stații, index stații→linii
const DataModule = (function () {

  const LINE_TYPES = {
    '1':'tram','2':'tram','4':'tram','7':'tram','8':'tram','9':'tram',
    '5':'bus','5B':'bus','11':'bus','13':'bus','14':'bus','15':'bus',
    '16':'bus','17':'bus','18':'bus','21':'bus','24':'bus','28':'bus',
    '32':'bus','33':'bus','33B':'bus','40':'bus','46':'bus',
    'E1':'met','E2':'met','E3':'met','E4':'met','E4B':'met',
    'E6':'met','E7':'met','E8':'met'
  };

  let _allStations = [];
  let _stationsToLines = new Map(); // norm → [{lineId, direction, stationIdx}]
  let _canonicalMap   = new Map(); // norm → canonical string

  // Normalizare completă: spații, liniuțe, fără diacritice, lowercase
  function normalize(name) {
    if (!name) return '';
    return name.trim()
      .replace(/\s+/g, ' ')
      .replace(/\s*[-–—]\s*/g, '-')
      .replace(/\(\s+/g, '(').replace(/\s+\)/g, ')')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[,.]/g, '')
      .trim();
  }

  // Normalizare bază: elimină paranteza și conținutul ei.
  // Folosit ca cheie în stationsToLines pentru a unifica variante ale aceleiași stații:
  // "PIAȚA 700 (Spitalul Militar)" și "PIAȚA 700 (Paris)" → ambele "piata 700"
  function normalizeBase(name) {
    if (!name) return '';
    const base = (name + '').replace(/\s*\(.*$/, '').trim();
    return normalize(base);
  }

  function init() {
    const seen = new Map(); // fullNorm → canonical (space-cleaned)

    for (const [lineId, dirs] of Object.entries(NETWORK_DATA)) {
      for (const [direction, lineData] of Object.entries(dirs)) {
        lineData.stations.forEach((st, idx) => {
          const name = (st.name || '').trim();
          if (!name) return;

          // Validare orar
          const sched = st.schedule;
          let valid = false;
          if (sched) {
            for (const dt of ['school','vacation','holiday']) {
              const s = sched[dt];
              if (!s) continue;
              for (const [h, mins] of Object.entries(s)) {
                const hour = parseInt(h);
                if (isNaN(hour) || hour < 0 || hour > 23) {
                  console.warn('Ora invalida', h, 'la statia', name);
                  continue;
                }
                for (const m of mins) {
                  if (m < 0 || m > 59) {
                    console.warn('Minut invalid', m, 'la statia', name);
                    continue;
                  }
                  valid = true;
                }
              }
            }
          }
          if (!valid) return;

          const norm = normalize(name);
          // Curăță spații din interiorul parantezelor: "( Ion Vidu )" → "(Ion Vidu)"
          const cleanName = name.replace(/\s+/g, ' ').replace(/\(\s+/g, '(').replace(/\s+\)/g, ')');

          if (!seen.has(norm)) seen.set(norm, cleanName);
          _canonicalMap.set(norm, seen.get(norm));

          // stationsToLines: cheie = norm complet — fiecare variantă are rutele ei separate
          if (!_stationsToLines.has(norm)) _stationsToLines.set(norm, []);
          _stationsToLines.get(norm).push({ lineId, direction, stationIdx: idx });
        });
      }
    }

    _allStations = [...seen.values()].sort(function(a, b) {
      return a.localeCompare(b, 'ro', { sensitivity: 'base' });
    });
    console.log('DataModule: ' + _allStations.length + ' statii indexate');
  }

  function getSuggestions(query, limit) {
    limit = limit || 10;
    if (!query || !query.trim()) return _allStations.slice(0, limit);
    const q = normalize(query);
    const starts = [], contains = [];
    for (const s of _allStations) {
      const n = normalize(s);
      if (n.startsWith(q)) starts.push(s);
      else if (n.includes(q)) contains.push(s);
    }
    return starts.concat(contains).slice(0, limit);
  }

  function getCanonical(name) {
    if (!name) return null;
    return _canonicalMap.get(normalize(name)) || null;
  }

  function getLineType(lineId) {
    return LINE_TYPES[lineId] || 'bus';
  }

  function getLineName(lineId, direction) {
    const stations = NETWORK_DATA[lineId] && NETWORK_DATA[lineId][direction] && NETWORK_DATA[lineId][direction].stations;
    if (!stations || !stations.length) return 'Linia ' + lineId;
    const first = stations.find(function(s) { return (s.name || '').trim(); });
    const last  = stations.slice().reverse().find(function(s) { return (s.name || '').trim(); });
    if (!first || !last) return 'Linia ' + lineId;
    return first.name.trim() + ' → ' + last.name.trim();
  }

  return {
    init           : init,
    normalize      : normalize,
    normalizeBase  : normalizeBase,
    getSuggestions : getSuggestions,
    getCanonical   : getCanonical,
    getLineType    : getLineType,
    getLineName    : getLineName,
    get allStations()    { return _allStations; },
    get stationsToLines(){ return _stationsToLines; }
  };

})();
