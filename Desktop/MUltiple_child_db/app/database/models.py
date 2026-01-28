# app/database/models.py
import uuid
import enum
from datetime import date

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    Enum,
    Float,
    JSON,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# ============================================================
# COMMON
# ============================================================

def UUID_PK():
    return Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )


# ============================================================
# PARENT
# ============================================================

class Parent(Base):
    __tablename__ = "parents"

    id = UUID_PK()
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20))
    role = Column(String(20), default="parent")

    token_version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    children = relationship(
        "Child",
        back_populates="parent",
        cascade="all, delete-orphan",
    )


# ============================================================
# TOY
# ============================================================

class Toy(Base):
    __tablename__ = "toys"

    id = UUID_PK()
    toy_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    model_no = Column(String(50))
    firmware_version = Column(String(50))

    is_active = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True))

    # Runtime active speaker
    active_child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("children.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    # 🔥 CRITICAL: explicit FK to avoid ambiguity
    children = relationship(
        "Child",
        back_populates="toy",
        foreign_keys="Child.toy_id",
    )


# ============================================================
# CHILD
# ============================================================

class Child(Base):
    __tablename__ = "children"

    id = UUID_PK()

    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parents.id", ondelete="CASCADE"),
        nullable=False,
    )

    toy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("toys.id", ondelete="SET NULL"),
        nullable=True,
    )

    child_name = Column(String(100))
    age = Column(Integer)

    parent = relationship(
        "Parent",
        back_populates="children",
    )

    toy = relationship(
        "Toy",
        back_populates="children",
        foreign_keys=[toy_id],
    )

    analytics = relationship(
        "ChildAnalytics",
        back_populates="child",
        uselist=False,
        cascade="all, delete-orphan",
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# CHILD ANALYTICS
# ============================================================

class ChildAnalytics(Base):
    __tablename__ = "child_analytics"

    id = UUID_PK()
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("children.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    total_questions = Column(Integer, default=0)
    weekly_questions = Column(Integer, default=0)
    vocab_growth = Column(Integer, default=0)
    avg_complexity = Column(Float, default=0.0)

    streak_days = Column(Integer, default=0)
    progress_score = Column(Float, default=0.0)
    last_active_date = Column(Date, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    child = relationship(
        "Child",
        back_populates="analytics",
    )


# ============================================================
# CONVERSATION
# ============================================================

class Conversation(Base):
    __tablename__ = "conversations"

    id = UUID_PK()
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("children.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship(
        "Message",
        cascade="all, delete-orphan",
    )


# ============================================================
# MESSAGE
# ============================================================

class RoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(Base):
    __tablename__ = "messages"

    id = UUID_PK()
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(Enum(RoleEnum), nullable=False)
    content = Column(Text, nullable=False)
    seq = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# MESSAGE MASTER (ADMIN AUDIT LOG)
# ============================================================

class MessageMaster(Base):
    __tablename__ = "messages_master"

    id = UUID_PK()
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("children.id", ondelete="SET NULL"),
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
    )

    role = Column(String(20))
    content = Column(Text)

    model_used = Column(String(50))
    complexity = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# AI INFERENCE LOG
# ============================================================

class AIInferenceLog(Base):
    __tablename__ = "ai_inference_logs"

    id = UUID_PK()
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("children.id", ondelete="SET NULL"),
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
    )

    question = Column(Text)
    answer = Column(Text)

    model = Column(String(50))
    latency_ms = Column(Integer)
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# WEEKLY SUMMARY
# ============================================================

class WeeklySummary(Base):
    __tablename__ = "weekly_summaries"

    id = UUID_PK()
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("children.id", ondelete="CASCADE"),
        nullable=False,
    )

    week_start = Column(DateTime(timezone=True))
    week_end = Column(DateTime(timezone=True))

    topics = Column(JSON)
    summary_text = Column(Text)
    questions_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# API KEY
# ============================================================

class APIKey(Base):
    __tablename__ = "api_keys"

    id = UUID_PK()
    key = Column(String, unique=True, nullable=False)
    owner = Column(String)
    revoked = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# REFRESH TOKEN
# ============================================================

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = UUID_PK()
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    user_agent = Column(String(255))
    expires_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# REVOKED TOKEN
# ============================================================

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = UUID_PK()
    jti = Column(String(64), unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(Text)
