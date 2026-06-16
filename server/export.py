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

        network = {}

        for line_row in lines:
            line_id = line_row["id"]
            network[line_id] = {}

            # Fetch directions for this line
            directions = conn.execute(
                """SELECT DISTINCT direction FROM line_stations
                   WHERE line_id = ? ORDER BY direction""",
                (line_id,)
            ).fetchall()

            for dir_row in directions:
                direction = dir_row["direction"]

                # Fetch ordered stations for this line+direction
                station_rows = conn.execute(
                    """SELECT station_name FROM line_stations
                       WHERE line_id = ? AND direction = ?
                       ORDER BY position""",
                    (line_id, direction)
                ).fetchall()

                stations_list = []
                for st_row in station_rows:
                    station_name = st_row["station_name"]

                    # Fetch schedules for this station
                    sched_rows = conn.execute(
                        """SELECT day_type, schedule_json FROM schedules
                           WHERE line_id = ? AND direction = ? AND station_name = ?""",
                        (line_id, direction, station_name)
                    ).fetchall()

                    schedule = {}
                    for sched_row in sched_rows:
                        schedule[sched_row["day_type"]] = json.loads(
                            sched_row["schedule_json"]
                        )

                    stations_list.append({
                        "name": station_name,
                        "schedule": schedule
                    })

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
