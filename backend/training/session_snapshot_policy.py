"""训练会话场景快照策略。

这一层专门负责：
1. 冻结新会话的主线场景快照与分支目录
2. 给历史会话做惰性回填
3. 在会话级冻结快照中解析具体场景

这样可以把 `TrainingService` 里的快照生命周期管理职责独立出来，
避免服务层继续膨胀。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

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
        """确保会话已经持久化主线快照与分支目录。"""
        scenario_payload_sequence = self.scenario_policy.resolve_session_payload_sequence(session)
        scenario_payload_catalog = self.scenario_policy.resolve_session_payload_catalog(session)
        if scenario_payload_sequence and scenario_payload_catalog:
            return SessionScenarioSnapshotBundle(
                session=session,
                scenario_payload_sequence=scenario_payload_sequence,
                scenario_payload_catalog=scenario_payload_catalog,
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
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
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
            return scenario_payload

        scenario_payload = self._find_scenario_payload_by_id(scenario_payload_catalog or [], scenario_id)
        if scenario_payload is not None:
            return scenario_payload

        # 只有旧链路完全没有目录快照时，才保留仓储兜底兼容。
        if has_snapshot_catalog:
            return None

        repository_payload = self.scenario_repository.get_scenario(scenario_id)
        return dict(repository_payload) if repository_payload is not None else None

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
