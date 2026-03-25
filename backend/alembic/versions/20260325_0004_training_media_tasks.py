"""add training media task table

Revision ID: 20260325_0004
Revises: 20260319_0003
Create Date: 2026-03-25 20:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260325_0004"
down_revision = "20260319_0003"
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
    if not _table_exists("training_media_tasks"):
        op.create_table(
            "training_media_tasks",
            sa.Column("task_id", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.String(length=36), nullable=False),
            sa.Column("round_no", sa.Integer(), nullable=True),
            sa.Column("task_type", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("request_payload", sa.JSON(), nullable=False),
            sa.Column("result_payload", sa.JSON(), nullable=True),
            sa.Column("error_payload", sa.JSON(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
            sa.PrimaryKeyConstraint("task_id"),
            sa.UniqueConstraint("idempotency_key", name="uq_training_media_tasks_idempotency_key"),
        )

    if not _index_exists("training_media_tasks", "ix_training_media_tasks_session_id"):
        op.create_index(
            "ix_training_media_tasks_session_id",
            "training_media_tasks",
            ["session_id"],
            unique=False,
        )

    if not _index_exists("training_media_tasks", "ix_training_media_tasks_idempotency_key"):
        op.create_index(
            "ix_training_media_tasks_idempotency_key",
            "training_media_tasks",
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    if _index_exists("training_media_tasks", "ix_training_media_tasks_idempotency_key"):
        op.drop_index("ix_training_media_tasks_idempotency_key", table_name="training_media_tasks")

    if _index_exists("training_media_tasks", "ix_training_media_tasks_session_id"):
        op.drop_index("ix_training_media_tasks_session_id", table_name="training_media_tasks")

    if _table_exists("training_media_tasks"):
        op.drop_table("training_media_tasks")
