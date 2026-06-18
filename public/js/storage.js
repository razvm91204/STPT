'use strict';
// StorageModule – favorite în localStorage
const StorageModule = (function () {
  const KEY = 'stpt_favs_v2';

  function getFavs() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); }
    catch { return []; }
  }

  function _save(favs) {
    localStorage.setItem(KEY, JSON.stringify(favs));
  }

  // Returnează true dacă a fost adăugat, false dacă exista deja
  function addFav(from, to, lines) {
    const favs = getFavs();
    const key  = `${from}|${to}|${lines}`;
    if (favs.find(f => f.key === key)) return false;
    favs.push({ key, from, to, lines, date: new Date().toLocaleDateString('ro-RO') });
    _save(favs);
    return true;
  }

  function removeFav(key) {
    _save(getFavs().filter(f => f.key !== key));
  }

  return { getFavs, addFav, removeFav };
})();
