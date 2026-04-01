"""训练系统相关数据库模型"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from models.character import Base


def _uuid_str() -> str:
    return str(uuid4())


class TrainingSession(Base):
    """训练会话主表"""

    __tablename__ = "training_sessions"

    session_id = Column(String(36), primary_key=True, default=_uuid_str)
    user_id = Column(String(128), nullable=False, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    training_mode = Column(String(32), nullable=False, default="guided")
    status = Column(String(32), nullable=False, default="initialized")  # initialized/in_progress/completed/aborted

    current_round_no = Column(Integer, nullable=False, default=0)
    current_scenario_id = Column(String(64), nullable=True)

    k_state = Column(JSON, nullable=False, default=dict)
    s_state = Column(JSON, nullable=False, default=dict)
    session_meta = Column(JSON, nullable=False, default=dict)

    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TrainingRound(Base):
    """训练回合记录表"""

    __tablename__ = "training_rounds"
    __table_args__ = (
        UniqueConstraint("session_id", "round_no", name="uq_training_rounds_session_round"),
    )

    round_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)

    scenario_id = Column(String(64), nullable=False)
    node_code = Column(String(64), nullable=True)
    user_input_raw = Column(Text, nullable=False)
    selected_option = Column(String(64), nullable=True)

    user_action = Column(JSON, nullable=False, default=dict)
    state_before = Column(JSON, nullable=False, default=dict)
    state_after = Column(JSON, nullable=False, default=dict)
    kt_before = Column(JSON, nullable=False, default=dict)
    kt_after = Column(JSON, nullable=False, default=dict)

    feedback_text = Column(Text, nullable=True)
    submit_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RoundEvaluation(Base):
    """回合评估结果表"""

    __tablename__ = "round_evaluations"

    evaluation_id = Column(String(36), primary_key=True, default=_uuid_str)
    round_id = Column(
        String(36),
        ForeignKey("training_rounds.round_id"),
        nullable=False,
        unique=True,
        index=True,
    )

    llm_model = Column(String(128), nullable=False, default="rules_v1")
    confidence = Column(Float, nullable=False, default=0.5)
    risk_flags = Column(JSON, nullable=False, default=list)
    skill_delta = Column(JSON, nullable=False, default=dict)
    s_delta = Column(JSON, nullable=False, default=dict)
    evidence = Column(JSON, nullable=False, default=list)
    skill_scores_preview = Column(JSON, nullable=False, default=dict)
    raw_payload = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class KtStateSnapshot(Base):
    """KT状态快照"""

    __tablename__ = "kt_state_snapshots"
    __table_args__ = (
        UniqueConstraint("session_id", "round_no", name="uq_kt_state_snapshots_session_round"),
    )

    snapshot_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)

    k1 = Column(Float, nullable=False, default=0.0)
    k2 = Column(Float, nullable=False, default=0.0)
    k3 = Column(Float, nullable=False, default=0.0)
    k4 = Column(Float, nullable=False, default=0.0)
    k5 = Column(Float, nullable=False, default=0.0)
    k6 = Column(Float, nullable=False, default=0.0)
    k7 = Column(Float, nullable=False, default=0.0)
    k8 = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NarrativeStateSnapshot(Base):
    """剧情状态S快照"""

    __tablename__ = "narrative_state_snapshots"
    __table_args__ = (
        UniqueConstraint("session_id", "round_no", name="uq_narrative_state_snapshots_session_round"),
    )

    snapshot_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)

    credibility = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)
    public_panic = Column(Float, nullable=False, default=0.0)
    source_safety = Column(Float, nullable=False, default=0.0)
    editor_trust = Column(Float, nullable=False, default=0.0)
    actionability = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EndingResult(Base):
    """结局结果表"""

    __tablename__ = "ending_results"

    ending_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(
        String(36),
        ForeignKey("training_sessions.session_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    ending_type = Column(String(64), nullable=False)
    ending_score = Column(Float, nullable=False, default=0.0)
    explanation = Column(Text, nullable=False, default="")
    report_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ScenarioRecommendationLog(Base):
    """场景推荐日志表：沉淀每轮推荐候选与最终选择，便于后续分析与审计。"""

    __tablename__ = "scenario_recommendation_logs"
    __table_args__ = (
        UniqueConstraint("session_id", "round_no", name="uq_scenario_recommendation_logs_session_round"),
    )

    recommendation_log_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)

    training_mode = Column(String(32), nullable=False, default="guided")
    selection_source = Column(String(64), nullable=True)
    recommended_scenario_id = Column(String(64), nullable=True)
    selected_scenario_id = Column(String(64), nullable=True)

    candidate_pool = Column(JSON, nullable=False, default=list)
    recommended_recommendation = Column(JSON, nullable=False, default=dict)
    selected_recommendation = Column(JSON, nullable=False, default=dict)
    decision_context = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TrainingAuditEvent(Base):
    """训练审计事件表：记录关键流程事件，支撑排错、回放和治理。"""

    __tablename__ = "training_audit_events"

    event_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TrainingMediaTask(Base):
    """Training media generation task lifecycle table."""

    __tablename__ = "training_media_tasks"

    task_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=True)

    task_type = Column(String(16), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)

    request_payload = Column(JSON, nullable=False, default=dict)
    result_payload = Column(JSON, nullable=True)
    error_payload = Column(JSON, nullable=True)

    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class TrainingStoryScript(Base):
    """训练剧本库：为每个 session 固化一份连续剧本（可复用/克隆）。"""

    __tablename__ = "training_story_scripts"

    script_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(
        String(36),
        ForeignKey("training_sessions.session_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    source_script_id = Column(String(36), nullable=True, index=True)

    provider = Column(String(64), nullable=False, default="auto")
    model = Column(String(128), nullable=False, default="auto")

    major_scene_count = Column(Integer, nullable=False, default=6)
    micro_scenes_per_gap = Column(Integer, nullable=False, default=2)
    # Contract: pending -> running -> ready|failed
    # Backward compatibility: older rows may use `succeeded`.
    status = Column(String(16), nullable=False, default="ready")  # pending/running/ready/failed(+succeeded legacy)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    fallback_used = Column(Boolean, nullable=False, default=False)
    payload = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TrainingCharacterPreviewJob(Base):
    """Persisted async preview-job lifecycle for training character portraits."""

    __tablename__ = "training_character_preview_jobs"

    job_id = Column(String(36), primary_key=True, default=_uuid_str)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)

    status = Column(String(32), nullable=False, default="pending")
    request_payload = Column(JSON, nullable=False, default=dict)
    request_payload_canonical = Column(Text, nullable=False, default="")
    image_urls = Column(JSON, nullable=False, default=list)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class KtObservation(Base):
    """KT 结构化观测表：沉淀每轮的关键训练事实，便于分析和诊断。"""

    __tablename__ = "kt_observations"
    __table_args__ = (
        UniqueConstraint("session_id", "round_no", name="uq_kt_observations_session_round"),
    )

    observation_id = Column(String(36), primary_key=True, default=_uuid_str)
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    round_no = Column(Integer, nullable=False)
    scenario_id = Column(String(64), nullable=False)
    scenario_title = Column(String(128), nullable=False, default="")
    training_mode = Column(String(32), nullable=False, default="guided")

    primary_skill_code = Column(String(32), nullable=True)
    primary_risk_flag = Column(String(64), nullable=True)
    is_high_risk = Column(Boolean, nullable=False, default=False)

    target_skills = Column(JSON, nullable=False, default=list)
    weak_skills_before = Column(JSON, nullable=False, default=list)
    risk_flags = Column(JSON, nullable=False, default=list)
    focus_tags = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)
    skill_observations = Column(JSON, nullable=False, default=list)
    state_observations = Column(JSON, nullable=False, default=list)
    observation_summary = Column(Text, nullable=False, default="")
    raw_payload = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
