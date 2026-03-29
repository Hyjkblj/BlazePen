"""训练持久化适配层。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import inspect
from typing import Any, Dict, List, Protocol

from sqlalchemy.exc import DatabaseError, OperationalError, ProgrammingError

from training.exceptions import TrainingStorageUnavailableError
from training.training_repository import SqlAlchemyTrainingRepository
from utils.logger import get_logger


logger = get_logger(__name__)


def _is_missing_training_media_tasks_table_error(exc: Exception) -> bool:
    """Detect DB errors caused by missing `training_media_tasks` table."""
    message = str(exc or "")
    lowered = message.lower()
    if "training_media_tasks" not in lowered:
        return False
    return any(
        token in lowered
        for token in (
            "undefinedtable",
            "does not exist",
            "doesn't exist",
            "no such table",
            "unknown table",
            "relation",
        )
    )


def _raise_media_task_storage_unavailable(
    *,
    operation: str,
    error: Exception,
    details: dict | None = None,
) -> None:
    logger.error(
        "training media task storage unavailable: operation=%s error=%s details=%s",
        operation,
        str(error),
        dict(details or {}),
    )
    raise TrainingStorageUnavailableError(
        message="training media task storage unavailable: training_media_tasks table is missing",
        details={
            "operation": operation,
            **dict(details or {}),
        },
    ) from error


@dataclass(slots=True)
class TrainingSessionRecord:
    """训练会话的稳定读取模型。"""

    session_id: str
    user_id: str
    character_id: int | None = None
    training_mode: str = "guided"
    status: str = "in_progress"
    current_round_no: int = 0
    current_scenario_id: str | None = None
    k_state: Dict[str, float] = field(default_factory=dict)
    s_state: Dict[str, float] = field(default_factory=dict)
    session_meta: Dict[str, Any] = field(default_factory=dict)
    end_time: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class TrainingRoundRecord:
    """训练回合的稳定读取模型。"""

    round_id: str
    session_id: str
    round_no: int
    scenario_id: str
    user_input_raw: str
    selected_option: str | None = None
    user_action: Dict[str, Any] = field(default_factory=dict)
    state_before: Dict[str, float] = field(default_factory=dict)
    state_after: Dict[str, float] = field(default_factory=dict)
    kt_before: Dict[str, float] = field(default_factory=dict)
    kt_after: Dict[str, float] = field(default_factory=dict)
    feedback_text: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class RoundEvaluationRecord:
    """回合评估的稳定读取模型。"""

    round_id: str
    llm_model: str = ""
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    risk_flags: List[str] = field(default_factory=list)


@dataclass(slots=True)
class EndingResultRecord:
    """结局结果的稳定读取模型。"""

    session_id: str
    report_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScenarioRecommendationLogRecord:
    """场景推荐日志的稳定读取模型。"""

    recommendation_log_id: str
    session_id: str
    round_no: int
    training_mode: str = "guided"
    selection_source: str | None = None
    recommended_scenario_id: str | None = None
    selected_scenario_id: str | None = None
    candidate_pool: List[Dict[str, Any]] = field(default_factory=list)
    recommended_recommendation: Dict[str, Any] = field(default_factory=dict)
    selected_recommendation: Dict[str, Any] = field(default_factory=dict)
    decision_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class TrainingAuditEventRecord:
    """训练审计事件的稳定读取模型。"""

    event_id: str
    session_id: str
    event_type: str
    round_no: int | None = None
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(slots=True)
class TrainingMediaTaskRecord:
    """Stable read model for training media task persistence."""

    task_id: str
    session_id: str
    round_no: int | None
    task_type: str
    status: str
    idempotency_key: str
    request_payload: Dict[str, Any] = field(default_factory=dict)
    result_payload: Dict[str, Any] | None = None
    error_payload: Dict[str, Any] | None = None
    retry_count: int = 0
    max_retries: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(slots=True)
class KtObservationRecord:
    """KT 结构化观测的稳定读取模型。"""

    observation_id: str
    session_id: str
    round_no: int
    scenario_id: str
    scenario_title: str = ""
    training_mode: str = "guided"
    primary_skill_code: str | None = None
    primary_risk_flag: str | None = None
    is_high_risk: bool = False
    target_skills: List[str] = field(default_factory=list)
    weak_skills_before: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    focus_tags: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    skill_observations: List[Dict[str, Any]] = field(default_factory=list)
    state_observations: List[Dict[str, Any]] = field(default_factory=list)
    observation_summary: str = ""
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


class TrainingStoreProtocol(Protocol):
    """训练服务真正依赖的最小持久化接口。"""

    def create_training_session_artifacts(
        self,
        user_id: str,
        character_id: int | None = None,
        training_mode: str = "guided",
        k_state: dict | None = None,
        s_state: dict | None = None,
        session_meta: dict | None = None,
        audit_event_payload: dict | None = None,
    ) -> TrainingSessionRecord:
        ...

    def create_training_session(
        self,
        user_id: str,
        character_id: int | None = None,
        training_mode: str = "guided",
        k_state: dict | None = None,
        s_state: dict | None = None,
        session_meta: dict | None = None,
    ) -> TrainingSessionRecord:
        ...

    def get_training_session(self, session_id: str) -> TrainingSessionRecord | None:
        ...

    def update_training_session(self, session_id: str, updates: dict) -> TrainingSessionRecord | None:
        ...

    def create_media_task(
        self,
        *,
        session_id: str,
        round_no: int | None,
        task_type: str,
        idempotency_key: str,
        request_payload: dict,
        max_retries: int = 0,
    ) -> TrainingMediaTaskRecord:
        ...

    def get_media_task(self, task_id: str) -> TrainingMediaTaskRecord | None:
        ...

    def get_media_task_by_idempotency_key(self, idempotency_key: str) -> TrainingMediaTaskRecord | None:
        ...

    def update_media_task(self, task_id: str, updates: dict) -> TrainingMediaTaskRecord | None:
        ...

    def list_media_tasks(self, session_id: str, round_no: int | None = None) -> List[TrainingMediaTaskRecord]:
        ...

    def list_media_tasks_by_status(self, statuses: List[str]) -> List[TrainingMediaTaskRecord]:
        ...

    def claim_media_task(self, task_id: str) -> TrainingMediaTaskRecord | None:
        ...

    def complete_media_task(
        self,
        task_id: str,
        *,
        status: str,
        result_payload: dict | None = None,
        error_payload: dict | None = None,
        retry_count: int | None = None,
    ) -> TrainingMediaTaskRecord | None:
        ...

    def get_training_rounds(self, session_id: str) -> List[TrainingRoundRecord]:
        ...

    def get_training_round_by_session_round(self, session_id: str, round_no: int) -> TrainingRoundRecord | None:
        ...

    def get_round_evaluations_by_session(self, session_id: str) -> List[RoundEvaluationRecord]:
        ...

    def get_round_evaluation_by_round_id(self, round_id: str) -> RoundEvaluationRecord | None:
        ...

    def create_kt_snapshot(self, session_id: str, round_no: int, k_state: dict) -> Any:
        ...

    def create_narrative_snapshot(self, session_id: str, round_no: int, s_state: dict) -> Any:
        ...

    def save_training_round_artifacts(
        self,
        session_id: str,
        round_no: int,
        scenario_id: str,
        user_input_raw: str,
        selected_option: str | None,
        user_action: dict,
        state_before: dict,
        state_after: dict,
        kt_before: dict,
        kt_after: dict,
        feedback_text: str | None,
        evaluation_payload: dict,
        ending_payload: dict | None,
        status: str,
        end_time: datetime | None,
        session_meta: dict | None = None,
        recommendation_log_payload: dict | None = None,
        audit_event_payloads: List[dict] | None = None,
        kt_observation_payload: dict | None = None,
        media_task_specs: List[dict] | None = None,
    ) -> TrainingRoundRecord:
        ...

    def get_ending_result(self, session_id: str) -> EndingResultRecord | None:
        ...

    def get_scenario_recommendation_logs(self, session_id: str) -> List[ScenarioRecommendationLogRecord]:
        ...

    def get_training_audit_events(self, session_id: str) -> List[TrainingAuditEventRecord]:
        ...

    def create_training_audit_event(
        self,
        session_id: str,
        event_type: str,
        round_no: int | None = None,
        payload: dict | None = None,
    ) -> TrainingAuditEventRecord:
        ...

    def get_kt_observations(self, session_id: str) -> List[KtObservationRecord]:
        ...

    def create_kt_observation(
        self,
        session_id: str,
        round_no: int,
        payload: dict,
    ) -> KtObservationRecord:
        ...


class DatabaseTrainingStore:
    """把底层训练持久化实现适配成训练服务关心的稳定接口。

    说明：
    1. 默认走训练域专用仓储，不再默认依赖通用 `DatabaseManager`
    2. 仍保留对旧版自定义 db_manager / fake manager 的兼容，方便渐进迁移
    """

    def __init__(self, storage_backend: Any = None, db_manager: Any = None):
        # `db_manager` 关键字仅作为兼容别名保留，新的默认入口统一叫 storage_backend。
        self.storage_backend = storage_backend or db_manager or SqlAlchemyTrainingRepository()
        # 兼容旧测试和旧调用方：外部如果还在读 `store.db_manager`，这里先保留别名。
        self.db_manager = self.storage_backend

    def create_training_session_artifacts(
        self,
        user_id: str,
        character_id: int | None = None,
        training_mode: str = "guided",
        k_state: dict | None = None,
        s_state: dict | None = None,
        session_meta: dict | None = None,
        audit_event_payload: dict | None = None,
    ) -> TrainingSessionRecord:
        """优先走底层原子初始化接口；老实现不存在时再降级为多次调用。"""
        if hasattr(self.storage_backend, "create_training_session_artifacts"):
            row = self.storage_backend.create_training_session_artifacts(
                user_id=user_id,
                character_id=character_id,
                training_mode=training_mode,
                k_state=k_state,
                s_state=s_state,
                session_meta=session_meta,
                audit_event_payload=audit_event_payload,
            )
            return self._to_training_session_record(row)

        row = self.storage_backend.create_training_session(
            user_id=user_id,
            character_id=character_id,
            training_mode=training_mode,
            k_state=k_state,
            s_state=s_state,
            session_meta=session_meta,
        )
        session_id = getattr(row, "session_id", None)
        if session_id is not None:
            self.storage_backend.create_kt_snapshot(session_id, 0, k_state or {})
            self.storage_backend.create_narrative_snapshot(session_id, 0, s_state or {})
            if audit_event_payload and hasattr(self.storage_backend, "create_training_audit_event"):
                self.storage_backend.create_training_audit_event(
                    session_id=session_id,
                    event_type=str(audit_event_payload.get("event_type") or ""),
                    round_no=audit_event_payload.get("round_no"),
                    payload=audit_event_payload.get("payload"),
                )
        return self._to_training_session_record(row)

    def create_training_session(
        self,
        user_id: str,
        character_id: int | None = None,
        training_mode: str = "guided",
        k_state: dict | None = None,
        s_state: dict | None = None,
        session_meta: dict | None = None,
    ) -> TrainingSessionRecord:
        row = self.storage_backend.create_training_session(
            user_id=user_id,
            character_id=character_id,
            training_mode=training_mode,
            k_state=k_state,
            s_state=s_state,
            session_meta=session_meta,
        )
        return self._to_training_session_record(row)

    def get_training_session(self, session_id: str) -> TrainingSessionRecord | None:
        row = self.storage_backend.get_training_session(session_id)
        return self._to_training_session_record(row)

    def update_training_session(self, session_id: str, updates: dict) -> TrainingSessionRecord | None:
        """更新训练会话，供服务层做惰性回填和增量修复。"""
        row = self.storage_backend.update_training_session(session_id, updates)
        return self._to_training_session_record(row)

    def create_media_task(
        self,
        *,
        session_id: str,
        round_no: int | None,
        task_type: str,
        idempotency_key: str,
        request_payload: dict,
        max_retries: int = 0,
    ) -> TrainingMediaTaskRecord:
        try:
            row = self.storage_backend.create_media_task(
                session_id=session_id,
                round_no=round_no,
                task_type=task_type,
                idempotency_key=idempotency_key,
                request_payload=request_payload,
                max_retries=max_retries,
            )
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="create_media_task",
                    error=exc,
                    details={
                        "session_id": session_id,
                        "round_no": round_no,
                        "task_type": task_type,
                    },
                )
            raise
        return self._to_training_media_task_record(row)

    def get_media_task(self, task_id: str) -> TrainingMediaTaskRecord | None:
        try:
            row = self.storage_backend.get_media_task(task_id)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="get_media_task",
                    error=exc,
                    details={"task_id": task_id},
                )
            raise
        return self._to_training_media_task_record(row)

    def get_media_task_by_idempotency_key(self, idempotency_key: str) -> TrainingMediaTaskRecord | None:
        try:
            row = self.storage_backend.get_media_task_by_idempotency_key(idempotency_key)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="get_media_task_by_idempotency_key",
                    error=exc,
                    details={"idempotency_key": idempotency_key},
                )
            raise
        return self._to_training_media_task_record(row)

    def update_media_task(self, task_id: str, updates: dict) -> TrainingMediaTaskRecord | None:
        try:
            row = self.storage_backend.update_media_task(task_id, updates)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="update_media_task",
                    error=exc,
                    details={"task_id": task_id},
                )
            raise
        return self._to_training_media_task_record(row)

    def list_media_tasks(self, session_id: str, round_no: int | None = None) -> List[TrainingMediaTaskRecord]:
        try:
            rows = self.storage_backend.list_media_tasks(session_id=session_id, round_no=round_no)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="list_media_tasks",
                    error=exc,
                    details={
                        "session_id": session_id,
                        "round_no": round_no,
                    },
                )
            raise
        return [self._to_training_media_task_record(row) for row in rows]

    def list_media_tasks_by_status(self, statuses: List[str]) -> List[TrainingMediaTaskRecord]:
        try:
            rows = self.storage_backend.list_media_tasks_by_status(statuses=statuses)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="list_media_tasks_by_status",
                    error=exc,
                    details={"statuses": list(statuses or [])},
                )
            raise
        return [self._to_training_media_task_record(row) for row in rows]

    def claim_media_task(self, task_id: str) -> TrainingMediaTaskRecord | None:
        try:
            row = self.storage_backend.claim_media_task(task_id)
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="claim_media_task",
                    error=exc,
                    details={"task_id": task_id},
                )
            raise
        return self._to_training_media_task_record(row)

    def complete_media_task(
        self,
        task_id: str,
        *,
        status: str,
        result_payload: dict | None = None,
        error_payload: dict | None = None,
        retry_count: int | None = None,
    ) -> TrainingMediaTaskRecord | None:
        try:
            row = self.storage_backend.complete_media_task(
                task_id,
                status=status,
                result_payload=result_payload,
                error_payload=error_payload,
                retry_count=retry_count,
            )
        except (ProgrammingError, OperationalError, DatabaseError) as exc:
            if _is_missing_training_media_tasks_table_error(exc):
                _raise_media_task_storage_unavailable(
                    operation="complete_media_task",
                    error=exc,
                    details={"task_id": task_id},
                )
            raise
        return self._to_training_media_task_record(row)

    def get_training_rounds(self, session_id: str) -> List[TrainingRoundRecord]:
        return [self._to_training_round_record(row) for row in self.storage_backend.get_training_rounds(session_id)]

    def get_training_round_by_session_round(self, session_id: str, round_no: int) -> TrainingRoundRecord | None:
        row = self.storage_backend.get_training_round_by_session_round(session_id, round_no)
        return self._to_training_round_record(row)

    def get_round_evaluations_by_session(self, session_id: str) -> List[RoundEvaluationRecord]:
        return [self._to_round_evaluation_record(row) for row in self.storage_backend.get_round_evaluations_by_session(session_id)]

    def get_round_evaluation_by_round_id(self, round_id: str) -> RoundEvaluationRecord | None:
        row = self.storage_backend.get_round_evaluation_by_round_id(round_id)
        return self._to_round_evaluation_record(row)

    def create_kt_snapshot(self, session_id: str, round_no: int, k_state: dict) -> Any:
        return self.storage_backend.create_kt_snapshot(session_id, round_no, k_state)

    def create_narrative_snapshot(self, session_id: str, round_no: int, s_state: dict) -> Any:
        return self.storage_backend.create_narrative_snapshot(session_id, round_no, s_state)

    def save_training_round_artifacts(
        self,
        session_id: str,
        round_no: int,
        scenario_id: str,
        user_input_raw: str,
        selected_option: str | None,
        user_action: dict,
        state_before: dict,
        state_after: dict,
        kt_before: dict,
        kt_after: dict,
        feedback_text: str | None,
        evaluation_payload: dict,
        ending_payload: dict | None,
        status: str,
        end_time: datetime | None,
        session_meta: dict | None = None,
        recommendation_log_payload: dict | None = None,
        audit_event_payloads: List[dict] | None = None,
        kt_observation_payload: dict | None = None,
        media_task_specs: List[dict] | None = None,
    ) -> TrainingRoundRecord:
        # 兼容旧版自定义存储后端：如果底层方法还没跟上新增可选参数，只传它能识别的字段。
        row = self._call_storage_backend_method(
            "save_training_round_artifacts",
            session_id=session_id,
            round_no=round_no,
            scenario_id=scenario_id,
            user_input_raw=user_input_raw,
            selected_option=selected_option,
            user_action=user_action,
            state_before=state_before,
            state_after=state_after,
            kt_before=kt_before,
            kt_after=kt_after,
            feedback_text=feedback_text,
            evaluation_payload=evaluation_payload,
            ending_payload=ending_payload,
            status=status,
            end_time=end_time,
            session_meta=session_meta,
            recommendation_log_payload=recommendation_log_payload,
            audit_event_payloads=audit_event_payloads,
            kt_observation_payload=kt_observation_payload,
            media_task_specs=media_task_specs,
        )
        return self._to_training_round_record(row)

    def get_ending_result(self, session_id: str) -> EndingResultRecord | None:
        row = self.storage_backend.get_ending_result(session_id)
        return self._to_ending_result_record(row)

    def get_scenario_recommendation_logs(self, session_id: str) -> List[ScenarioRecommendationLogRecord]:
        rows = self.storage_backend.get_scenario_recommendation_logs(session_id)
        return [self._to_scenario_recommendation_log_record(row) for row in rows]

    def get_training_audit_events(self, session_id: str) -> List[TrainingAuditEventRecord]:
        rows = self.storage_backend.get_training_audit_events(session_id)
        return [self._to_training_audit_event_record(row) for row in rows]

    def create_training_audit_event(
        self,
        session_id: str,
        event_type: str,
        round_no: int | None = None,
        payload: dict | None = None,
    ) -> TrainingAuditEventRecord:
        row = self.storage_backend.create_training_audit_event(
            session_id=session_id,
            event_type=event_type,
            round_no=round_no,
            payload=payload,
        )
        return self._to_training_audit_event_record(row)

    def get_kt_observations(self, session_id: str) -> List[KtObservationRecord]:
        if not hasattr(self.storage_backend, "get_kt_observations"):
            return []
        rows = self.storage_backend.get_kt_observations(session_id)
        return [self._to_kt_observation_record(row) for row in rows]

    def create_kt_observation(
        self,
        session_id: str,
        round_no: int,
        payload: dict,
    ) -> KtObservationRecord:
        if not hasattr(self.storage_backend, "create_kt_observation"):
            raise NotImplementedError("current storage backend does not support kt observation persistence")
        row = self.storage_backend.create_kt_observation(
            session_id=session_id,
            round_no=round_no,
            payload=payload,
        )
        return self._to_kt_observation_record(row)

    def _call_storage_backend_method(self, method_name: str, **kwargs):
        """按底层方法签名裁剪参数，兼容旧版自定义存储实现。"""
        method = getattr(self.storage_backend, method_name)
        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            return method(**kwargs)

        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
            return method(**kwargs)

        supported_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in signature.parameters
        }
        return method(**supported_kwargs)

    def _to_training_session_record(self, row: Any) -> TrainingSessionRecord | None:
        """把底层行对象转换成服务层可依赖的稳定会话模型。"""
        if row is None:
            return None
        return TrainingSessionRecord(
            session_id=str(getattr(row, "session_id")),
            user_id=str(getattr(row, "user_id", "")),
            character_id=getattr(row, "character_id", None),
            training_mode=str(getattr(row, "training_mode", "guided")),
            status=str(getattr(row, "status", "in_progress")),
            current_round_no=int(getattr(row, "current_round_no", 0) or 0),
            current_scenario_id=getattr(row, "current_scenario_id", None),
            k_state=dict(getattr(row, "k_state", {}) or {}),
            s_state=dict(getattr(row, "s_state", {}) or {}),
            session_meta=dict(getattr(row, "session_meta", {}) or {}),
            end_time=getattr(row, "end_time", None),
            created_at=getattr(row, "created_at", None),
            updated_at=getattr(row, "updated_at", None),
        )

    def _to_training_round_record(self, row: Any) -> TrainingRoundRecord | None:
        """把底层回合对象转换成稳定回放模型。"""
        if row is None:
            return None
        return TrainingRoundRecord(
            round_id=str(getattr(row, "round_id")),
            session_id=str(getattr(row, "session_id")),
            round_no=int(getattr(row, "round_no", 0) or 0),
            scenario_id=str(getattr(row, "scenario_id", "")),
            user_input_raw=str(getattr(row, "user_input_raw", "")),
            selected_option=getattr(row, "selected_option", None),
            user_action=dict(getattr(row, "user_action", {}) or {}),
            state_before=dict(getattr(row, "state_before", {}) or {}),
            state_after=dict(getattr(row, "state_after", {}) or {}),
            kt_before=dict(getattr(row, "kt_before", {}) or {}),
            kt_after=dict(getattr(row, "kt_after", {}) or {}),
            feedback_text=getattr(row, "feedback_text", None),
            created_at=getattr(row, "created_at", None),
        )

    def _to_round_evaluation_record(self, row: Any) -> RoundEvaluationRecord | None:
        """把底层评估对象转换成稳定评估模型。"""
        if row is None:
            return None
        return RoundEvaluationRecord(
            round_id=str(getattr(row, "round_id")),
            llm_model=str(getattr(row, "llm_model", "")),
            raw_payload=dict(getattr(row, "raw_payload", {}) or {}),
            risk_flags=list(getattr(row, "risk_flags", []) or []),
        )

    def _to_ending_result_record(self, row: Any) -> EndingResultRecord | None:
        """把底层结局对象转换成稳定结局模型。"""
        if row is None:
            return None
        return EndingResultRecord(
            session_id=str(getattr(row, "session_id")),
            report_payload=dict(getattr(row, "report_payload", {}) or {}),
        )

    def _to_scenario_recommendation_log_record(self, row: Any) -> ScenarioRecommendationLogRecord | None:
        """把底层推荐日志对象转换成稳定读取模型。"""
        if row is None:
            return None
        return ScenarioRecommendationLogRecord(
            recommendation_log_id=str(getattr(row, "recommendation_log_id")),
            session_id=str(getattr(row, "session_id")),
            round_no=int(getattr(row, "round_no", 0) or 0),
            training_mode=str(getattr(row, "training_mode", "guided")),
            selection_source=getattr(row, "selection_source", None),
            recommended_scenario_id=getattr(row, "recommended_scenario_id", None),
            selected_scenario_id=getattr(row, "selected_scenario_id", None),
            candidate_pool=list(getattr(row, "candidate_pool", []) or []),
            recommended_recommendation=dict(getattr(row, "recommended_recommendation", {}) or {}),
            selected_recommendation=dict(getattr(row, "selected_recommendation", {}) or {}),
            decision_context=dict(getattr(row, "decision_context", {}) or {}),
            created_at=getattr(row, "created_at", None),
            updated_at=getattr(row, "updated_at", None),
        )

    def _to_training_audit_event_record(self, row: Any) -> TrainingAuditEventRecord | None:
        """把底层审计事件对象转换成稳定读取模型。"""
        if row is None:
            return None
        return TrainingAuditEventRecord(
            event_id=str(getattr(row, "event_id")),
            session_id=str(getattr(row, "session_id")),
            event_type=str(getattr(row, "event_type", "")),
            round_no=getattr(row, "round_no", None),
            payload=dict(getattr(row, "payload", {}) or {}),
            created_at=getattr(row, "created_at", None),
        )

    def _to_training_media_task_record(self, row: Any) -> TrainingMediaTaskRecord | None:
        """Convert storage rows into stable media task records."""
        if row is None:
            return None
        return TrainingMediaTaskRecord(
            task_id=str(getattr(row, "task_id", "")),
            session_id=str(getattr(row, "session_id", "")),
            round_no=getattr(row, "round_no", None),
            task_type=str(getattr(row, "task_type", "")),
            status=str(getattr(row, "status", "")),
            idempotency_key=str(getattr(row, "idempotency_key", "")),
            request_payload=dict(getattr(row, "request_payload", {}) or {}),
            result_payload=(
                dict(getattr(row, "result_payload", {}) or {})
                if getattr(row, "result_payload", None) is not None
                else None
            ),
            error_payload=(
                dict(getattr(row, "error_payload", {}) or {})
                if getattr(row, "error_payload", None) is not None
                else None
            ),
            retry_count=int(getattr(row, "retry_count", 0) or 0),
            max_retries=int(getattr(row, "max_retries", 0) or 0),
            created_at=getattr(row, "created_at", None),
            updated_at=getattr(row, "updated_at", None),
            started_at=getattr(row, "started_at", None),
            finished_at=getattr(row, "finished_at", None),
        )

    def _to_kt_observation_record(self, row: Any) -> KtObservationRecord | None:
        """把底层 KT 观测对象转换成稳定读取模型。"""
        if row is None:
            return None
        return KtObservationRecord(
            observation_id=str(getattr(row, "observation_id")),
            session_id=str(getattr(row, "session_id")),
            round_no=int(getattr(row, "round_no", 0) or 0),
            scenario_id=str(getattr(row, "scenario_id", "")),
            scenario_title=str(getattr(row, "scenario_title", "")),
            training_mode=str(getattr(row, "training_mode", "guided")),
            primary_skill_code=getattr(row, "primary_skill_code", None),
            primary_risk_flag=getattr(row, "primary_risk_flag", None),
            is_high_risk=bool(getattr(row, "is_high_risk", False)),
            target_skills=list(getattr(row, "target_skills", []) or []),
            weak_skills_before=list(getattr(row, "weak_skills_before", []) or []),
            risk_flags=list(getattr(row, "risk_flags", []) or []),
            focus_tags=list(getattr(row, "focus_tags", []) or []),
            evidence=list(getattr(row, "evidence", []) or []),
            skill_observations=list(getattr(row, "skill_observations", []) or []),
            state_observations=list(getattr(row, "state_observations", []) or []),
            observation_summary=str(getattr(row, "observation_summary", "")),
            raw_payload=dict(getattr(row, "raw_payload", {}) or {}),
            created_at=getattr(row, "created_at", None),
        )
