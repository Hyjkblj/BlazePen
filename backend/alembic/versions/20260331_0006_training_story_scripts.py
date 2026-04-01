"""add training story scripts table

Revision ID: 20260331_0006
Revises: 20260327_0005
Create Date: 2026-03-31 13:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0006"
down_revision = "20260327_0005"
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
    if not _table_exists("training_story_scripts"):
        op.create_table(
            "training_story_scripts",
            sa.Column("script_id", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.String(length=36), nullable=False),
            sa.Column("source_script_id", sa.String(length=36), nullable=True),
            sa.Column("provider", sa.String(length=64), nullable=False, server_default="auto"),
            sa.Column("model", sa.String(length=128), nullable=False, server_default="auto"),
            sa.Column("major_scene_count", sa.Integer(), nullable=False, server_default="6"),
            sa.Column("micro_scenes_per_gap", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
            sa.PrimaryKeyConstraint("script_id"),
            sa.UniqueConstraint("session_id", name="uq_training_story_scripts_session_id"),
        )

    if not _index_exists("training_story_scripts", "ix_training_story_scripts_session_id"):
        op.create_index(
            "ix_training_story_scripts_session_id",
            "training_story_scripts",
            ["session_id"],
            unique=True,
        )

    if not _index_exists("training_story_scripts", "ix_training_story_scripts_source_script_id"):
        op.create_index(
            "ix_training_story_scripts_source_script_id",
            "training_story_scripts",
            ["source_script_id"],
            unique=False,
        )


def downgrade() -> None:
    if _index_exists("training_story_scripts", "ix_training_story_scripts_source_script_id"):
        op.drop_index("ix_training_story_scripts_source_script_id", table_name="training_story_scripts")

    if _index_exists("training_story_scripts", "ix_training_story_scripts_session_id"):
        op.drop_index("ix_training_story_scripts_session_id", table_name="training_story_scripts")

    if _table_exists("training_story_scripts"):
        op.drop_table("training_story_scripts")

