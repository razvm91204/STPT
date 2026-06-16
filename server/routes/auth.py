# -*- coding: utf-8 -*-
"""
auth.py — Authentication routes.

POST /api/auth/login
  Body: { "username": "...", "password": "..." }
  Returns: { "access_token": "...", "token_type": "bearer" }
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    from jose import jwt

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate a user and return a JWT access token."""
    import bcrypt as _bcrypt
    from server.db import get_db

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (body.username,)
        ).fetchone()
    finally:
        conn.close()

    valid = (
        row is not None
        and _bcrypt.checkpw(body.password.encode(), row["password_hash"].encode())
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": body.username})
    return JSONResponse({"access_token": token, "token_type": "bearer"})
