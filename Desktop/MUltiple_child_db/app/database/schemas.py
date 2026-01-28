from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from uuid import UUID

# ============================================================
# 1) PARENT
# ============================================================

class ParentBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None


class ParentCreate(ParentBase):
    password: str


class ParentOut(ParentBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 2) TOY
# ============================================================

class ToyBase(BaseModel):
    name: Optional[str]
    model_no: Optional[str]
    firmware_version: Optional[str]


class ToyOut(ToyBase):
    id: UUID
    toy_uuid: UUID
    registered_at: datetime

    class Config:
        from_attributes = True
        

class ToyAskRequest(BaseModel):
    question: str


class ToyAskResponse(BaseModel):
    conversation_id: UUID
    answer: str



# ============================================================
# 3) CHILD
# ============================================================

class ChildBase(BaseModel):
    child_name: str
    age: int


class ChildCreate(ChildBase):
    pass


class ChildOut(ChildBase):
    id: UUID
    parent_id: UUID
    toy_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 4) CHILD ANALYTICS
# ============================================================

class ChildAnalyticsOut(BaseModel):
    id: UUID
    child_id: UUID

    total_questions: int
    weekly_questions: int
    vocab_growth: int
    avg_complexity: float

    streak_days: int
    progress_score: Optional[float]

    last_active_date: Optional[date]
    updated_at: datetime

    class Config:
        from_attributes = True



# ============================================================
# 5) WEEKLY SUMMARY (Parent Dashboard)
# ============================================================

class WeeklySummaryOut(BaseModel):
    id: UUID
    child_id: UUID
    week_start: datetime
    week_end: datetime
    topics: List[str]
    summary_text: Optional[str]
    questions_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 6) MESSAGE MASTER (Admin-only Full History)
# ============================================================

class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageMasterOut(BaseModel):
    id: UUID
    child_id: Optional[UUID]
    conversation_id: Optional[UUID]
    role: MessageRole
    content: str
    model_used: Optional[str]
    complexity: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# 7) API KEYS
# ============================================================

class APIKeyOut(BaseModel):
    id: UUID
    key: str
    owner: Optional[str]
    revoked: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# 8) QUERY PROCESSING  ❌ (Deprecated – not used in production)
# ============================================================
# class QueryRequest(BaseModel):
#     question: str
#
# class QueryResponse(BaseModel):
#     request_id: str
#     status: str
