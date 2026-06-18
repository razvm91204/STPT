# -*- coding: utf-8 -*-
"""
auth.py — Authentication routes.

POST /api/auth/login
  Body: { "username": "...", "password": "..." }
  Returns: { "access_token": "...", "token_type": "bearer" }

Rate limited: 5 requests/minute per IP.
"""

from datetime import datetime, timedelta, timezone

import jwt as _jwt
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from server.limiter import limiter

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return _jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
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
