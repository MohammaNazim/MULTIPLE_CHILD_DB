# app/routes/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone

from app.database.database import get_db
from app.database.models import Parent, RefreshToken, APIKey
from app.auth import (
    hash_password,
    verify_password,
    create_token_pair,
    hash_refresh_token,
    revoke_all_refresh_tokens,
    get_current_parent,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ======================================================
# Schemas
# ======================================================

class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class RefreshIn(BaseModel):
    refresh_token: str

class APIKeyCreateIn(BaseModel):
    owner: str


# ======================================================
# SIGNUP
# ======================================================

@router.post("/signup", status_code=201)
async def signup(data: SignupIn, db: AsyncSession = Depends(get_db)):
    if len(data.password) < 10:
        raise HTTPException(400, "Password must be at least 10 characters")
    
    # ❌ bcrypt limit (IMPORTANT)
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password too long (max 72 characters allowed)"
        )

    q = await db.execute(select(Parent).where(Parent.email == data.email))
    if q.scalars().first():
        raise HTTPException(400, "Email already exists")

    parent = Parent(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        is_active=True,
        token_version=1,
    )

    db.add(parent)
    await db.commit()
    await db.refresh(parent)

    return {
        "id": str(parent.id),
        "email": parent.email,
    }


# ======================================================
# LOGIN → ACCESS + REFRESH
# ======================================================

@router.post("/login")
async def login(
    data: LoginIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Parent).where(Parent.email == data.email))
    parent = q.scalars().first()

    if not parent or not verify_password(data.password, parent.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not parent.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return await create_token_pair(
        db=db,
        parent=parent,
        user_agent=request.headers.get("user-agent"),
    )


# ======================================================
# REFRESH TOKEN (ROTATION ENABLED)
# ======================================================

@router.post("/refresh")
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)

    q = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = q.scalars().first()

    if not stored:
        raise HTTPException(401, "Invalid refresh token")

    if stored.expires_at < datetime.now(timezone.utc):
        await db.delete(stored)
        await db.commit()
        raise HTTPException(401, "Refresh token expired")

    # fetch parent
    parent = await db.get(Parent, stored.parent_id)
    if not parent or not parent.is_active:
        raise HTTPException(401, "User inactive")

    # 🔁 ROTATE: delete old refresh token
    await db.delete(stored)
    await db.commit()

    return await create_token_pair(db, parent)


# ======================================================
# LOGOUT (ACCESS + REFRESH INVALID)
# ======================================================

@router.post("/logout")
async def logout(
    current_parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    # 🔐 revoke all access tokens
    current_parent.token_version += 1

    # 🔐 revoke all refresh tokens
    await revoke_all_refresh_tokens(db, str(current_parent.id))

    db.add(current_parent)
    await db.commit()

    return {"status": "logged_out"}


# ======================================================
# API KEY (ADMIN ONLY)
# ======================================================

@router.post("/apikey/create")
async def create_api_key(
    payload: APIKeyCreateIn,
    current_parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    if current_parent.role != "admin":
        raise HTTPException(403, "Admin only")

    import secrets
    from app.auth import hash_api_key

    raw_key = secrets.token_urlsafe(48)
    hashed = hash_api_key(raw_key)

    api_key = APIKey(
        key=hashed,
        owner=payload.owner,
        revoked=False,
    )
    db.add(api_key)
    await db.commit()

    # ⚠️ RAW KEY ONLY SHOWN ONCE
    return {
        "api_key": raw_key,
        "owner": payload.owner,
    }


# ======================================================
# CURRENT USER
# ======================================================

@router.get("/me")
async def get_me(current_parent: Parent = Depends(get_current_parent)):
    return {
        "id": str(current_parent.id),
        "email": current_parent.email,
        "name": current_parent.name,
        "role": current_parent.role,
        "created_at": current_parent.created_at,
    }
