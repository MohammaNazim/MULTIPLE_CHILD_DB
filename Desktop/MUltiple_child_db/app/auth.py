# app/auth.py
import os
import secrets
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.database import get_db, settings
from app.database.models import Parent, APIKey, RefreshToken

# ======================================================
# CONFIG
# ======================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY not set")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", 15))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", 30))

oauth2_scheme = HTTPBearer()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ======================================================
# PASSWORD
# ======================================================

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(raw: str, hashed: str) -> bool:
    return pwd_ctx.verify(raw, hashed)


# ======================================================
# JWT HELPERS
# ======================================================

def _utcnow():
    return datetime.now(timezone.utc)

def create_access_token(parent: Parent) -> str:
    expire = _utcnow() + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": str(parent.id),
        "role": parent.role,
        "token_version": parent.token_version,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token")


# ======================================================
# REFRESH TOKENS
# ======================================================

def create_refresh_token_raw() -> str:
    return secrets.token_urlsafe(64)

def hash_refresh_token(raw: str) -> str:
    return hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()

async def store_refresh_token(
    db: AsyncSession,
    parent_id: str,
    raw_token: str,
    user_agent: Optional[str] = None,
):
    expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_DAYS)
    token = RefreshToken(
        parent_id=parent_id,
        token_hash=hash_refresh_token(raw_token),
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(token)
    await db.commit()

async def revoke_all_refresh_tokens(db: AsyncSession, parent_id: str):
    q = await db.execute(
        select(RefreshToken).where(RefreshToken.parent_id == parent_id)
    )
    for row in q.scalars().all():
        await db.delete(row)
    await db.commit()


# ======================================================
# TOKEN PAIR
# ======================================================

async def create_token_pair(
    db: AsyncSession,
    parent: Parent,
    user_agent: Optional[str] = None,
):
    access_token = create_access_token(parent)
    refresh_raw = create_refresh_token_raw()
    await store_refresh_token(db, str(parent.id), refresh_raw, user_agent)

    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
    }


# ======================================================
# CURRENT PARENT (JWT GUARD)
# ======================================================

async def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Parent:
    payload = decode_access_token(credentials.credentials)

    parent_id = payload.get("sub")
    token_version = payload.get("token_version")

    if not parent_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    q = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = q.scalars().first()

    if not parent or not parent.is_active:
        raise HTTPException(status_code=401, detail="User inactive or not found")

    if parent.token_version != token_version:
        raise HTTPException(status_code=401, detail="Token revoked")

    return parent


# ======================================================
# API KEY (MACHINE AUTH)
# ======================================================

def hash_api_key(raw: str) -> str:
    return hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()

async def verify_api_key(
    api_key: Optional[str] = Header(None, alias="x-api-key"),
    db: AsyncSession = Depends(get_db),
):
    if not api_key:
        raise HTTPException(status_code=401, detail= "API key required")

    hashed = hash_api_key(api_key)
    q = await db.execute(select(APIKey).where(APIKey.key == hashed))
    key = q.scalars().first()

    if not key or key.revoked:
        raise HTTPException(status_code=403, detail= "Invalid or revoked API key")

    return key
