# -*- coding: utf-8 -*-
"""
import_graphical_lines.py — Import routes + schedules from graphical_lines_data.json.

Populates lines 16, 33, 40, 46, E4B, E8 whose station names are graphical
(image-based) and therefore could not be extracted from PDFs via text methods.

Usage:
  python server/import_graphical_lines.py [--dry-run]
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.db import DB_PATH, get_db, init_db
from server.export import generate_network_data_js, generate_stations_coords_js

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(REPO_ROOT, "server", "graphical_lines_data.json")

LINE_TYPES = {
    "16": "bus", "33": "bus", "40": "bus", "46": "bus",
    "E4B": "express", "E8": "express",
}


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("[DRY RUN] No changes will be written.")

    print(f"Loading {JSON_PATH} ...")
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    db_path = DB_PATH
    init_db(db_path)
    conn = get_db(db_path)
    cursor = conn.cursor()

    total_stations = 0
    total_schedules = 0

    try:
        for line_id in sorted(data):
            if not dry_run:
                cursor.execute(
                    "INSERT OR IGNORE INTO lines (id, type, active) VALUES (?, ?, 1)",
                    (line_id, LINE_TYPES.get(line_id, "bus")),
                )

            for direction, stations in data[line_id].items():
                ls_count = 0
                sched_count = 0

                for pos, st in enumerate(stations):
                    name = st["name"].strip()
                    if not name:
                        continue

                    if not dry_run:
                        cursor.execute(
                            "INSERT OR IGNORE INTO stations (name, lat, lon) VALUES (?, 0, 0)",
                            (name,),
                        )
                        cursor.execute(
                            "INSERT OR REPLACE INTO line_stations "
                            "(line_id, direction, station_name, position) VALUES (?, ?, ?, ?)",
                            (line_id, direction, name, pos),
                        )
                    ls_count += 1

                    for day_type, hours_dict in st.get("schedule", {}).items():
                        if not hours_dict:
                            continue
                        if not dry_run:
                            cursor.execute(
                                "INSERT OR REPLACE INTO schedules "
                                "(line_id, direction, station_name, day_type, schedule_json) "
                                "VALUES (?, ?, ?, ?, ?)",
                                (line_id, direction, name, day_type,
                                 json.dumps(hours_dict, ensure_ascii=False)),
                            )
                        sched_count += 1

                print(f"  {line_id}/{direction}: {ls_count} statii, {sched_count} orare")
                total_stations += ls_count
                total_schedules += sched_count

        if not dry_run:
            conn.commit()
            print(f"\nImport complet: {total_stations} statii, {total_schedules} orare.")

            print("\nPublicam network_data.js ...")
            network_js = generate_network_data_js(db_path)
            coords_js = generate_stations_coords_js(db_path)
            with open(os.path.join(REPO_ROOT, "network_data.js"), "w", encoding="utf-8") as f:
                f.write(network_js)
            with open(os.path.join(REPO_ROOT, "stations_coords.js"), "w", encoding="utf-8") as f:
                f.write(coords_js)
            print("Publicare completa.")
        else:
            print(f"\n[DRY RUN] Ar fi importat: {total_stations} statii, {total_schedules} orare.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
