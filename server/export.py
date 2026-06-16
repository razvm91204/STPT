# -*- coding: utf-8 -*-
"""
export.py — Generate network_data.js and stations_coords.js from SQLite.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.db import DB_PATH, get_db


def generate_network_data_js(db_path: str = None) -> str:
    """
    Read lines/line_stations/schedules from SQLite and return a JS string
    recreating the same structure as the original network_data.js.
    """
    conn = get_db(db_path or DB_PATH)
    try:
        # Fetch all active lines
        lines = conn.execute(
            "SELECT id FROM lines WHERE active = 1 ORDER BY id"
        ).fetchall()
        active_ids = {row["id"] for row in lines}

        # Bulk fetch all line_stations and schedules (avoids N+1 queries)
        all_ls = conn.execute(
            "SELECT line_id, direction, station_name, position FROM line_stations ORDER BY line_id, direction, position"
        ).fetchall()
        ls_index = {}
        for r in all_ls:
            if r["line_id"] not in active_ids:
                continue
            key = (r["line_id"], r["direction"])
            ls_index.setdefault(key, []).append(r["station_name"])

        all_scheds = conn.execute(
            "SELECT line_id, direction, station_name, day_type, schedule_json FROM schedules"
        ).fetchall()
        sched_index = {}
        for r in all_scheds:
            key = (r["line_id"], r["direction"], r["station_name"])
            sched_index.setdefault(key, {})[r["day_type"]] = json.loads(r["schedule_json"])

        network = {}
        for line_row in lines:
            line_id = line_row["id"]
            network[line_id] = {}
            directions = {k[1] for k in ls_index if k[0] == line_id}
            for direction in sorted(directions):
                stations_list = []
                for station_name in ls_index.get((line_id, direction), []):
                    schedule = sched_index.get((line_id, direction, station_name), {})
                    stations_list.append({"name": station_name, "schedule": schedule})
                network[line_id][direction] = {"stations": stations_list}

        js_content = (
            "const NETWORK_DATA = "
            + json.dumps(network, ensure_ascii=False, separators=(",", ":"))
            + ";"
        )
        return js_content
    finally:
        conn.close()


def generate_stations_coords_js(db_path: str = None) -> str:
    """
    Read stations from SQLite and return the stations_coords.js content.
    """
    conn = get_db(db_path or DB_PATH)
    try:
        rows = conn.execute(
            "SELECT name, lat, lon FROM stations ORDER BY name"
        ).fetchall()

        coords = {}
        for row in rows:
            coords[row["name"]] = [row["lat"], row["lon"]]

        js_content = (
            "// Generat automat de gen_coords.py — nu edita manual\n"
            "const STATIONS_COORDS = "
            + json.dumps(coords, ensure_ascii=False, separators=(",", ":"))
            + ";"
        )
        return js_content
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export DB to JS files")
    parser.add_argument(
        "--db-path", default=None,
        help=f"Path to SQLite DB (default: {DB_PATH})"
    )
    parser.add_argument(
        "--output-dir", default=".",
        help="Output directory for generated files (default: current directory)"
    )
    args = parser.parse_args()

    db_path = args.db_path or DB_PATH
    out_dir = args.output_dir

    print("Generating network_data.js ...")
    network_js = generate_network_data_js(db_path)
    network_path = os.path.join(out_dir, "network_data.js")
    with open(network_path, "w", encoding="utf-8") as f:
        f.write(network_js)
    print(f"  Written: {network_path}")

    print("Generating stations_coords.js ...")
    coords_js = generate_stations_coords_js(db_path)
    coords_path = os.path.join(out_dir, "stations_coords.js")
    with open(coords_path, "w", encoding="utf-8") as f:
        f.write(coords_js)
    print(f"  Written: {coords_path}")

    print("Export complete.")
