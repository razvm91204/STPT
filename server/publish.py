"""Regenerates network_data.js and stations_coords.js from DB. Usage: python server/publish.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.db import get_db, DB_PATH
from server.export import generate_stations_coords_js, generate_network_data_js

conn = get_db(DB_PATH)
try:
    generate_network_data_js(conn)
    generate_stations_coords_js(conn)
    print('Republished OK')
finally:
    conn.close()
