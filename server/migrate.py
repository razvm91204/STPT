# -*- coding: utf-8 -*-
"""
migrate.py — Import network.json + stations_coords.js into SQLite.

Usage:
  python server/migrate.py                  # import all data
  python server/migrate.py --create-admin   # also prompt for admin credentials
"""

import argparse
import getpass
import json
import os
import re
import sys

# Allow running from repo root as: python server/migrate.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.db import DB_PATH, get_db, init_db

TRAM_IDS = {"1", "2", "4", "7", "8", "9"}
MET_IDS = {"E1", "E2", "E3", "E4", "E4B", "E6", "E7", "E8"}

NETWORK_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "stpt_orare", "network.json"
)
STATIONS_COORDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "stations_coords.js"
)


def get_line_type(line_id: str) -> str:
    if line_id in TRAM_IDS:
        return "tram"
    if line_id in MET_IDS:
        return "met"
    return "bus"


def import_network(conn, network_path: str) -> None:
    print(f"Reading {network_path} ...")
    with open(network_path, encoding="utf-8") as f:
        network = json.load(f)

    cursor = conn.cursor()
    lines_inserted = 0
    stations_inserted = 0
    schedules_inserted = 0

    for line_id, directions in network.items():
        line_type = get_line_type(line_id)
        cursor.execute(
            "INSERT OR REPLACE INTO lines (id, type, active) VALUES (?, ?, 1)",
            (line_id, line_type)
        )
        lines_inserted += 1

        for direction, direction_data in directions.items():
            stations = direction_data.get("stations", [])
            for position, station_obj in enumerate(stations):
                station_name = station_obj.get("name", "")
                if not station_name:
                    continue

                # Insert into line_stations
                cursor.execute(
                    """INSERT OR REPLACE INTO line_stations
                       (line_id, direction, station_name, position)
                       VALUES (?, ?, ?, ?)""",
                    (line_id, direction, station_name, position)
                )
                stations_inserted += 1

                # Insert schedules per day_type
                schedule = station_obj.get("schedule", {})
                for day_type, hours_dict in schedule.items():
                    schedule_json = json.dumps(hours_dict, ensure_ascii=False)
                    cursor.execute(
                        """INSERT OR REPLACE INTO schedules
                           (line_id, direction, station_name, day_type, schedule_json)
                           VALUES (?, ?, ?, ?, ?)""",
                        (line_id, direction, station_name, day_type, schedule_json)
                    )
                    schedules_inserted += 1

    conn.commit()
    print(f"  Lines inserted/updated:          {lines_inserted}")
    print(f"  Line-station rows inserted:      {stations_inserted}")
    print(f"  Schedule rows inserted:          {schedules_inserted}")


def import_stations_coords(conn, coords_path: str) -> None:
    print(f"Reading {coords_path} ...")
    content = open(coords_path, encoding="utf-8").read()
    match = re.search(r"const STATIONS_COORDS\s*=\s*(\{[\s\S]*?\});", content)
    if not match:
        print("ERROR: Could not parse STATIONS_COORDS from stations_coords.js", file=sys.stderr)
        sys.exit(1)

    # Remove trailing commas before closing braces/brackets (JS allows them, JSON doesn't)
    raw = re.sub(r",\s*([}\]])", r"\1", match.group(1))
    data = json.loads(raw)
    cursor = conn.cursor()
    count = 0
    for name, coords in data.items():
        lat, lon = coords[0], coords[1]
        cursor.execute(
            "INSERT OR REPLACE INTO stations (name, lat, lon) VALUES (?, ?, ?)",
            (name, lat, lon)
        )
        count += 1

    conn.commit()
    print(f"  Stations inserted/updated: {count}")


def create_admin(conn) -> None:
    try:
        from passlib.hash import bcrypt
    except ImportError:
        print("ERROR: passlib not installed. Run: pip install passlib[bcrypt]", file=sys.stderr)
        sys.exit(1)

    print("\n--- Create Admin User ---")
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.", file=sys.stderr)
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    password_hash = bcrypt.hash(password)
    conn.execute(
        """INSERT INTO users (username, password_hash) VALUES (?, ?)
           ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash""",
        (username, password_hash)
    )
    conn.commit()
    print(f"Admin user '{username}' created/updated successfully.")


def main():
    parser = argparse.ArgumentParser(description="Migrate STPT data to SQLite")
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Prompt for admin credentials and insert into users table"
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help=f"Path to SQLite DB (default: {DB_PATH})"
    )
    args = parser.parse_args()

    db_path = args.db_path or DB_PATH

    # Ensure parent directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"Created directory: {db_dir}")

    print(f"Using DB: {db_path}")
    init_db(db_path)
    print("Schema initialized.")

    conn = get_db(db_path)
    try:
        import_network(conn, NETWORK_JSON_PATH)
        import_stations_coords(conn, STATIONS_COORDS_PATH)

        if args.create_admin:
            create_admin(conn)
    finally:
        conn.close()

    print("\nMigration complete.")


if __name__ == "__main__":
    main()
