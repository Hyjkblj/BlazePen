"""add status fields for training story scripts

Revision ID: 20260331_0007
Revises: 20260331_0006
Create Date: 2026-03-31 20:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0007"
down_revision = "20260331_0006"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name)
    return any(item.get("name") == column_name for item in cols)


def upgrade() -> None:
    if not _table_exists("training_story_scripts"):
        return

    if not _column_exists("training_story_scripts", "status"):
        op.add_column(
            "training_story_scripts",
            sa.Column("status", sa.String(length=16), nullable=False, server_default="succeeded"),
        )
    if not _column_exists("training_story_scripts", "error_code"):
        op.add_column("training_story_scripts", sa.Column("error_code", sa.String(length=64), nullable=True))
    if not _column_exists("training_story_scripts", "error_message"):
        op.add_column("training_story_scripts", sa.Column("error_message", sa.Text(), nullable=True))
    if not _column_exists("training_story_scripts", "fallback_used"):
        op.add_column(
            "training_story_scripts",
            sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    if not _table_exists("training_story_scripts"):
        return
    if _column_exists("training_story_scripts", "fallback_used"):
        op.drop_column("training_story_scripts", "fallback_used")
    if _column_exists("training_story_scripts", "error_message"):
        op.drop_column("training_story_scripts", "error_message")
    if _column_exists("training_story_scripts", "error_code"):
        op.drop_column("training_story_scripts", "error_code")
    if _column_exists("training_story_scripts", "status"):
        op.drop_column("training_story_scripts", "status")

