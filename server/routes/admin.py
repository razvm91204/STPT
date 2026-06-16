# -*- coding: utf-8 -*-
"""
admin.py — Admin API routes.

All routes are protected with JWT authentication and mounted under /api/admin.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from server.db import get_db

security = HTTPBearer()
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Decode the Bearer JWT and return the username (sub claim)."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise ValueError("no sub")
        return username
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# All routes on this router require a valid JWT automatically.
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/me")
async def me(username: str = Depends(get_current_user)):
    """Return the currently authenticated username."""
    return {"username": username}


# ── Pydantic models ─────────────────────────────────────────────────────────

class LineCreate(BaseModel):
    id: str
    type: str
    active: int = 1


class LineUpdate(BaseModel):
    type: str
    active: int


class StationCreate(BaseModel):
    name: str
    lat: float
    lon: float


class StationUpdate(BaseModel):
    name: Optional[str] = None
    lat: float
    lon: float


class StructureDirection(BaseModel):
    direction: str
    stations: List[str]


class StationAdd(BaseModel):
    station_name: str
    position: Optional[int] = None


# ── Lines CRUD ───────────────────────────────────────────────────────────────

@router.get("/lines")
async def list_lines():
    """List all lines."""
    db = get_db()
    try:
        rows = db.execute("SELECT id, type, active FROM lines ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("/lines", status_code=201)
async def create_line(body: LineCreate):
    """Create a new line."""
    db = get_db()
    try:
        existing = db.execute("SELECT id FROM lines WHERE id=?", (body.id,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Line '{body.id}' already exists")
        db.execute(
            "INSERT INTO lines (id, type, active) VALUES (?, ?, ?)",
            (body.id, body.type, body.active),
        )
        db.commit()
        return {"id": body.id, "type": body.type, "active": body.active}
    finally:
        db.close()


@router.put("/lines/{line_id}")
async def update_line(line_id: str, body: LineUpdate):
    """Update a line's type and active status."""
    db = get_db()
    try:
        row = db.execute("SELECT id FROM lines WHERE id=?", (line_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")
        db.execute(
            "UPDATE lines SET type=?, active=? WHERE id=?",
            (body.type, body.active, line_id),
        )
        db.commit()
        return {"id": line_id, "type": body.type, "active": body.active}
    finally:
        db.close()


@router.delete("/lines/{line_id}", status_code=204)
async def delete_line(line_id: str):
    """Delete a line and cascade-delete its stations and schedules."""
    db = get_db()
    try:
        row = db.execute("SELECT id FROM lines WHERE id=?", (line_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")
        db.execute("DELETE FROM line_stations WHERE line_id=?", (line_id,))
        db.execute("DELETE FROM schedules WHERE line_id=?", (line_id,))
        db.execute("DELETE FROM lines WHERE id=?", (line_id,))
        db.commit()
    finally:
        db.close()


# ── Stations CRUD ────────────────────────────────────────────────────────────

@router.get("/stations")
async def list_stations():
    """List all stations."""
    db = get_db()
    try:
        rows = db.execute("SELECT name, lat, lon FROM stations ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("/stations", status_code=201)
async def create_station(body: StationCreate):
    """Create a new station."""
    db = get_db()
    try:
        existing = db.execute("SELECT name FROM stations WHERE name=?", (body.name,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Station '{body.name}' already exists")
        db.execute(
            "INSERT INTO stations (name, lat, lon) VALUES (?, ?, ?)",
            (body.name, body.lat, body.lon),
        )
        db.commit()
        return {"name": body.name, "lat": body.lat, "lon": body.lon}
    finally:
        db.close()


@router.put("/stations/{station_name}")
async def update_station(station_name: str, body: StationUpdate):
    """Update a station. If body.name differs, rename across line_stations and schedules."""
    db = get_db()
    try:
        row = db.execute("SELECT name FROM stations WHERE name=?", (station_name,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Station '{station_name}' not found")

        new_name = body.name if body.name is not None else station_name

        if new_name != station_name:
            # Check target name doesn't already exist
            conflict = db.execute("SELECT name FROM stations WHERE name=?", (new_name,)).fetchone()
            if conflict:
                raise HTTPException(status_code=409, detail=f"Station '{new_name}' already exists")
            # Cascade rename
            db.execute(
                "UPDATE line_stations SET station_name=? WHERE station_name=?",
                (new_name, station_name),
            )
            db.execute(
                "UPDATE schedules SET station_name=? WHERE station_name=?",
                (new_name, station_name),
            )
            db.execute(
                "UPDATE stations SET name=?, lat=?, lon=? WHERE name=?",
                (new_name, body.lat, body.lon, station_name),
            )
        else:
            db.execute(
                "UPDATE stations SET lat=?, lon=? WHERE name=?",
                (body.lat, body.lon, station_name),
            )
        db.commit()
        return {"name": new_name, "lat": body.lat, "lon": body.lon}
    finally:
        db.close()


@router.delete("/stations/{station_name}", status_code=204)
async def delete_station(station_name: str):
    """Delete a station."""
    db = get_db()
    try:
        row = db.execute("SELECT name FROM stations WHERE name=?", (station_name,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Station '{station_name}' not found")
        db.execute("DELETE FROM stations WHERE name=?", (station_name,))
        db.commit()
    finally:
        db.close()


# ── Line structure ───────────────────────────────────────────────────────────

@router.get("/lines/{line_id}/structure")
async def get_line_structure(line_id: str):
    """Return the station list for both directions of a line."""
    db = get_db()
    try:
        row = db.execute("SELECT id FROM lines WHERE id=?", (line_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")

        rows = db.execute(
            "SELECT direction, station_name FROM line_stations WHERE line_id=? ORDER BY direction, position",
            (line_id,),
        ).fetchall()

        result: dict = {"dus": [], "intors": []}
        for r in rows:
            d = r["direction"]
            if d not in result:
                result[d] = []
            result[d].append(r["station_name"])
        return result
    finally:
        db.close()


@router.put("/lines/{line_id}/structure")
async def replace_line_structure(line_id: str, body: StructureDirection):
    """Replace the entire station list for one direction."""
    db = get_db()
    try:
        row = db.execute("SELECT id FROM lines WHERE id=?", (line_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")

        db.execute(
            "DELETE FROM line_stations WHERE line_id=? AND direction=?",
            (line_id, body.direction),
        )
        for i, sname in enumerate(body.stations):
            db.execute(
                "INSERT INTO line_stations (line_id, direction, station_name, position) VALUES (?, ?, ?, ?)",
                (line_id, body.direction, sname, i),
            )
        db.commit()
        return {"line_id": line_id, "direction": body.direction, "stations": body.stations}
    finally:
        db.close()


@router.post("/lines/{line_id}/structure/{direction}/add", status_code=201)
async def add_station_to_structure(line_id: str, direction: str, body: StationAdd):
    """Add a station to a direction, at a given position or at the end."""
    db = get_db()
    try:
        row = db.execute("SELECT id FROM lines WHERE id=?", (line_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")

        existing = db.execute(
            "SELECT position FROM line_stations WHERE line_id=? AND direction=? AND station_name=?",
            (line_id, direction, body.station_name),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Station '{body.station_name}' already in {direction}",
            )

        max_pos_row = db.execute(
            "SELECT COALESCE(MAX(position), -1) as max_pos FROM line_stations WHERE line_id=? AND direction=?",
            (line_id, direction),
        ).fetchone()
        max_pos = max_pos_row["max_pos"]

        if body.position is None:
            pos = max_pos + 1
        else:
            pos = body.position
            # Shift existing stations at or after this position
            db.execute(
                "UPDATE line_stations SET position=position+1 WHERE line_id=? AND direction=? AND position>=?",
                (line_id, direction, pos),
            )

        db.execute(
            "INSERT INTO line_stations (line_id, direction, station_name, position) VALUES (?, ?, ?, ?)",
            (line_id, direction, body.station_name, pos),
        )
        db.commit()
        return {"line_id": line_id, "direction": direction, "station_name": body.station_name, "position": pos}
    finally:
        db.close()


@router.delete("/lines/{line_id}/structure/{direction}/{station_name}", status_code=204)
async def remove_station_from_structure(line_id: str, direction: str, station_name: str):
    """Remove a station from a direction."""
    db = get_db()
    try:
        row = db.execute(
            "SELECT position FROM line_stations WHERE line_id=? AND direction=? AND station_name=?",
            (line_id, direction, station_name),
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Station '{station_name}' not found in line '{line_id}' direction '{direction}'",
            )
        db.execute(
            "DELETE FROM line_stations WHERE line_id=? AND direction=? AND station_name=?",
            (line_id, direction, station_name),
        )
        db.commit()
    finally:
        db.close()
