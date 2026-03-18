"""baseline character and training schema

Revision ID: 20260317_0001
Revises:
Create Date: 2026-03-17 19:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260317_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建当前项目由 ORM 管理的角色域与训练域基础表。"""
    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=False),
        sa.Column("appearance", sa.Text(), nullable=False),
        sa.Column("personality", sa.Text(), nullable=False),
        sa.Column("scene_id", sa.String(length=50), nullable=True),
        sa.Column("character_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "character_attributes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("attribute_type", sa.String(length=50), nullable=False),
        sa.Column("attribute_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "character_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("favorability", sa.Float(), nullable=True),
        sa.Column("trust", sa.Float(), nullable=True),
        sa.Column("hostility", sa.Float(), nullable=True),
        sa.Column("dependence", sa.Float(), nullable=True),
        sa.Column("emotion", sa.Float(), nullable=True),
        sa.Column("stress", sa.Float(), nullable=True),
        sa.Column("anxiety", sa.Float(), nullable=True),
        sa.Column("happiness", sa.Float(), nullable=True),
        sa.Column("sadness", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("initiative", sa.Float(), nullable=True),
        sa.Column("caution", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_sessions",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=True),
        sa.Column("training_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_round_no", sa.Integer(), nullable=False),
        sa.Column("current_scenario_id", sa.String(length=64), nullable=True),
        sa.Column("k_state", sa.JSON(), nullable=False),
        sa.Column("s_state", sa.JSON(), nullable=False),
        sa.Column("session_meta", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_training_sessions_user_id", "training_sessions", ["user_id"], unique=False)

    op.create_table(
        "training_rounds",
        sa.Column("round_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("node_code", sa.String(length=64), nullable=True),
        sa.Column("user_input_raw", sa.Text(), nullable=False),
        sa.Column("selected_option", sa.String(length=64), nullable=True),
        sa.Column("user_action", sa.JSON(), nullable=False),
        sa.Column("state_before", sa.JSON(), nullable=False),
        sa.Column("state_after", sa.JSON(), nullable=False),
        sa.Column("kt_before", sa.JSON(), nullable=False),
        sa.Column("kt_after", sa.JSON(), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("submit_ts", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("round_id"),
        sa.UniqueConstraint("session_id", "round_no", name="uq_training_rounds_session_round"),
    )
    op.create_index("ix_training_rounds_session_id", "training_rounds", ["session_id"], unique=False)

    op.create_table(
        "round_evaluations",
        sa.Column("evaluation_id", sa.String(length=36), nullable=False),
        sa.Column("round_id", sa.String(length=36), nullable=False),
        sa.Column("llm_model", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("skill_delta", sa.JSON(), nullable=False),
        sa.Column("s_delta", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("skill_scores_preview", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["round_id"], ["training_rounds.round_id"]),
        sa.PrimaryKeyConstraint("evaluation_id"),
    )
    op.create_index("ix_round_evaluations_round_id", "round_evaluations", ["round_id"], unique=True)

    op.create_table(
        "kt_state_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("k1", sa.Float(), nullable=False),
        sa.Column("k2", sa.Float(), nullable=False),
        sa.Column("k3", sa.Float(), nullable=False),
        sa.Column("k4", sa.Float(), nullable=False),
        sa.Column("k5", sa.Float(), nullable=False),
        sa.Column("k6", sa.Float(), nullable=False),
        sa.Column("k7", sa.Float(), nullable=False),
        sa.Column("k8", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint("session_id", "round_no", name="uq_kt_state_snapshots_session_round"),
    )
    op.create_index("ix_kt_state_snapshots_session_id", "kt_state_snapshots", ["session_id"], unique=False)

    op.create_table(
        "narrative_state_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("credibility", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("public_panic", sa.Float(), nullable=False),
        sa.Column("source_safety", sa.Float(), nullable=False),
        sa.Column("editor_trust", sa.Float(), nullable=False),
        sa.Column("actionability", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint("session_id", "round_no", name="uq_narrative_state_snapshots_session_round"),
    )
    op.create_index(
        "ix_narrative_state_snapshots_session_id",
        "narrative_state_snapshots",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "ending_results",
        sa.Column("ending_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("ending_type", sa.String(length=64), nullable=False),
        sa.Column("ending_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("report_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("ending_id"),
    )
    op.create_index("ix_ending_results_session_id", "ending_results", ["session_id"], unique=True)

    op.create_table(
        "scenario_recommendation_logs",
        sa.Column("recommendation_log_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("training_mode", sa.String(length=32), nullable=False),
        sa.Column("selection_source", sa.String(length=64), nullable=True),
        sa.Column("recommended_scenario_id", sa.String(length=64), nullable=True),
        sa.Column("selected_scenario_id", sa.String(length=64), nullable=True),
        sa.Column("candidate_pool", sa.JSON(), nullable=False),
        sa.Column("recommended_recommendation", sa.JSON(), nullable=False),
        sa.Column("selected_recommendation", sa.JSON(), nullable=False),
        sa.Column("decision_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("recommendation_log_id"),
        sa.UniqueConstraint("session_id", "round_no", name="uq_scenario_recommendation_logs_session_round"),
    )
    op.create_index(
        "ix_scenario_recommendation_logs_session_id",
        "scenario_recommendation_logs",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "training_audit_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_training_audit_events_event_type", "training_audit_events", ["event_type"], unique=False)
    op.create_index("ix_training_audit_events_session_id", "training_audit_events", ["session_id"], unique=False)

    op.create_table(
        "kt_observations",
        sa.Column("observation_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("scenario_title", sa.String(length=128), nullable=False),
        sa.Column("training_mode", sa.String(length=32), nullable=False),
        sa.Column("primary_skill_code", sa.String(length=32), nullable=True),
        sa.Column("primary_risk_flag", sa.String(length=64), nullable=True),
        sa.Column("is_high_risk", sa.Boolean(), nullable=False),
        sa.Column("target_skills", sa.JSON(), nullable=False),
        sa.Column("weak_skills_before", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("focus_tags", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("skill_observations", sa.JSON(), nullable=False),
        sa.Column("state_observations", sa.JSON(), nullable=False),
        sa.Column("observation_summary", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.session_id"]),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint("session_id", "round_no", name="uq_kt_observations_session_round"),
    )
    op.create_index("ix_kt_observations_session_id", "kt_observations", ["session_id"], unique=False)


def downgrade() -> None:
    """回滚基础表结构。"""
    op.drop_index("ix_kt_observations_session_id", table_name="kt_observations")
    op.drop_table("kt_observations")

    op.drop_index("ix_training_audit_events_session_id", table_name="training_audit_events")
    op.drop_index("ix_training_audit_events_event_type", table_name="training_audit_events")
    op.drop_table("training_audit_events")

    op.drop_index("ix_scenario_recommendation_logs_session_id", table_name="scenario_recommendation_logs")
    op.drop_table("scenario_recommendation_logs")

    op.drop_index("ix_ending_results_session_id", table_name="ending_results")
    op.drop_table("ending_results")

    op.drop_index("ix_narrative_state_snapshots_session_id", table_name="narrative_state_snapshots")
    op.drop_table("narrative_state_snapshots")

    op.drop_index("ix_kt_state_snapshots_session_id", table_name="kt_state_snapshots")
    op.drop_table("kt_state_snapshots")

    op.drop_index("ix_round_evaluations_round_id", table_name="round_evaluations")
    op.drop_table("round_evaluations")

    op.drop_index("ix_training_rounds_session_id", table_name="training_rounds")
    op.drop_table("training_rounds")

    op.drop_index("ix_training_sessions_user_id", table_name="training_sessions")
    op.drop_table("training_sessions")

    op.drop_table("character_states")
    op.drop_table("character_attributes")
    op.drop_table("characters")
