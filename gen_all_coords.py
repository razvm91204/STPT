"""
gen_all_coords.py — Geocodes ALL stations from network.json + graphical_lines_data.json.
Uses Overpass API. Tries two match strategies per station:
  1. Exact normalized name
  2. Normalized name without parenthetical qualifier

Usage: python gen_all_coords.py
"""
import json, os, re, unicodedata, urllib.request, urllib.parse, sys

NETWORK_JSON        = 'stpt_orare/network.json'
GRAPHICAL_JSON      = 'server/graphical_lines_data.json'
OUT_JS              = 'stations_coords.js'
BBOX                = '45.65,21.10,45.85,21.40'

sys.stdout.reconfigure(encoding='utf-8')

def normalize(name):
    s = name.strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*[-–—]\s*', '-', s)
    s = re.sub(r'\(\s+', '(', s)
    s = re.sub(r'\s+\)', ')', s)
    s = s.lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[,.]', '', s)
    return s.strip()

def normalize_no_parens(name):
    return normalize(re.sub(r'\(.*?\)', '', name))

_ABBR = [
    (r'\bb-?dul\b', 'bulevardul'),
    (r'\bbd\.?\b', 'bulevardul'),
    (r'\bstr\.?\b', 'strada'),
    (r'\bp-?ta\b', 'piata'),
    (r'\bc\.\b', 'calea'),
]

# STPT uses abbreviated/different names; map normalized base form → OSM normalized base form
# These were found by comparing unmatched STPT names against actual OSM stop names in Timișoara
_ALIASES = {
    # Piete
    'piata a mocioni':                'piata alexandru mocioni',
    'piata mocioni':                  'piata alexandru mocioni',
    'p-ta a mocioni':                 'piata alexandru mocioni',
    'p-ta mocioni':                   'piata alexandru mocioni',
    'piata v economu':                'piata virgil economu',
    'p-ta v economu':                 'piata virgil economu',
    'piata huniade':                  'piata iancu huniade',
    'piata n balcescu':               'piata nicolae balcescu',
    # Bulevarde
    'bd iuliu maniu':                 'piata iuliu maniu',
    'b-dul iuliu maniu':              'piata iuliu maniu',
    'bd regele carol i':              'regele carol i',
    'b-dul regele carol i':           'regele carol i',
    'b-dul regele carol l':           'regele carol i',
    'b-dul ion c bratianu':           'bd ic bratianu',
    'bulevardul ion c bratianu':      'bd ic bratianu',
    # Calea Brancoveanu variants
    'c brancoveanu':                  'constantin brancoveanu',
    'brancoveanu':                    'constantin brancoveanu',
    # Institutii
    'prefectura jud timis':           'prefectura',
    'prefectura judtimis':            'prefectura',
    'politia judtimis':               'politia jud timis',
    'politia judetimis':              'politia jud timis',
    'colegiul national banatean':     'colegiul banatean',
    'comlexul studentesc':            'complexul studentesc',
    # Transport / puncte
    'j h pestalozzi':                 'pestalozzi',
    'jh pestalozzi':                  'pestalozzi',
    'meteo':                          'statia meteo',
    'batm':                           'batma',
    'bastionul maria tereza':         'bastion',
    'hornbach':                       'hornbach-buziasului',
    'parcul c sylva':                 'parc carmen sylva',
    'pasaj jiul':                     'jiul',
    'pasajul jiul':                   'jiul',
    'uzinei parc':                    'uzinei',
    'intrare rudicica':               'rudicica intrare',
    # Alte locatii
    'bd circumvalatiunii':            'circumvalatiunii',
    'bulevardul circumvalatiunii':    'circumvalatiunii',
    'titeica':                        'ghtiteica',
    'constantin nottara':             'ci nottara',
    'vuk karadjici':                  'vuk karadzic',
    'v simionescu':                   'virgil simionescu',
    'vox':                            'vox park',
    'iulius mall':                    'iulius town',
    'rudolf walter':                  'rudolf water',
    'martir c popescu':               'martir cornel popescu',
    'maresal c prezan':               'strada maresal constantin prezan',
    'maresalc prezan':                'strada maresal constantin prezan',
    'cbrancoveanu':                   'constantin brancoveanu',  # no space: C.BRANCOVEANU
    'politia judetului timis':        'politia jud timis',
}

def normalize_expanded(name):
    s = normalize_no_parens(name)
    for pat, repl in _ABBR:
        s = re.sub(pat, repl, s)
    return s.strip()

def normalize_aliased(name):
    s = normalize_no_parens(name)
    if s in _ALIASES:
        return _ALIASES[s]
    # Also try after abbreviation expansion
    s2 = normalize_expanded(name)
    return _ALIASES.get(s2, s2)

# ── Collect all unique station names ──────────────────────────────────────────
raw_names = {}   # norm → first raw name seen

def collect_from_network(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    for line_id, dirs in data.items():
        for direction, ddata in dirs.items():
            stations = ddata.get('stations', [])
            for st in (stations if isinstance(stations, list) else []):
                name = (st.get('name') or '').strip()
                if not name: continue
                n = normalize(name)
                if n not in raw_names:
                    raw_names[n] = name

def collect_from_graphical(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    for line_id, dirs in data.items():
        for direction, dlist in dirs.items():
            for st in dlist:
                name = (st.get('name') or '').strip()
                if not name: continue
                n = normalize(name)
                if n not in raw_names:
                    raw_names[n] = name

collect_from_network(NETWORK_JSON)
collect_from_graphical(GRAPHICAL_JSON)
print(f'Stații unice totale: {len(raw_names)}')

# ── Query Overpass ─────────────────────────────────────────────────────────────
query = f"""
[out:json][timeout:60];
(
  node["highway"="bus_stop"]({BBOX});
  node["public_transport"="stop_position"]({BBOX});
  node["public_transport"="platform"]({BBOX});
  node["railway"="tram_stop"]({BBOX});
);
out body;
"""
CACHE = '_osm_cache.json'
if os.path.exists(CACHE):
    print(f'Folosesc cache: {CACHE}')
    with open(CACHE, encoding='utf-8') as f:
        osm = json.load(f)
else:
    print('Interogare Overpass API...')
    data = urllib.parse.urlencode({'data': query}).encode()
    req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=data)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.add_header('User-Agent', 'STPT-Timisoara-RouteApp/1.0')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            osm = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'Eroare Overpass: {e}')
        sys.exit(1)
    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump(osm, f)
    print(f'Cache salvat: {CACHE}')

# Build OSM lookup: norm → (lat, lon)
osm_stops = {}
osm_stops_no_parens = {}
osm_stops_expanded = {}
for el in osm['elements']:
    name = el.get('tags', {}).get('name', '')
    if not name: continue
    lat, lon = el.get('lat'), el.get('lon')
    if not lat or not lon: continue
    n = normalize(name)
    if n not in osm_stops:
        osm_stops[n] = (lat, lon)
    n2 = normalize_no_parens(name)
    if n2 not in osm_stops_no_parens:
        osm_stops_no_parens[n2] = (lat, lon)
    n3 = normalize_expanded(name)
    if n3 not in osm_stops_expanded:
        osm_stops_expanded[n3] = (lat, lon)

print(f'Stații OSM unice (exact): {len(osm_stops)}')

# ── Match ──────────────────────────────────────────────────────────────────────
coords = {}
unmatched = []

for norm, raw in raw_names.items():
    if norm in osm_stops:
        coords[raw] = osm_stops[norm]
    elif normalize_no_parens(raw) in osm_stops_no_parens:
        coords[raw] = osm_stops_no_parens[normalize_no_parens(raw)]
    elif normalize_expanded(raw) in osm_stops_expanded:
        coords[raw] = osm_stops_expanded[normalize_expanded(raw)]
    elif normalize_aliased(raw) in osm_stops:
        coords[raw] = osm_stops[normalize_aliased(raw)]
    else:
        unmatched.append(raw)

# Fallback: stations sharing same base name (without qualifier) get same coords as matched variant
base_coords = {}
for raw, (lat, lon) in coords.items():
    for key in (normalize_no_parens(raw), normalize_aliased(raw)):
        if key not in base_coords:
            base_coords[key] = (lat, lon)

still_unmatched = []
for raw in unmatched:
    base = normalize_no_parens(raw)
    alias = normalize_aliased(raw)
    if base in base_coords:
        coords[raw] = base_coords[base]
    elif alias in base_coords:
        coords[raw] = base_coords[alias]
    else:
        still_unmatched.append(raw)
unmatched = still_unmatched

print(f'\nPotrivite: {len(coords)}  |  Nepotrivite: {len(unmatched)}')
if unmatched:
    print('\nStații fără coordonate:')
    for s in sorted(unmatched):
        print(f'  {s}')

# ── Write JS ───────────────────────────────────────────────────────────────────
lines_js = ['// Generat automat de gen_all_coords.py — nu edita manual',
            'const STATIONS_COORDS = {']
for raw, (lat, lon) in sorted(coords.items(), key=lambda x: x[0]):
    lines_js.append(f'  {json.dumps(raw, ensure_ascii=False)}: [{lat:.6f},{lon:.6f}],')
lines_js.append('};')

with open(OUT_JS, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines_js) + '\n')

print(f'\nSalvat {OUT_JS} cu {len(coords)} intrări.')
