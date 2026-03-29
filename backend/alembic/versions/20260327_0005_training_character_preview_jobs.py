"""add training character preview job table

Revision ID: 20260327_0005
Revises: 20260325_0004
Create Date: 2026-03-27 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0005"
down_revision = "20260325_0004"
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
    if not _table_exists("training_character_preview_jobs"):
        op.create_table(
            "training_character_preview_jobs",
            sa.Column("job_id", sa.String(length=36), nullable=False),
            sa.Column("character_id", sa.Integer(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("request_payload", sa.JSON(), nullable=False),
            sa.Column("request_payload_canonical", sa.Text(), nullable=False, server_default=""),
            sa.Column("image_urls", sa.JSON(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
            sa.PrimaryKeyConstraint("job_id"),
            sa.UniqueConstraint(
                "idempotency_key",
                name="uq_training_character_preview_jobs_idempotency_key",
            ),
        )

    if not _index_exists(
        "training_character_preview_jobs",
        "ix_training_character_preview_jobs_character_id",
    ):
        op.create_index(
            "ix_training_character_preview_jobs_character_id",
            "training_character_preview_jobs",
            ["character_id"],
            unique=False,
        )

    if not _index_exists(
        "training_character_preview_jobs",
        "ix_training_character_preview_jobs_idempotency_key",
    ):
        op.create_index(
            "ix_training_character_preview_jobs_idempotency_key",
            "training_character_preview_jobs",
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    if _index_exists(
        "training_character_preview_jobs",
        "ix_training_character_preview_jobs_idempotency_key",
    ):
        op.drop_index(
            "ix_training_character_preview_jobs_idempotency_key",
            table_name="training_character_preview_jobs",
        )

    if _index_exists(
        "training_character_preview_jobs",
        "ix_training_character_preview_jobs_character_id",
    ):
        op.drop_index(
            "ix_training_character_preview_jobs_character_id",
            table_name="training_character_preview_jobs",
        )

    if _table_exists("training_character_preview_jobs"):
        op.drop_table("training_character_preview_jobs")
