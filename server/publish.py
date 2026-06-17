"""Regenerates network_data.js and stations_coords.js from DB. Usage: python server/publish.py"""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.db import DB_PATH
from server.export import generate_stations_coords_js, generate_network_data_js

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def atomic_write(path, content):
    dir_ = os.path.dirname(path) or '.'
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix='.pub_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        shutil.move(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except: pass
        raise

atomic_write(os.path.join(REPO_ROOT, 'network_data.js'), generate_network_data_js(DB_PATH))
atomic_write(os.path.join(REPO_ROOT, 'stations_coords.js'), generate_stations_coords_js(DB_PATH))
print('Republished OK')
