'use strict';
// UiModule – interfața, autocomplete, randare rezultate, linii, favorite
const UiModule = (function () {

  const TIP_LABEL = { bus:'Autobuz', met:'Expres', tram:'Tramvai', trol:'Troleibuz' };
  const TIP_SHORT = { bus:'BUS',     met:'EXP',   tram:'TRAM',    trol:'TROL'      };
  let _stopToggleCounter = 0;

  // ── Helper: escape HTML ─────────────────────────────────────────────────────
  function esc(s) {
    return String(s || '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Helper: badge linie ─────────────────────────────────────────────────────
  function badgeHtml(lineId, type, size) {
    size = size || 44;
    const fs = size > 38 ? 15 : 12;
    return `<div class="line-badge ${esc(type)}" style="width:${size}px;height:${size}px;font-size:${fs}px">
      ${esc(lineId)}<div class="badge-sub">${esc(TIP_SHORT[type] || 'BUS')}</div>
    </div>`;
  }

  // ── Helper: stil tip pentru pill ────────────────────────────────────────────
  function tipStyle(type) {
    const map = {
      bus:  'background:var(--bus-bg);color:var(--bus-text)',
      met:  'background:var(--met-bg);color:var(--met-text)',
      tram: 'background:var(--tram-bg);color:var(--tram-text)',
      trol: 'background:var(--trol-bg);color:var(--trol-text)'
    };
    return map[type] || map.bus;
  }

  // ── Helper: lista opriri ─────────────────────────────────────────────────────
  function stopsHtml(stops, id) {
    let h = `<div class="stops-list" id="${id}">`;
    stops.forEach((stop, i) => {
      const first = i === 0, last = i === stops.length - 1;
      h += `<div class="stop-row">
        <div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0">
          <div class="stop-dot${first||last?' highlight':''}"></div>
          ${i < stops.length - 1 ? '<div class="stop-line"></div>' : ''}
        </div>
        <div class="stop-name${first||last?' active-stop':''}">${esc(stop.name)}</div>
        <div class="stop-time">${esc(ScheduleModule.toStr(stop.time))}</div>
      </div>`;
    });
    h += '</div>';
    return h;
  }

  function toggleStops(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle('open');
    const btn = document.getElementById('btn-' + id);
    if (btn) btn.textContent = el.classList.contains('open')
      ? '▲ Ascunde stații'
      : `▼ ${btn.dataset.label}`;
  }

  // ── Autocomplete ─────────────────────────────────────────────────────────────
  function setupAutocomplete(inputId, sugId, onSelect) {
    const input   = document.getElementById(inputId);
    const sugBox  = document.getElementById(sugId);
    let hideTimer = null;
    let activeIdx = -1;

    function showSugs(query) {
      if (!query || !query.trim()) { sugBox.classList.remove('open'); return; }
      const list = DataModule.getSuggestions(query, 10);
      activeIdx = -1;
      if (!list.length) { sugBox.classList.remove('open'); return; }
      sugBox.innerHTML = list.map(s =>
        `<div class="suggestion" data-val="${esc(s)}">${esc(s)}</div>`
      ).join('');
      sugBox.classList.add('open');
    }

    function getItems() { return sugBox.querySelectorAll('.suggestion'); }

    function select(val) {
      input.value = val;
      sugBox.classList.remove('open');
      onSelect(val);
    }

    input.addEventListener('focus', () => {
      clearTimeout(hideTimer);
      if (input.value.trim()) showSugs(input.value);
    });
    input.addEventListener('input', () => showSugs(input.value));
    input.addEventListener('blur',  () => {
      hideTimer = setTimeout(() => sugBox.classList.remove('open'), 200);
    });

    sugBox.addEventListener('mousedown', e => {
      const el = e.target.closest('.suggestion');
      if (!el) return;
      e.preventDefault();
      select(el.dataset.val);
    });

    input.addEventListener('keydown', e => {
      const items = getItems();
      if (!items.length || !sugBox.classList.contains('open')) {
        if (e.key === 'Enter') AppModule && AppModule.cauta();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle('focused', i === activeIdx));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
        items.forEach((el, i) => el.classList.toggle('focused', i === activeIdx));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const focused = activeIdx >= 0 ? items[activeIdx] : items[0];
        if (focused) select(focused.dataset.val);
        activeIdx = -1;
      } else if (e.key === 'Escape') {
        sugBox.classList.remove('open');
      }
    });
  }

  // ── Swap stații ──────────────────────────────────────────────────────────────
  function swap() {
    const fi = document.getElementById('from-input');
    const ti = document.getElementById('to-input');
    const tmp = fi.value;
    fi.value = ti.value;
    ti.value = tmp;
  }

  // ── Randare rezultate căutare ─────────────────────────────────────────────────
  function renderResults(result, from, to, nowMin, dayType, nearby) {
    const el = document.getElementById('results');
    const { direct, transfers } = result;

    const nearbyPill = (nearby && (nearby.from || nearby.to))
      ? '<span class="pill pill-nearby">În apropiere</span> '
      : '';

    let nearbyBanner = '';
    if (nearby && (nearby.from || nearby.to)) {
      const parts = [];
      if (nearby.from) parts.push(
        `<b>${esc(nearby.from.station)}</b> <span style="opacity:.7">(${nearby.from.dist} m față de „${esc(nearby.from.original)}")</span>`
      );
      if (nearby.to) parts.push(
        `<b>${esc(nearby.to.station)}</b> <span style="opacity:.7">(${nearby.to.dist} m față de „${esc(nearby.to.original)}")</span>`
      );
      nearbyBanner = `<div class="nearby-banner">${parts.join(' &middot; ')}</div>`;
    }

    if (!direct.length && !transfers.length) {
      let noRouteHtml = nearbyBanner;
      noRouteHtml += `<div class="empty-state">
        <div class="empty-icon">:(</div>
        Nu am găsit rute între <strong>${esc(from)}</strong> și <strong>${esc(to)}</strong>
        pentru intervalul ales.<br>Încearcă o altă oră sau tip de zi.
      </div>`;
      const deps = ScheduleModule.nextDepartures(from, nowMin, dayType, 8);
      if (deps.length) noRouteHtml += _nextDepsHtml(from, deps);
      el.innerHTML = noRouteHtml;
      return;
    }

    let html = nearbyBanner + '<div class="results-section-title">Rute recomandate</div>';

    // ── Rute directe
    let firstFuture = true;
    direct.forEach(r => {
      const sid    = `sl-${++_stopToggleCounter}`;
      const stops  = ScheduleModule.legStops(r.lineId, r.direction, r.fromIdx, r.toIdx, r.boardRank, dayType);
      const label  = `Stații (${stops.length})`;
      const isLate = !!r.late;

      let pill = '';
      let isBest = false;
      if (!isLate && firstFuture) {
        isBest = true; firstFuture = false;
        pill = '<span class="pill pill-green">Recomandat</span> ';
      } else if (isLate) {
        const ago = r.minsAgo === 1 ? '1 min în urmă' : `${r.minsAgo} min în urmă`;
        pill = `<span class="pill pill-red">&#9201; ${esc(ago)}</span> `;
      }

      const metaLine = isLate
        ? `Plecat ${r.minsAgo} min în urmă &middot; ${r.numStations} stații`
        : `Direct &middot; ${r.numStations} stații &middot; ${esc(TIP_LABEL[r.lineType] || 'Autobuz')}`;

      html += `<div class="result-card${isBest ? ' best' : ''}${isLate ? ' late-route' : ''}">
        ${pill || nearbyPill ? `<div>${pill}${nearbyPill}</div>` : ''}
        <div class="result-header">
          ${badgeHtml(r.lineId, r.lineType, 40)}
          <div class="result-body">
            <div class="result-title">${esc(from)} &rarr; ${esc(to)}</div>
            <div class="result-meta">${metaLine}</div>
          </div>
          <div class="result-right">
            <div class="result-duration">${r.duration} min</div>
            <div class="result-times">${esc(ScheduleModule.toStr(r.departure))} &ndash; ${esc(ScheduleModule.toStr(r.arrival))}</div>
          </div>
          <button class="fav-btn" onclick='UiModule.salvFav(${JSON.stringify(r.from)},${JSON.stringify(r.to)},${JSON.stringify(r.lineId)})' title="Salvează">&#9733;</button>
        </div>
        <button class="stops-toggle" id="btn-${sid}" data-label="${esc(label)}"
                onclick="UiModule.toggleStops('${sid}')">&#9660; ${esc(label)}</button>
        ${stopsHtml(stops, sid)}
      </div>`;
    });

    // ── Rute cu transfer
    transfers.forEach(r => {
      const sid1   = `sl-${++_stopToggleCounter}`;
      const sid2   = `sl-${++_stopToggleCounter}`;
      const stops1 = ScheduleModule.legStops(r.leg1.lineId, r.leg1.direction, r.leg1.fromIdx, r.leg1.toIdx, r.leg1.boardRank, dayType);
      const stops2 = ScheduleModule.legStops(r.leg2.lineId, r.leg2.direction, r.leg2.fromIdx, r.leg2.toIdx, r.leg2.boardRank, dayType);
      const lbl1   = `${r.leg1.lineId} (${stops1.length} stații)`;
      const lbl2   = `${r.leg2.lineId} (${stops2.length} stații)`;

      html += `<div class="result-card">
        <div style="margin-bottom:5px"><span class="pill pill-yellow">1 schimbare</span>${nearbyPill ? ` ${nearbyPill}` : ''}</div>
        <div class="result-header">
          <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0">
            ${badgeHtml(r.leg1.lineId, r.leg1.lineType, 36)}
            ${badgeHtml(r.leg2.lineId, r.leg2.lineType, 36)}
          </div>
          <div class="result-body">
            <div class="result-title">${esc(from)} &rarr; ${esc(to)}</div>
            <div class="result-meta">Schimb: <strong>${esc(r.hub)}</strong> &middot; ${r.hubWait} min așteptare</div>
            <div class="result-meta">${esc(r.leg1.lineId)}: ${esc(ScheduleModule.toStr(r.leg1.departure))} &ndash; ${esc(ScheduleModule.toStr(r.leg1.arrival))}</div>
            <div class="result-meta">${esc(r.leg2.lineId)}: ${esc(ScheduleModule.toStr(r.leg2.departure))} &ndash; ${esc(ScheduleModule.toStr(r.leg2.arrival))}</div>
          </div>
          <div class="result-right">
            <div class="result-duration">${r.total} min</div>
            <div class="result-times">${esc(ScheduleModule.toStr(r.leg1.departure))} &ndash; ${esc(ScheduleModule.toStr(r.leg2.arrival))}</div>
          </div>
          <button class="fav-btn" onclick='UiModule.salvFav(${JSON.stringify(r.leg1.from)},${JSON.stringify(r.leg2.to)},${JSON.stringify(r.leg1.lineId+"→"+r.leg2.lineId)})' title="Salvează">&#9733;</button>
        </div>
        <button class="stops-toggle" id="btn-${sid1}" data-label="${esc(lbl1)}"
                onclick="UiModule.toggleStops('${sid1}')">&#9660; ${esc(lbl1)}</button>
        ${stopsHtml(stops1, sid1)}
        <button class="stops-toggle" id="btn-${sid2}" data-label="${esc(lbl2)}"
                style="margin-top:6px"
                onclick="UiModule.toggleStops('${sid2}')">&#9660; ${esc(lbl2)}</button>
        ${stopsHtml(stops2, sid2)}
      </div>`;
    });

    el.innerHTML = html;
  }

  function _nextDepsHtml(station, deps) {
    const rows = deps.map(d =>
      `<div class="stop-row">
         ${badgeHtml(d.lineId, DataModule.getLineType(d.lineId), 36)}
         <div class="stop-name" style="padding-left:8px">
           ${esc(d.lineId)} · ${esc(d.direction === 'dus' ? 'dus' : 'întors')}
         </div>
         <div class="stop-time">${esc(ScheduleModule.toStr(d.time))}</div>
       </div>`
    ).join('');
    return `<div class="card" style="margin-top:12px">
      <div class="card-title">Plecări din ${esc(station)}</div>
      ${rows}
    </div>`;
  }

  // ── Randare tab Linii ─────────────────────────────────────────────────────────
  function renderLinii() {
    const el = document.getElementById('all-lines');
    const sorted = Object.keys(NETWORK_DATA).sort((a, b) => {
      const na = parseInt(a), nb = parseInt(b);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      if (!isNaN(na)) return -1;
      if (!isNaN(nb)) return  1;
      return a.localeCompare(b);
    });

    el.innerHTML = sorted.map(lineId => {
      const type = DataModule.getLineType(lineId);
      const dirs = NETWORK_DATA[lineId];
      let dirsHtml = '';

      for (const [dir, lineData] of Object.entries(dirs)) {
        const sts = lineData.stations.filter(s => (s.name || '').trim());
        const firstName = (sts[0]?.name  || '').trim();
        const lastName  = (sts[sts.length - 1]?.name || '').trim();
        const firstSt   = lineData.stations.find(s => (s.name || '').trim());
        let firstDep = '--:--', lastDep = '--:--', nTrips = 0;
        if (firstSt) {
          const times = ScheduleModule.flatten(firstSt, 'school');
          if (times.length) {
            firstDep = ScheduleModule.toStr(times[0]);
            lastDep  = ScheduleModule.toStr(times[times.length - 1]);
            nTrips   = times.length;
          }
        }
        const arrow = dir === 'dus' ? '&#8594;' : '&#8592;';
        dirsHtml += `<div style="margin-top:5px;font-size:12px;color:var(--muted)">
          ${arrow} <span style="color:var(--text);font-weight:500">${esc(firstName)} &rarr; ${esc(lastName)}</span>
          &middot; ${sts.length} stații &middot; ${nTrips} curse/zi
          <span style="font-variant-numeric:tabular-nums;font-size:11px;margin-left:4px">${esc(firstDep)}–${esc(lastDep)}</span>
        </div>`;
      }

      return `<div class="line-row">
        ${badgeHtml(lineId, type, 40)}
        <div class="line-info">
          <div class="line-name">
            <span class="tip-pill" style="${tipStyle(type)}">${esc(TIP_LABEL[type] || 'Autobuz')}</span>
            Linia ${esc(lineId)}
          </div>
          ${dirsHtml}
        </div>
      </div>`;
    }).join('');
  }

  // ── Favorite ──────────────────────────────────────────────────────────────────
  function renderFavs() {
    const favs = StorageModule.getFavs();
    const el   = document.getElementById('favs-list');
    if (!favs.length) {
      el.innerHTML = `<div class="empty-state">
        <div class="empty-icon">&#9733;</div>
        Nicio rută favorită.<br>Apasă steluța de lângă orice rută ca s-o salvezi.
      </div>`;
      return;
    }
    el.innerHTML = favs.map(f => `
      <div class="fav-item">
        <div>
          <div class="fav-label">${esc(f.from)} &rarr; ${esc(f.to)}</div>
          <div class="fav-sub">Linia ${esc(f.lines)} &middot; Salvat ${esc(f.date)}</div>
        </div>
        <div class="fav-actions">
          <button class="icon-btn" title="Caută ruta"
                  onclick='AppModule.loadFav(${JSON.stringify(f.from)},${JSON.stringify(f.to)})'>&#8594;</button>
          <button class="icon-btn danger" title="Șterge"
                  onclick='UiModule.stergeFav(${JSON.stringify(f.key)})'>&#10005;</button>
        </div>
      </div>`
    ).join('');
  }

  function salvFav(from, to, lines) {
    if (StorageModule.addFav(from, to, lines)) {
      alert('Rută salvată la favorite ★');
      renderFavs();
    } else {
      alert('Deja salvată!');
    }
  }

  function stergeFav(key) {
    StorageModule.removeFav(key);
    renderFavs();
  }

  // ── Tab switching ─────────────────────────────────────────────────────────────
  function showTab(name) {
    ['plan','favs','linii'].forEach(t => {
      const el = document.getElementById('card-' + t);
      if (el) el.style.display = t === name ? '' : 'none';
    });
    document.querySelectorAll('.nav-link').forEach(el => {
      el.classList.toggle('active', el.dataset.section === name);
    });
    const card = document.querySelector('.planner-card');
    if (card) card.classList.toggle('card-full', name !== 'plan');
    if (name === 'favs')  renderFavs();
    if (name === 'linii') renderLinii();
  }

  return {
    setupAutocomplete,
    swap,
    renderResults,
    renderFavs,
    renderLinii,
    salvFav,
    stergeFav,
    showTab,
    toggleStops
  };

})();
