# app/routes/parent_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.database.database import get_db
from app.database.models import (
    Parent,
    Child,
    ChildAnalytics,
    Toy,
    WeeklySummary,
)
from app.database.schemas import (
    ChildOut,
    ChildCreate,
    ChildAnalyticsOut,
    WeeklySummaryOut,
)
from app.auth import get_current_parent

router = APIRouter(prefix="/parent", tags=["Parent Dashboard"])


# ======================================================
# 1️⃣ GET ALL CHILDREN OF PARENT
# ======================================================
@router.get("/children", response_model=list[ChildOut])
async def get_children(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(   
        select(Child)
        .where(Child.parent_id == parent.id)
        .order_by(Child.created_at.asc())
    )
    return q.scalars().all()

# ======================================================
# 2️⃣ CREATE A NEW CHILD  
# ======================================================

@router.post("/children", response_model=ChildOut)
async def create_child(
    data: ChildCreate,
    current_parent=Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    # 🔒 Max 3 children rule
    q = await db.execute(
        select(func.count(Child.id))
        .where(Child.parent_id == current_parent.id)
    )
    count = q.scalar()

    if count >= 3:
        raise HTTPException(
            status_code=409,
            detail="Maximum 3 children allowed per parent"
        )

    try:
        child = Child(
            parent=current_parent,   # ✅ SINGLE SOURCE OF TRUTH
            child_name=data.child_name,
            age=data.age,
        )

        db.add(child)
        await db.flush()  # child.id generated

        db.add(ChildAnalytics(child_id=child.id))
        await db.commit()
        await db.refresh(child)

        return child

    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Child creation conflict")

# ======================================================
# 2️⃣ GET CHILD ANALYTICS
# ======================================================
@router.get("/child/{child_id}/analytics", response_model=ChildAnalyticsOut)
async def get_child_analytics(
    child_id: UUID,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(ChildAnalytics)
        .join(Child)
        .where(
            Child.id == child_id,
            Child.parent_id == parent.id,
        )
    )
    analytics = q.scalars().first()

    if not analytics:
        raise HTTPException(
            status_code=404,
            detail="Analytics not initialized for this child"
        )

    return analytics


# ======================================================
# 3️⃣ GET ACTIVE CHILD (RUNTIME STATE)
# ======================================================
@router.get("/toy/{toy_uuid}/active-child")
async def get_active_child(
    toy_uuid: UUID,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Toy)
        .join(Child, Toy.id == Child.toy_id)
        .where(
            Toy.toy_uuid == toy_uuid,
            Child.parent_id == parent.id,
        )
    )
    toy = q.scalars().first()

    if not toy or not toy.active_child_id:
        raise HTTPException(404, "No active child set")

    q = await db.execute(
        select(Child).where(Child.id == toy.active_child_id)
    )
    child = q.scalars().first()

    if not child:
        raise HTTPException(404, "Active child not found")

    return {
        "toy_uuid": str(toy_uuid),
        "child_id": str(child.id),
        "child_name": child.child_name,
    }


# ======================================================
# 4️⃣ GET TOY STATUS (ONLINE / OFFLINE)
# ======================================================
@router.get("/toy/{toy_uuid}/status")
async def get_toy_status(
    toy_uuid: UUID,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Toy)
        .join(Child, Toy.id == Child.toy_id)
        .where(
            Toy.toy_uuid == toy_uuid,
            Child.parent_id == parent.id,
        )
    )
    toy = q.scalars().first()

    if not toy:
        raise HTTPException(404, "Toy not found")

    now = datetime.now(timezone.utc)

    if toy.last_seen:
        last_seen = (
            toy.last_seen.replace(tzinfo=timezone.utc)
            if toy.last_seen.tzinfo is None
            else toy.last_seen
        )
        is_online = (now - last_seen) < timedelta(minutes=2)
    else:
        is_online = False
        last_seen = None

    return {
        "toy_uuid": str(toy_uuid),
        "is_active": is_online,
        "last_seen": last_seen,
    }


# ======================================================
# 5️⃣ WEEKLY SUMMARY
# ======================================================
@router.get(
    "/child/{child_id}/weekly-summary",
    response_model=WeeklySummaryOut
)
async def get_weekly_summary(
    child_id: UUID,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(WeeklySummary)
        .join(Child)
        .where(
            Child.id == child_id,
            Child.parent_id == parent.id,
        )
        .order_by(WeeklySummary.week_start.desc())
    )
    summary = q.scalars().first()

    if not summary:
        raise HTTPException(404, "Weekly summary not found")

    return summary
