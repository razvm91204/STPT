'use strict';
// ScheduleModule – calcul orare reale, potrivire curse, plecări
const ScheduleModule = (function () {

  // Aplatizează orarul unei stații într-un array sortat de minute de la miezul nopții
  function flatten(station, dayType) {
    const sched = station && station.schedule && station.schedule[dayType];
    if (!sched) return [];
    const times = [];
    for (const [h, mins] of Object.entries(sched)) {
      const hour = parseInt(h);
      if (isNaN(hour) || hour < 0 || hour > 23) continue;
      for (const m of mins) {
        if (m >= 0 && m <= 59) times.push(hour * 60 + m);
      }
    }
    return times.sort((a, b) => a - b);
  }

  // Returnează indexul primei valori >= fromMin, sau null dacă nu există
  function nextRank(times, fromMin) {
    if (!times || !times.length) return null;
    const idx = times.findIndex(t => t >= fromMin);
    return idx === -1 ? null : idx;
  }

  // Calculează ora de sosire la stația alightIdx.
  // Folosește greedy forward: prima cursă la destinație strict după ora de plecare.
  // Corect chiar și când stațiile intermediare au curse scurte (short-turn) ce nu
  // trec prin stația de plecare și ar decala un K-index simplu.
  function tripArrival(lineId, direction, boardIdx, alightIdx, boardRank, boardTime, dayType) {
    const stations = NETWORK_DATA[lineId]?.[direction]?.stations;
    if (!stations || alightIdx >= stations.length) return null;
    const alightTimes = flatten(stations[alightIdx], dayType);
    if (!alightTimes.length) return null;
    return alightTimes.find(t => t > boardTime) || null;
  }

  function _cleanName(s) {
    return (s || '').trim().replace(/\s+/g, ' ').replace(/\(\s+/g, '(').replace(/\s+\)/g, ')');
  }

  // Returnează lista de opriri cu orele pentru un segment de linie.
  // Parcurgere greedy forward: fiecare stație = prima cursă după ora stației precedente.
  // Evită orele haotice cauzate de K-index când trip-count-urile diferă între stații.
  function legStops(lineId, direction, fromIdx, toIdx, boardRank, dayType) {
    const stations = NETWORK_DATA[lineId]?.[direction]?.stations;
    if (!stations) return [];

    const fromTimes = flatten(stations[fromIdx], dayType);
    if (!fromTimes.length) return [];
    const boardTime = fromTimes[Math.min(boardRank, fromTimes.length - 1)];

    const stops = [{ name: _cleanName(stations[fromIdx].name), time: boardTime }];
    let prevTime = boardTime;

    for (let k = fromIdx + 1; k <= toIdx; k++) {
      const st = stations[k];
      if (!st) { stops.push({ name: '', time: null }); continue; }
      const times = flatten(st, dayType);
      const t = times.find(x => x > prevTime) || null;
      stops.push({ name: _cleanName(st.name), time: t });
      if (t !== null) prevTime = t;
    }
    return stops;
  }

  // Formatează minute → "HH:MM"
  function toStr(min) {
    if (min == null || isNaN(min)) return '--:--';
    const h = Math.floor(min / 60) % 24;
    const m = min % 60;
    return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');
  }

  // Parsează "HH:MM" → minute de la miezul nopții
  function toMin(str) {
    const parts = (str || '').split(':').map(Number);
    return (parts[0] || 0) * 60 + (parts[1] || 0);
  }

  // Returnează următoarele `count` plecări dintr-o stație pe toate liniile
  function nextDepartures(stationName, nowMin, dayType, count) {
    count = count || 10;
    const norm = DataModule.normalize(stationName);
    const entries = DataModule.stationsToLines.get(norm) || [];
    const results = [];

    for (const { lineId, direction, stationIdx } of entries) {
      const st = NETWORK_DATA[lineId]?.[direction]?.stations?.[stationIdx];
      if (!st) continue;
      const times = flatten(st, dayType);
      for (const t of times) {
        if (t >= nowMin && t <= nowMin + 120) {
          results.push({ lineId, direction, time: t });
          break; // prima plecare per linie/sens
        }
      }
    }
    return results.sort((a, b) => a.time - b.time).slice(0, count);
  }

  return { flatten, nextRank, tripArrival, legStops, toStr, toMin, nextDepartures };

})();
