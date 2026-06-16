"""
Generează stations_coords.js cu coordonatele stațiilor STPT Timișoara.
Sursa: Overpass API (OpenStreetMap).
Rulare: python gen_coords.py  (din folderul D:\Projects\STPT)
"""
import json, re, unicodedata, urllib.request, urllib.parse, sys

NETWORK_JSON = 'stpt_orare/network.json'
OUT_JS       = 'stations_coords.js'
# Bounding box Timișoara (lat_min, lon_min, lat_max, lon_max)
BBOX = '45.65,21.10,45.85,21.40'

def normalize(name):
    if not name: return ''
    s = name.strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*[-–—]\s*', '-', s)
    s = re.sub(r'\(\s+', '(', s); s = re.sub(r'\s+\)', ')', s)
    s = s.lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[,.]', '', s)
    return s.strip()

# ── 1. Colectează toate numele unice din network.json ──────────────────────────
with open(NETWORK_JSON, encoding='utf-8') as f:
    network = json.load(f)

raw_names = {}          # norm → primul raw_name văzut
for line_id, dirs in network.items():
    for direction, ld in dirs.items():
        for st in ld['stations']:
            name = (st.get('name') or '').strip()
            if not name: continue
            n = normalize(name)
            if n not in raw_names:
                raw_names[n] = name

print(f'Stații unice în network.json: {len(raw_names)}')

# ── 2. Interogare Overpass ─────────────────────────────────────────────────────
query = f"""
[out:json][timeout:40];
(
  node["highway"="bus_stop"]({BBOX});
  node["public_transport"="stop_position"]({BBOX});
  node["public_transport"="platform"]({BBOX});
  node["railway"="tram_stop"]({BBOX});
);
out body;
"""
print('Interogare Overpass API...')
data = urllib.parse.urlencode({'data': query}).encode()
req  = urllib.request.Request('https://overpass-api.de/api/interpreter', data=data)
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
req.add_header('User-Agent', 'STPT-Timisoara-RouteApp/1.0')
try:
    with urllib.request.urlopen(req, timeout=45) as resp:
        osm = json.loads(resp.read().decode('utf-8'))
except Exception as e:
    print(f'Eroare Overpass: {e}'); sys.exit(1)

# norm_name → (lat, lon) – prima apariție per nume normalizat
osm_stops = {}
for el in osm['elements']:
    name = el.get('tags', {}).get('name', '')
    if not name: continue
    n = normalize(name)
    lat, lon = el.get('lat'), el.get('lon')
    if lat and lon and n not in osm_stops:
        osm_stops[n] = (lat, lon)

print(f'Stații OSM unice: {len(osm_stops)}')

# ── 3. Matching ────────────────────────────────────────────────────────────────
coords   = {}    # raw_name → (lat, lon)
unmatched = []

for norm, raw in raw_names.items():
    if norm in osm_stops:
        coords[raw] = osm_stops[norm]
    else:
        unmatched.append(raw)

print(f'Potrivite: {len(coords)}  |  Nepotrivite: {len(unmatched)}')
if unmatched:
    print('\nStații fără coordonate:')
    for s in sorted(unmatched):
        print(f'  {s}')

# ── 4. Scrie JS ────────────────────────────────────────────────────────────────
lines = ['// Generat automat de gen_coords.py — nu edita manual',
         'const STATIONS_COORDS = {']
for raw, (lat, lon) in sorted(coords.items(), key=lambda x: x[0]):
    lines.append(f'  {json.dumps(raw, ensure_ascii=False)}: [{lat:.6f},{lon:.6f}],')
lines.append('};')

with open(OUT_JS, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print(f'\nSalvat {OUT_JS} cu {len(coords)} intrări.')
