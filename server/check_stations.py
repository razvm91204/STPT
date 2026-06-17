import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect(os.environ.get('DB_PATH', './data/stpt.db'))
db.row_factory = sqlite3.Row

all_st = db.execute('SELECT name, lat, lon FROM stations ORDER BY name').fetchall()
zeros = [r for r in all_st if r['lat'] == 0 and r['lon'] == 0]
with_coords = [r for r in all_st if r['lat'] != 0 or r['lon'] != 0]

print(f'Total statii: {len(all_st)}')
print(f'Cu coordonate: {len(with_coords)}')
print(f'Cu 0,0 (fara coord): {len(zeros)}')

# Statii cu 0,0 care NU exista cu coordonate reale
zero_names = {r['name'] for r in zeros}
coord_names = {r['name'] for r in with_coords}
only_zero = zero_names - coord_names
also_has_coord = zero_names & coord_names

print(f'\nDin cele cu 0,0:')
print(f'  Doar 0,0 (no real coord): {len(only_zero)}')
print(f'  Exista si cu coord reale (DUPLICATE!): {len(also_has_coord)}')
if also_has_coord:
    for n in sorted(also_has_coord)[:10]:
        real = next(r for r in with_coords if r['name'] == n)
        print(f'    {repr(n)} -> ({real["lat"]}, {real["lon"]})')

# Top lines that reference zero-stations
ls = db.execute(
    'SELECT line_id, direction, station_name FROM line_stations WHERE station_name IN ({})'.format(
        ','.join('?' * len(only_zero))
    ), list(only_zero)
).fetchall()
from collections import Counter
by_line = Counter(f'{r["line_id"]}/{r["direction"]}' for r in ls)
print(f'\nLinii care referencieaza statii fara coord: {len(by_line)}')
for k, v in sorted(by_line.items()):
    print(f'  {k}: {v} statii')
