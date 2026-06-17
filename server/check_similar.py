import sqlite3, os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect(os.environ.get('DB_PATH', './data/stpt.db'))
db.row_factory = sqlite3.Row

all_st = db.execute('SELECT name, lat, lon FROM stations ORDER BY name').fetchall()
zeros = [r for r in all_st if r['lat'] == 0 and r['lon'] == 0]
with_coords = [r for r in all_st if r['lat'] != 0 or r['lon'] != 0]

# Normalize: strip parens, uppercase, remove diacritics approx
def norm(s):
    s = re.sub(r'\(.*?\)', '', s).strip().upper()
    s = re.sub(r'\s+', ' ', s)
    return s

coord_norm = {norm(r['name']): r['name'] for r in with_coords}
zero_norm  = {norm(r['name']): r['name'] for r in zeros}

# Find where normalized names match
overlaps = set(coord_norm) & set(zero_norm)
print(f'Stații cu 0,0 care par duplicate dupa normalizare: {len(overlaps)}')
for n in sorted(overlaps):
    print(f'  cu coord: "{coord_norm[n]}"')
    print(f'  fara:     "{zero_norm[n]}"')
    print()

# Also show total stats again
print(f'Total: {len(all_st)} | Cu coord: {len(with_coords)} | Fara: {len(zeros)}')
