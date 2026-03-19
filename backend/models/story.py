"""Story-domain persistence models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON

from models.character import Base


def _uuid_str() -> str:
    return str(uuid4())


class StorySession(Base):
    """Story session fact table."""

    __tablename__ = "story_sessions"

    thread_id = Column(String(36), primary_key=True)
    user_id = Column(String(128), nullable=False, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    game_mode = Column(String(32), nullable=False, default="solo")
    status = Column(String(32), nullable=False, default="initialized")
    current_round_no = Column(Integer, nullable=False, default=0)
    current_scene_id = Column(String(64), nullable=True)
    latest_snapshot_round_no = Column(Integer, nullable=True)
    is_initialized = Column(Boolean, nullable=False, default=False)
    session_meta = Column(JSON, nullable=False, default=dict)
    expires_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class StoryRound(Base):
    """Story round submission record."""

    __tablename__ = "story_rounds"
    __table_args__ = (
        UniqueConstraint("thread_id", "round_no", name="uq_story_rounds_thread_round"),
    )

    round_id = Column(String(36), primary_key=True, default=_uuid_str)
    thread_id = Column(String(36), ForeignKey("story_sessions.thread_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)
    input_kind = Column(String(32), nullable=False, default="free_text")
    user_input_raw = Column(Text, nullable=False, default="")
    selected_option_index = Column(Integer, nullable=True)
    request_payload = Column(JSON, nullable=False, default=dict)
    response_payload = Column(JSON, nullable=False, default=dict)
    state_before = Column(JSON, nullable=False, default=dict)
    state_after = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="in_progress")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StorySnapshot(Base):
    """Restorable story runtime snapshot."""

    __tablename__ = "story_snapshots"
    __table_args__ = (
        UniqueConstraint("thread_id", "round_no", name="uq_story_snapshots_thread_round"),
    )

    snapshot_id = Column(String(36), primary_key=True, default=_uuid_str)
    thread_id = Column(String(36), ForeignKey("story_sessions.thread_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="initialized")
    current_scene_id = Column(String(64), nullable=True)
    snapshot_payload = Column(JSON, nullable=False, default=dict)
    response_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
