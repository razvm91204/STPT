# -*- coding: utf-8 -*-
"""
admin.py — Admin API routes.

All routes are protected with JWT authentication and mounted under /api/admin.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

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
