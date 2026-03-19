"""add story session persistence tables

Revision ID: 20260319_0003
Revises: 20260317_0002
Create Date: 2026-03-19 22:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260319_0003"
down_revision = "20260317_0002"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(item.get("name") == index_name for item in indexes)


def upgrade() -> None:
    if not _table_exists("story_sessions"):
        op.create_table(
            "story_sessions",
            sa.Column("thread_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("character_id", sa.Integer(), nullable=False),
            sa.Column("game_mode", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("current_round_no", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_scene_id", sa.String(length=64), nullable=True),
            sa.Column("latest_snapshot_round_no", sa.Integer(), nullable=True),
            sa.Column("is_initialized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("session_meta", sa.JSON(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("last_active_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
            sa.PrimaryKeyConstraint("thread_id"),
        )
    if not _index_exists("story_sessions", "ix_story_sessions_user_id"):
        op.create_index("ix_story_sessions_user_id", "story_sessions", ["user_id"], unique=False)

    if not _table_exists("story_rounds"):
        op.create_table(
            "story_rounds",
            sa.Column("round_id", sa.String(length=36), nullable=False),
            sa.Column("thread_id", sa.String(length=36), nullable=False),
            sa.Column("round_no", sa.Integer(), nullable=False),
            sa.Column("input_kind", sa.String(length=32), nullable=False),
            sa.Column("user_input_raw", sa.Text(), nullable=False),
            sa.Column("selected_option_index", sa.Integer(), nullable=True),
            sa.Column("request_payload", sa.JSON(), nullable=False),
            sa.Column("response_payload", sa.JSON(), nullable=False),
            sa.Column("state_before", sa.JSON(), nullable=False),
            sa.Column("state_after", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["thread_id"], ["story_sessions.thread_id"]),
            sa.PrimaryKeyConstraint("round_id"),
            sa.UniqueConstraint("thread_id", "round_no", name="uq_story_rounds_thread_round"),
        )
    if not _index_exists("story_rounds", "ix_story_rounds_thread_id"):
        op.create_index("ix_story_rounds_thread_id", "story_rounds", ["thread_id"], unique=False)

    if not _table_exists("story_snapshots"):
        op.create_table(
            "story_snapshots",
            sa.Column("snapshot_id", sa.String(length=36), nullable=False),
            sa.Column("thread_id", sa.String(length=36), nullable=False),
            sa.Column("round_no", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("current_scene_id", sa.String(length=64), nullable=True),
            sa.Column("snapshot_payload", sa.JSON(), nullable=False),
            sa.Column("response_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["thread_id"], ["story_sessions.thread_id"]),
            sa.PrimaryKeyConstraint("snapshot_id"),
            sa.UniqueConstraint("thread_id", "round_no", name="uq_story_snapshots_thread_round"),
        )
    if not _index_exists("story_snapshots", "ix_story_snapshots_thread_id"):
        op.create_index("ix_story_snapshots_thread_id", "story_snapshots", ["thread_id"], unique=False)


def downgrade() -> None:
    if _index_exists("story_snapshots", "ix_story_snapshots_thread_id"):
        op.drop_index("ix_story_snapshots_thread_id", table_name="story_snapshots")
    if _table_exists("story_snapshots"):
        op.drop_table("story_snapshots")

    if _index_exists("story_rounds", "ix_story_rounds_thread_id"):
        op.drop_index("ix_story_rounds_thread_id", table_name="story_rounds")
    if _table_exists("story_rounds"):
        op.drop_table("story_rounds")

    if _index_exists("story_sessions", "ix_story_sessions_user_id"):
        op.drop_index("ix_story_sessions_user_id", table_name="story_sessions")
    if _table_exists("story_sessions"):
        op.drop_table("story_sessions")
