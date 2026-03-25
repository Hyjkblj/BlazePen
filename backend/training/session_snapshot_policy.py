"""训练会话场景快照策略。

这一层专门负责：
1. 冻结新会话的主线场景快照与分支目录
2. 显式校验会话是否具备可恢复快照事实
3. 给历史会话执行独立 repair/backfill（不走主链路热路径）
4. 在会话级冻结快照中解析具体场景

这样可以把 `TrainingService` 里的快照生命周期管理职责独立出来，
避免服务层继续膨胀。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from training.exceptions import TrainingSessionRecoveryStateError
from training.scenario_policy import ScenarioPolicy
from training.scenario_repository import ScenarioRepository
from training.training_store import TrainingStoreProtocol


@dataclass(slots=True)
class SessionScenarioSnapshotBundle:
    """会话级场景快照结果。"""

    scenario_payload_sequence: List[Dict[str, Any]]
    scenario_payload_catalog: List[Dict[str, Any]]
    session: Any | None = None


class SessionScenarioSnapshotPolicy:
    """负责训练会话的场景快照冻结、回填与解析。"""

    def __init__(
        self,
        scenario_policy: ScenarioPolicy | None = None,
        scenario_repository: ScenarioRepository | None = None,
    ):
        self.scenario_policy = scenario_policy or ScenarioPolicy()
        self.scenario_repository = scenario_repository or ScenarioRepository()

    def freeze_session_snapshots(
        self,
        session_sequence: List[Dict[str, Any]],
    ) -> SessionScenarioSnapshotBundle:
        """冻结新会话的主线快照和可达分支目录。"""
        scenario_payload_sequence = self.scenario_repository.freeze_sequence(session_sequence)
        scenario_payload_catalog = self.scenario_repository.freeze_related_catalog(scenario_payload_sequence)
        return SessionScenarioSnapshotBundle(
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
        )

    def ensure_session_snapshots(
        self,
        *,
        session: Any,
        training_store: TrainingStoreProtocol,
    ) -> SessionScenarioSnapshotBundle:
        """显式修复缺失的会话快照并持久化回填结果。

        该入口只应由 repair/migration 任务调用。请求热路径必须改用
        `require_session_snapshots(...)`，避免运行时静默修复损坏会话。
        """
        scenario_payload_sequence = self.scenario_policy.resolve_session_payload_sequence(session)
        scenario_payload_catalog = self.scenario_policy.resolve_session_payload_catalog(session)
        if scenario_payload_sequence and scenario_payload_catalog:
            normalized_sequence = self._normalize_snapshot_payloads(scenario_payload_sequence)
            normalized_catalog = self._normalize_snapshot_payloads(scenario_payload_catalog)
            return SessionScenarioSnapshotBundle(
                session=session,
                scenario_payload_sequence=normalized_sequence,
                scenario_payload_catalog=normalized_catalog,
            )

        updated_session_meta = dict(getattr(session, "session_meta", None) or {})
        if not scenario_payload_sequence:
            session_sequence = self.scenario_policy.resolve_session_sequence(session)
            scenario_payload_sequence = self.scenario_repository.freeze_sequence(session_sequence)
            updated_session_meta["scenario_payload_sequence"] = scenario_payload_sequence

        if not scenario_payload_catalog:
            scenario_payload_catalog = self.scenario_repository.freeze_related_catalog(scenario_payload_sequence)
            updated_session_meta["scenario_payload_catalog"] = scenario_payload_catalog

        updated_session = self._persist_session_meta_backfill(
            session=session,
            session_meta=updated_session_meta,
            training_store=training_store,
        )
        return SessionScenarioSnapshotBundle(
            session=updated_session,
            scenario_payload_sequence=self._normalize_snapshot_payloads(scenario_payload_sequence),
            scenario_payload_catalog=self._normalize_snapshot_payloads(scenario_payload_catalog),
        )

    def require_session_snapshots(
        self,
        *,
        session_id: str,
        session: Any,
    ) -> SessionScenarioSnapshotBundle:
        """Read persisted session snapshots and fail when recovery facts are missing."""
        snapshot_bundle = self.read_session_snapshots(session=session)
        missing_fields: List[str] = []
        if not snapshot_bundle.scenario_payload_sequence:
            missing_fields.append("scenario_payload_sequence")
        if not snapshot_bundle.scenario_payload_catalog:
            missing_fields.append("scenario_payload_catalog")
        if missing_fields:
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_snapshots_missing",
                details={
                    "current_round_no": int(getattr(session, "current_round_no", 0) or 0),
                    "missing_fields": missing_fields,
                },
            )
        return snapshot_bundle

    def read_session_snapshots(
        self,
        *,
        session: Any,
    ) -> SessionScenarioSnapshotBundle:
        """只读取已持久化的会话快照，不做任何修复或回写。"""
        scenario_payload_sequence = self.scenario_policy.resolve_session_payload_sequence(session)
        scenario_payload_catalog = self.scenario_policy.resolve_session_payload_catalog(session)
        return SessionScenarioSnapshotBundle(
            session=session,
            scenario_payload_sequence=self._normalize_snapshot_payloads(scenario_payload_sequence),
            scenario_payload_catalog=self._normalize_snapshot_payloads(scenario_payload_catalog),
        )

    def resolve_scenario_payload_by_id(
        self,
        *,
        scenario_id: str,
        scenario_payload_sequence: List[Dict[str, Any]],
        scenario_payload_catalog: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any] | None:
        """优先从会话冻结快照里定位具体场景。"""
        has_snapshot_catalog = bool(scenario_payload_catalog)
        scenario_payload = self._find_scenario_payload_by_id(scenario_payload_sequence, scenario_id)
        if scenario_payload is not None:
            return self._normalize_single_snapshot_payload(scenario_payload)

        scenario_payload = self._find_scenario_payload_by_id(scenario_payload_catalog or [], scenario_id)
        if scenario_payload is not None:
            return self._normalize_single_snapshot_payload(scenario_payload)

        # 只有旧链路完全没有目录快照时，才保留仓储兜底兼容。
        if has_snapshot_catalog:
            return None

        repository_payload = self.scenario_repository.get_scenario(scenario_id)
        return (
            self._normalize_single_snapshot_payload(dict(repository_payload))
            if repository_payload is not None
            else None
        )

    def _persist_session_meta_backfill(
        self,
        *,
        session: Any,
        session_meta: Dict[str, Any],
        training_store: TrainingStoreProtocol,
    ) -> Any:
        """把惰性补齐后的会话元数据回写到存储层。"""
        session_id = str(getattr(session, "session_id", "") or "").strip()
        normalized_session_meta = dict(session_meta or {})
        if not session_id:
            setattr(session, "session_meta", normalized_session_meta)
            return session

        updated_session = training_store.update_training_session(
            session_id,
            {"session_meta": normalized_session_meta},
        )
        if updated_session is not None:
            return updated_session

        setattr(session, "session_meta", normalized_session_meta)
        return session

    def _find_scenario_payload_by_id(
        self,
        scenario_payloads: List[Dict[str, Any]],
        scenario_id: str,
    ) -> Dict[str, Any] | None:
        """按场景 ID 在冻结集合中查找载荷。"""
        normalized_scenario_id = str(scenario_id or "").strip()
        if not normalized_scenario_id:
            return None

        for payload in scenario_payloads or []:
            if not isinstance(payload, dict):
                continue
            if str(payload.get("id") or "").strip() == normalized_scenario_id:
                return dict(payload)
        return None

    def _normalize_snapshot_payloads(
        self,
        scenario_payloads: List[Dict[str, Any]] | None,
    ) -> List[Dict[str, Any]]:
        normalized_payloads: List[Dict[str, Any]] = []
        for payload in scenario_payloads or []:
            if not isinstance(payload, dict):
                continue
            normalized_payloads.append(self._normalize_single_snapshot_payload(payload))
        return normalized_payloads

    def _normalize_single_snapshot_payload(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized_payload = dict(payload or {})
        canonical_brief = str(normalized_payload.get("brief") or "").strip()
        if not canonical_brief:
            legacy_brief = str(normalized_payload.get("briefing") or "").strip()
            normalized_payload["brief"] = legacy_brief
        normalized_payload.pop("briefing", None)
        return normalized_payload
