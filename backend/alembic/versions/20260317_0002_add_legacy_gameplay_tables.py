"""add legacy gameplay tables

Revision ID: 20260317_0002
Revises: 20260317_0001
Create Date: 2026-03-17 19:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260317_0002"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """判断当前库里是否已经存在指定表。"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    """判断指定索引是否已经存在，避免老库重复创建时报错。"""
    if not _table_exists(table_name):
        return False

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(item.get("name") == index_name for item in indexes)


def upgrade() -> None:
    """补齐旧无限剧情流仍在使用的核心表结构。"""
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id", name="users_pkey"),
        )
    if not _index_exists("users", "ix_users_username"):
        op.create_index("ix_users_username", "users", ["username"], unique=True)
    if not _index_exists("users", "ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _table_exists("image_cache"):
        op.create_table(
            "image_cache",
            sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("prompt_hash", sa.String(length=255), nullable=False),
            sa.Column("image_url", sa.Text(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id", name="image_cache_pkey"),
        )
    if not _index_exists("image_cache", "ix_image_cache_prompt_hash"):
        op.create_index("ix_image_cache_prompt_hash", "image_cache", ["prompt_hash"], unique=True)

    if not _table_exists("threads"):
        op.create_table(
            "threads",
            sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("openai_thread_id", sa.String(length=255), nullable=False),
            sa.Column("game_mode", sa.String(length=255), nullable=True),
            sa.Column("character_id", postgresql.UUID(as_uuid=False), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="threads_user_id_fkey"),
            sa.PrimaryKeyConstraint("id", name="threads_pkey"),
        )
    if not _index_exists("threads", "ix_threads_user_id"):
        op.create_index("ix_threads_user_id", "threads", ["user_id"], unique=False)
    if not _index_exists("threads", "ix_threads_openai_thread_id"):
        op.create_index("ix_threads_openai_thread_id", "threads", ["openai_thread_id"], unique=True)

    if not _table_exists("story_states"):
        op.create_table(
            "story_states",
            sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("thread_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("current_scene", sa.String(length=255), nullable=True),
            sa.Column("story_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("character_relations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("emotion_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], name="story_states_thread_id_fkey"),
            sa.PrimaryKeyConstraint("id", name="story_states_pkey"),
        )
    if not _index_exists("story_states", "ix_story_states_thread_id"):
        op.create_index("ix_story_states_thread_id", "story_states", ["thread_id"], unique=True)

    if not _table_exists("conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("thread_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("role", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], name="conversations_thread_id_fkey"),
            sa.PrimaryKeyConstraint("id", name="conversations_pkey"),
        )
    if not _index_exists("conversations", "ix_conversations_thread_id"):
        op.create_index("ix_conversations_thread_id", "conversations", ["thread_id"], unique=False)
    if not _index_exists("conversations", "ix_conversations_created_at"):
        op.create_index("ix_conversations_created_at", "conversations", ["created_at"], unique=False)


def downgrade() -> None:
    """回滚旧剧情流兼容表。"""
    if _index_exists("conversations", "ix_conversations_created_at"):
        op.drop_index("ix_conversations_created_at", table_name="conversations")
    if _index_exists("conversations", "ix_conversations_thread_id"):
        op.drop_index("ix_conversations_thread_id", table_name="conversations")
    if _table_exists("conversations"):
        op.drop_table("conversations")

    if _index_exists("story_states", "ix_story_states_thread_id"):
        op.drop_index("ix_story_states_thread_id", table_name="story_states")
    if _table_exists("story_states"):
        op.drop_table("story_states")

    if _index_exists("threads", "ix_threads_openai_thread_id"):
        op.drop_index("ix_threads_openai_thread_id", table_name="threads")
    if _index_exists("threads", "ix_threads_user_id"):
        op.drop_index("ix_threads_user_id", table_name="threads")
    if _table_exists("threads"):
        op.drop_table("threads")

    if _index_exists("image_cache", "ix_image_cache_prompt_hash"):
        op.drop_index("ix_image_cache_prompt_hash", table_name="image_cache")
    if _table_exists("image_cache"):
        op.drop_table("image_cache")

    if _index_exists("users", "ix_users_email"):
        op.drop_index("ix_users_email", table_name="users")
    if _index_exists("users", "ix_users_username"):
        op.drop_index("ix_users_username", table_name="users")
    if _table_exists("users"):
        op.drop_table("users")
