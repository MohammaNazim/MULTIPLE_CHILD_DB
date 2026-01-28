# app/routes/admin_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List, Optional

from app.database.database import get_db
from app.database.models import (
    Parent,
    MessageMaster,
    Child,
    Toy,
)
from app.database.schemas import MessageMasterOut
from app.auth import get_current_parent

router = APIRouter(prefix="/admin", tags=["Admin"])


# ======================================================
# ADMIN GUARD
# ======================================================
def require_admin(
    current_parent: Parent = Depends(get_current_parent),
) -> Parent:
    if current_parent.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return current_parent


# ======================================================
# 1️⃣ ALL MESSAGES (GLOBAL – PERMANENT LOG)
# ======================================================
@router.get(
    "/messages",
    response_model=List[MessageMasterOut],
)
async def get_all_messages(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: Parent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(MessageMaster)
        .order_by(MessageMaster.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return q.scalars().all()


# ======================================================
# 2️⃣ MESSAGES BY CHILD
# ======================================================
@router.get(
    "/child/{child_id}/messages",
    response_model=List[MessageMasterOut],
)
async def get_child_messages(
    child_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: Parent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(MessageMaster)
        .where(MessageMaster.child_id == child_id)
        .order_by(MessageMaster.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return q.scalars().all()


# ======================================================
# 3️⃣ MESSAGES BY TOY
# ======================================================
@router.get(
    "/toy/{toy_uuid}/messages",
    response_model=List[MessageMasterOut],
)
async def get_toy_messages(
    toy_uuid: UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: Parent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(MessageMaster)
        .join(Child, Child.id == MessageMaster.child_id)
        .join(Toy, Toy.id == Child.toy_id)
        .where(Toy.toy_uuid == toy_uuid)
        .order_by(MessageMaster.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return q.scalars().all()
