# -*- coding: utf-8 -*-
"""
import_coords.py — Update stations table with coords from stations_coords.js.

Reads stations_coords.js from the repo root and runs:
  UPDATE stations SET lat=?, lon=? WHERE name=?
for every station that has a real coordinate in the JS file.
Stations not in the JS file (48 unmatched) are left unchanged.

Usage: python server/import_coords.py
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.db import DB_PATH, get_db, init_db

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COORDS_JS = os.path.join(REPO_ROOT, 'stations_coords.js')


def load_coords(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'const STATIONS_COORDS\s*=\s*(\{[\s\S]*?\});', content)
    if not m:
        raise ValueError('Cannot parse STATIONS_COORDS from stations_coords.js')
    raw = re.sub(r',\s*([}\]])', r'\1', m.group(1))
    return json.loads(raw)


def main():
    print(f'Using DB: {DB_PATH}')
    init_db(DB_PATH)
    conn = get_db(DB_PATH)

    coords = load_coords(COORDS_JS)
    print(f'Coordonate in stations_coords.js: {len(coords)}')

    updated = 0
    skipped = 0
    not_found = 0

    try:
        for name, (lat, lon) in coords.items():
            existing = conn.execute('SELECT lat, lon FROM stations WHERE name=?', (name,)).fetchone()
            if existing is None:
                not_found += 1
                continue
            conn.execute('UPDATE stations SET lat=?, lon=? WHERE name=?', (lat, lon, name))
            updated += 1

        conn.commit()
    finally:
        conn.close()

    print(f'Actualizate:    {updated}')
    print(f'Negasite in DB: {not_found}')
    print(f'Total statii cu coord: {updated}')


if __name__ == '__main__':
    main()
