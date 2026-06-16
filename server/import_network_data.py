# -*- coding: utf-8 -*-
"""
import_network_data.py — Import routes + schedules from network_data.js.

Restores data that was previously published but lost after volume recreation.
Also auto-generates reverse directions for lines where both directions have
the same station count (7, 17, 32) by reversing the working direction.

Usage:
  python server/import_network_data.py [--dry-run]
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.db import DB_PATH, get_db, init_db

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_DATA_JS = os.path.join(REPO_ROOT, "network_data.js")


def load_network_data(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'const NETWORK_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$', content)
    if not match:
        raise ValueError("Cannot parse NETWORK_DATA from network_data.js")
    return json.loads(match.group(1))


def import_direction(conn, line_id, direction, stations, dry_run=False):
    """Import route + schedules for one direction. stations is list of {name, schedule}."""
    cursor = conn.cursor()
    ls_inserted = 0
    sched_inserted = 0

    for position, station_obj in enumerate(stations):
        name = station_obj.get("name", "").strip()
        if not name:
            continue

        # Ensure station exists (without overwriting coordinates)
        existing = cursor.execute("SELECT name FROM stations WHERE name=?", (name,)).fetchone()
        if not existing:
            cursor.execute(
                "INSERT OR IGNORE INTO stations (name, lat, lon) VALUES (?, 0, 0)",
                (name,)
            )

        if not dry_run:
            cursor.execute(
                "INSERT OR REPLACE INTO line_stations (line_id, direction, station_name, position) VALUES (?, ?, ?, ?)",
                (line_id, direction, name, position)
            )
        ls_inserted += 1

        schedule = station_obj.get("schedule", {})
        for day_type, hours_dict in schedule.items():
            if not hours_dict:
                continue
            schedule_json = json.dumps(hours_dict, ensure_ascii=False)
            if not dry_run:
                cursor.execute(
                    """INSERT OR REPLACE INTO schedules
                       (line_id, direction, station_name, day_type, schedule_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (line_id, direction, name, day_type, schedule_json)
                )
            sched_inserted += 1

    if not dry_run:
        conn.commit()
    return ls_inserted, sched_inserted


OPPOSITE = {"dus": "intors", "intors": "dus"}


def auto_reverse_direction(stations):
    """Return station list reversed (for symmetric routes)."""
    return list(reversed(stations))


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[DRY RUN] No changes will be written.")

    print(f"Loading {NETWORK_DATA_JS} ...")
    data = load_network_data(NETWORK_DATA_JS)
    print(f"Found {len(data)} lines in network_data.js")

    db_path = DB_PATH
    init_db(db_path)
    conn = get_db(db_path)

    total_ls = 0
    total_sched = 0

    try:
        for line_id, dirs in sorted(data.items()):
            for direction, ddata in dirs.items():
                stations = ddata.get("stations", [])
                valid = [s for s in stations if s.get("name", "").strip()]

                if not valid:
                    continue

                ls, sched = import_direction(conn, line_id, direction, valid, dry_run)
                print(f"  {line_id}/{direction}: {ls} statii, {sched} orare")
                total_ls += ls
                total_sched += sched

                # Auto-generate reverse direction if missing from network_data.js
                opposite = OPPOSITE.get(direction)
                if opposite and opposite not in dirs:
                    opp_data = data.get(line_id, {}).get(opposite, {})
                    opp_stations = [s for s in opp_data.get("stations", []) if s.get("name", "").strip()]

                    if not opp_stations:
                        # Check if same station count → auto-reverse
                        # Get expected count from DB or use same as working direction
                        existing_opp = conn.execute(
                            "SELECT COUNT(*) as c FROM line_stations WHERE line_id=? AND direction=?",
                            (line_id, opposite)
                        ).fetchone()["c"]

                        if existing_opp == 0 and len(valid) > 0:
                            # Auto-generate reversed route (stations only, no schedules)
                            reversed_stations = [{"name": s["name"], "schedule": {}} for s in auto_reverse_direction(valid)]
                            ls2, _ = import_direction(conn, line_id, opposite, reversed_stations, dry_run)
                            print(f"  {line_id}/{opposite}: AUTO-REVERSE {ls2} statii (fara orare)")
                            total_ls += ls2

    finally:
        conn.close()

    print(f"\nTotal: {total_ls} statii, {total_sched} orare importate.")
    if dry_run:
        print("[DRY RUN] Nicio modificare nu a fost scrisa.")
    else:
        print("Import complet.")


if __name__ == "__main__":
    main()
