# -*- coding: utf-8 -*-
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "./data/stpt.db")

CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lines (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS stations (
  name TEXT PRIMARY KEY,
  lat REAL,
  lon REAL
);

CREATE TABLE IF NOT EXISTS line_stations (
  line_id TEXT NOT NULL,
  direction TEXT NOT NULL,
  station_name TEXT NOT NULL,
  position INTEGER NOT NULL,
  PRIMARY KEY (line_id, direction, station_name)
);

CREATE TABLE IF NOT EXISTS schedules (
  line_id TEXT NOT NULL,
  direction TEXT NOT NULL,
  station_name TEXT NOT NULL,
  day_type TEXT NOT NULL,
  schedule_json TEXT NOT NULL,
  PRIMARY KEY (line_id, direction, station_name, day_type)
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def get_db(db_path: str = None) -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory set to sqlite3.Row."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(db_path: str = None) -> None:
    """Create all tables if they don't exist."""
    conn = get_db(db_path)
    try:
        conn.executescript(CREATE_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
