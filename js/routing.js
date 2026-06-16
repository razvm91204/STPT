'use strict';
// RoutingModule – motor de rutare BFS cu rute directe și cu 1 transfer
const RoutingModule = (function () {

  function search(from, to, nowMin, dayType) {
    if (!from || !to) return { direct: [], transfers: [] };
    const fromC = DataModule.getCanonical(from) || from;
    const toC   = DataModule.getCanonical(to)   || to;
    if (DataModule.normalize(fromC) === DataModule.normalize(toC)) {
      return { direct: [], transfers: [] };
    }

    const future = _findDirect(fromC, toC, nowMin, dayType);
    const bestArr = future.length ? future[0].arrival : Infinity;
    const transfers = _findTransfers(fromC, toC, nowMin, dayType, bestArr);
    const past = _findRecent(fromC, toC, nowMin, dayType, 20)
                   .map(r => Object.assign(r, { late: true }));

    // Viitoare (sortate deja după sosire), apoi trecute (sortate deja după minsAgo)
    const allDirect = future.concat(past).slice(0, 6);

    return { direct: allDirect, transfers: transfers.slice(0, 3) };
  }

  // ── Rute directe ────────────────────────────────────────────────────────────
  function _findDirect(from, to, nowMin, dayType) {
    const fromNorm = DataModule.normalize(from);
    const toNorm   = DataModule.normalize(to);
    const fromEntries = DataModule.stationsToLines.get(fromNorm) || [];
    const toEntries   = DataModule.stationsToLines.get(toNorm)   || [];

    // Index rapid: "lineId|direction" → stationIdx pentru stația destinație
    const toMap = new Map();
    for (const e of toEntries) toMap.set(`${e.lineId}|${e.direction}`, e.stationIdx);

    const routes = [];
    for (const { lineId, direction, stationIdx: fi } of fromEntries) {
      const ti = toMap.get(`${lineId}|${direction}`);
      if (ti == null || ti <= fi) continue;

      const lineData  = NETWORK_DATA[lineId][direction];
      const boardTimes = ScheduleModule.flatten(lineData.stations[fi], dayType);
      let rank = ScheduleModule.nextRank(boardTimes, nowMin);
      if (rank === null) continue;

      for (let found = 0; rank < boardTimes.length && found < 3; rank++) {
        const dep = boardTimes[rank];
        const arr = ScheduleModule.tripArrival(lineId, direction, fi, ti, rank, dep, dayType);
        if (!arr) continue;
        routes.push({
          lineId, direction,
          from, fromIdx: fi,
          to,   toIdx: ti,
          departure: dep,
          arrival:   arr,
          boardRank: rank,
          duration:  arr - dep,
          wait:      dep - nowMin,
          numStations: ti - fi,
          lineType: DataModule.getLineType(lineId)
        });
        found++;
      }
    }
    return routes.sort((a, b) => a.arrival - b.arrival || a.wait - b.wait);
  }

  // ── Rute cu 1 transfer ──────────────────────────────────────────────────────
  function _findTransfers(from, to, nowMin, dayType, bestDirectArrival) {
    const fromNorm = DataModule.normalize(from);
    const toNorm   = DataModule.normalize(to);
    const fromEntries = DataModule.stationsToLines.get(fromNorm) || [];
    const toEntries   = DataModule.stationsToLines.get(toNorm)   || [];

    // Index pentru liniile care servesc destinația
    const toLineMap = new Map(); // "lineId|direction" → stationIdx
    for (const e of toEntries) toLineMap.set(`${e.lineId}|${e.direction}`, e.stationIdx);

    const results = [];
    const seenHub = new Set(); // deduplicare per (l1|d1|l2|d2|hub)
    const bestByPair = new Map(); // "l1|d1|l2|d2" → best route

    outer:
    for (const { lineId: l1, direction: d1, stationIdx: fi1 } of fromEntries) {
      const lineData1 = NETWORK_DATA[l1][d1];
      const boardTimes1 = ScheduleModule.flatten(lineData1.stations[fi1], dayType);
      const rank1 = ScheduleModule.nextRank(boardTimes1, nowMin);
      if (rank1 === null) continue;
      const dep1 = boardTimes1[rank1];

      for (let hi1 = fi1 + 1; hi1 < lineData1.stations.length; hi1++) {
        const hubSt  = lineData1.stations[hi1];
        const hubRaw = (hubSt.name || '').trim().replace(/\s+/g, ' ').replace(/\(\s+/g, '(').replace(/\s+\)/g, ')');
        if (!hubRaw) continue;
        const hubNorm = DataModule.normalize(hubRaw);

        const hubEntries = DataModule.stationsToLines.get(hubNorm) || [];
        for (const { lineId: l2, direction: d2, stationIdx: hi2 } of hubEntries) {
          if (l1 === l2 && d1 === d2) continue; // aceeași cursă
          const ti2 = toLineMap.get(`${l2}|${d2}`);
          if (ti2 == null || ti2 <= hi2) continue;

          const hubKey = `${l1}|${d1}|${l2}|${d2}|${hubNorm}`;
          if (seenHub.has(hubKey)) continue;
          seenHub.add(hubKey);

          // Timp sosire la hub
          const arr1 = ScheduleModule.tripArrival(l1, d1, fi1, hi1, rank1, dep1, dayType);
          if (!arr1) continue;
          if (arr1 >= nowMin + 180) continue; // max 3h până la hub

          // Plecare de la hub pe linia 2
          const lineData2   = NETWORK_DATA[l2][d2];
          const boardTimes2 = ScheduleModule.flatten(lineData2.stations[hi2], dayType);
          const rank2 = ScheduleModule.nextRank(boardTimes2, arr1);
          if (rank2 === null) continue;
          const dep2 = boardTimes2[rank2];

          const arr2 = ScheduleModule.tripArrival(l2, d2, hi2, ti2, rank2, dep2, dayType);
          if (!arr2) continue;

          // Filtrează: nu afișa dacă e mult mai slab decât directul
          if (bestDirectArrival < Infinity && arr2 > bestDirectArrival + 10) continue;

          const pairKey = `${l1}|${d1}|${l2}|${d2}`;
          const route = {
            leg1: {
              lineId: l1, direction: d1,
              from, fromIdx: fi1, to: hubRaw, toIdx: hi1,
              departure: dep1, arrival: arr1, boardRank: rank1,
              numStations: hi1 - fi1, lineType: DataModule.getLineType(l1)
            },
            leg2: {
              lineId: l2, direction: d2,
              from: hubRaw, fromIdx: hi2, to, toIdx: ti2,
              departure: dep2, arrival: arr2, boardRank: rank2,
              numStations: ti2 - hi2, lineType: DataModule.getLineType(l2)
            },
            hub: hubRaw,
            total: arr2 - nowMin,
            hubWait: dep2 - arr1
          };

          const existing = bestByPair.get(pairKey);
          if (!existing || arr2 < existing.leg2.arrival) {
            bestByPair.set(pairKey, route);
          }

          if (seenHub.size > 400) break outer; // limită de siguranță
        }
      }
    }

    return [...bestByPair.values()].sort((a, b) => a.leg2.arrival - b.leg2.arrival);
  }

  // ── Rute recente (plecate în ultimele N minute) ─────────────────────────────
  function _findRecent(from, to, nowMin, dayType, lookback) {
    const fromNorm = DataModule.normalize(from);
    const toNorm   = DataModule.normalize(to);
    const fromEntries = DataModule.stationsToLines.get(fromNorm) || [];
    const toEntries   = DataModule.stationsToLines.get(toNorm)   || [];

    const toMap = new Map();
    for (const e of toEntries) toMap.set(`${e.lineId}|${e.direction}`, e.stationIdx);

    const routes = [];
    for (const { lineId, direction, stationIdx: fi } of fromEntries) {
      const ti = toMap.get(`${lineId}|${direction}`);
      if (ti == null || ti <= fi) continue;

      const lineData   = NETWORK_DATA[lineId][direction];
      const boardTimes = ScheduleModule.flatten(lineData.stations[fi], dayType);

      // Ultima plecare din fereastra [nowMin-lookback, nowMin)
      const past = boardTimes.filter(t => t >= nowMin - lookback && t < nowMin);
      if (!past.length) continue;
      const dep  = past[past.length - 1]; // cea mai recentă
      const rank = boardTimes.lastIndexOf(dep);

      const arr = ScheduleModule.tripArrival(lineId, direction, fi, ti, rank, dep, dayType);
      if (!arr) continue;

      routes.push({
        lineId, direction,
        from, fromIdx: fi,
        to,   toIdx: ti,
        departure: dep,
        arrival:   arr,
        boardRank: rank,
        duration:  arr - dep,
        minsAgo:   nowMin - dep,
        numStations: ti - fi,
        lineType: DataModule.getLineType(lineId)
      });
    }
    return routes.sort((a, b) => a.minsAgo - b.minsAgo);
  }

  return { search };

})();
