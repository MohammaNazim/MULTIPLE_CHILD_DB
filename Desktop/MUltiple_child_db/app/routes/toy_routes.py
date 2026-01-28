from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from app.database.database import get_db
from app.database.models import (
    Toy,
    Child,
    Conversation,
    Message,
    ChildAnalytics,
)
from app.database.schemas import ToyAskRequest, ToyAskResponse
from app.auth import get_current_parent, verify_api_key

router = APIRouter(prefix="/toy", tags=["Toy"])

# ======================================================
# TOY PAIR (Parent → Child)
# ======================================================
@router.post("/pair")
async def pair_toy(
    toy_uuid: UUID,
    child_id: UUID,
    parent=Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == parent.id,
        )
    )
    child = q.scalars().first()
    if not child:
        raise HTTPException(403, "Child not owned by parent")

    q = await db.execute(select(Toy).where(Toy.toy_uuid == toy_uuid))
    toy = q.scalars().first()
    if not toy:
        raise HTTPException(404, "Toy not found")

    if child.toy_id == toy.id:
        return {"status": "already_paired"}

    child.toy_id = toy.id
    toy.is_active = True
    toy.last_seen = datetime.utcnow()

    await db.commit()
    return {"status": "paired"}

# ======================================================
# SET ACTIVE CHILD (Parent → Toy runtime control)
# ======================================================
@router.post("/set-active-child")
async def set_active_child(
    toy_uuid: UUID,
    child_id: UUID,
    parent=Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    # 1️⃣ verify child belongs to parent
    q = await db.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_id == parent.id,
        )
    )
    child = q.scalars().first()
    if not child:
        raise HTTPException(403, "Child not owned by parent")

    # 2️⃣ verify toy exists and is paired with parent
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
        raise HTTPException(404, "Toy not found or unauthorized")

    # 3️⃣ set runtime active child
    toy.active_child_id = child.id
    await db.commit()

    return {
        "status": "active_child_set",
        "toy_uuid": str(toy_uuid),
        "child_id": str(child_id),
    }   

# ======================================================
# TOY ASK (Toy → Cloud)
# ======================================================
@router.post("/ask", response_model=ToyAskResponse)
async def toy_ask(
    payload: ToyAskRequest,
    toy_uuid: UUID = Header(..., alias="x-toy-uuid"),
    api_key=Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    # 1️⃣ Verify toy
    q = await db.execute(
        select(Toy).where(Toy.toy_uuid == toy_uuid)
    )
    toy = q.scalars().first()

    if not toy or not toy.is_active:
        raise HTTPException(401, "Invalid or inactive toy")

    # 2️⃣ Active child must exist
    if not toy.active_child_id:
        raise HTTPException(409, "No active child set on toy")

    q = await db.execute(
        select(Child).where(Child.id == toy.active_child_id)
    )
    child = q.scalars().first()

    if not child:
        raise HTTPException(404, "Active child not found")

    # 3️⃣ Get or create conversation
    q = await db.execute(
        select(Conversation)
        .where(Conversation.child_id == child.id)
        .order_by(Conversation.last_activity.desc())
    )
    conversation = q.scalars().first()

    if not conversation:
        conversation = Conversation(child_id=child.id)
        db.add(conversation)
        await db.flush()

    conversation.last_activity = datetime.utcnow()

    # 4️⃣ Store child question
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.question,
    )
    db.add(user_msg)

    # 5️⃣ AI CALL (dummy for now)
    # 🔥 Later replace with vLLM / OpenAI
    ai_answer = f"Answer to: {payload.question}"

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_answer,
    )
    db.add(assistant_msg)

    # 6️⃣ Update analytics
    q = await db.execute(
        select(ChildAnalytics).where(ChildAnalytics.child_id == child.id)
    )
    analytics = q.scalars().first()

    if analytics:
        analytics.total_questions += 1
        analytics.weekly_questions += 1
        analytics.last_active_date = datetime.utcnow().date()

    await db.commit()

    return ToyAskResponse(
        conversation_id=conversation.id,
        answer=ai_answer,
    )

# ======================================================
# TOY HEARTBEAT (Toy → Cloud)
# ======================================================
@router.post("/heartbeat")
async def toy_heartbeat(
    toy_uuid: UUID = Header(..., alias="x-toy-uuid"),
    api_key=Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Toy).where(Toy.toy_uuid == toy_uuid))
    toy = q.scalars().first()
    if not toy:
        raise HTTPException(401, "Unknown toy")

    toy.last_seen = datetime.utcnow()
    toy.is_active = True

    await db.commit()
    return {"status": "ok"}
