"""训练场景序列策略。"""

from __future__ import annotations

from typing import Any, Dict, List

from training.constants import TRAINING_DEFAULT_SCENARIO_SEQUENCE, TRAINING_RUNTIME_CONFIG


class ScenarioPolicy:
    """负责场景序列冻结、恢复与提交流程校验。"""

    def __init__(
        self,
        default_sequence: List[Dict[str, str]] | None = None,
        scenario_version: str | None = None,
        enforce_order: bool | None = None,
        runtime_config: Any = None,
    ):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        runtime_default_sequence = [
            {
                "id": str(item.id),
                "title": str(item.title),
            }
            for item in self.runtime_config.scenario.default_sequence
        ]
        # 如果外部没有显式传入，则优先尊重当前运行时配置，而不是模块级默认常量。
        self._default_sequence = self._normalize_sequence(
            default_sequence or runtime_default_sequence or TRAINING_DEFAULT_SCENARIO_SEQUENCE
        )
        self._scenario_version = scenario_version or self.runtime_config.scenario.version
        self._enforce_order = (
            self.runtime_config.switches.enforce_scenario_order if enforce_order is None else bool(enforce_order)
        )

    def get_default_sequence(self) -> List[Dict[str, str]]:
        """返回默认场景序列的副本。"""
        return list(self._default_sequence)

    def build_session_meta(
        self,
        session_sequence: List[Dict[str, Any]] | None = None,
        scenario_payload_sequence: List[Dict[str, Any]] | None = None,
        scenario_payload_catalog: List[Dict[str, Any]] | None = None,
        scenario_bank_version: str | None = None,
        player_profile: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """把冻结后的场景序列写入会话元数据。"""
        sequence = self._normalize_sequence(session_sequence or self._default_sequence)
        meta = {
            "scenario_version": self._scenario_version,
            "scenario_sequence": sequence,
        }
        if scenario_payload_sequence:
            meta["scenario_payload_sequence"] = self._normalize_payload_sequence(scenario_payload_sequence)
        if scenario_payload_catalog:
            # 冻结主线之外的可达分支目录，避免老会话在分支节点回退读取实时场景库。
            meta["scenario_payload_catalog"] = self._normalize_payload_sequence(scenario_payload_catalog)
        if scenario_bank_version:
            meta["scenario_bank_version"] = str(scenario_bank_version)

        normalized_player_profile = self.normalize_player_profile(player_profile)
        if normalized_player_profile:
            # 把玩家档案冻结到会话元数据中，避免业务层分散读写 session_meta 做硬编码。
            meta["player_profile"] = normalized_player_profile
        return meta

    def resolve_session_sequence(self, session: Any) -> List[Dict[str, str]]:
        """优先读取会话冻结序列，缺失时回退默认序列。"""
        session_meta = getattr(session, "session_meta", None)
        if isinstance(session_meta, dict):
            sequence = self._normalize_sequence(session_meta.get("scenario_sequence"))
            if sequence:
                return sequence
        return list(self._default_sequence)

    def read_persisted_session_sequence(self, session: Any) -> List[Dict[str, str]]:
        """只读取持久化会话序列，不对缺失数据做默认兜底。"""
        session_meta = getattr(session, "session_meta", None)
        if isinstance(session_meta, dict):
            return self._normalize_sequence(session_meta.get("scenario_sequence"))
        return []

    def resolve_session_payload_sequence(self, session: Any) -> List[Dict[str, Any]]:
        """优先读取会话冻结的完整场景快照。"""
        session_meta = getattr(session, "session_meta", None)
        if isinstance(session_meta, dict):
            payload_sequence = self._normalize_payload_sequence(session_meta.get("scenario_payload_sequence"))
            if payload_sequence:
                return payload_sequence
        return []

    def resolve_session_payload_catalog(self, session: Any) -> List[Dict[str, Any]]:
        """优先读取会话冻结的完整场景目录，供分支节点稳定回放。"""
        session_meta = getattr(session, "session_meta", None)
        if isinstance(session_meta, dict):
            payload_catalog = self._normalize_payload_sequence(session_meta.get("scenario_payload_catalog"))
            if payload_catalog:
                return payload_catalog
        return []

    def resolve_session_player_profile(self, session: Any) -> Dict[str, Any] | None:
        """优先从会话元数据中读取玩家档案，并统一返回归一化后的结构。"""
        session_meta = getattr(session, "session_meta", None)
        if not isinstance(session_meta, dict):
            return None

        normalized_player_profile = self.normalize_player_profile(session_meta.get("player_profile"))
        return normalized_player_profile or None

    def normalize_player_profile(self, player_profile: Any) -> Dict[str, Any]:
        """归一化玩家档案，允许扩展字段，但保证核心字段稳定。"""
        if not isinstance(player_profile, dict):
            return {}

        normalized: Dict[str, Any] = {}
        known_text_fields = ("name", "gender", "identity")
        for field_name in known_text_fields:
            field_value = str(player_profile.get(field_name) or "").strip()
            if field_value:
                normalized[field_name] = field_value

        age_value = player_profile.get("age")
        if age_value is not None and str(age_value).strip():
            try:
                normalized_age = int(age_value)
            except (TypeError, ValueError):
                normalized_age = None
            if normalized_age is not None and normalized_age >= 0:
                normalized["age"] = normalized_age

        for key, value in player_profile.items():
            normalized_key = str(key or "").strip()
            if not normalized_key or normalized_key in normalized:
                continue
            if value is None:
                continue
            if isinstance(value, str):
                normalized_value = value.strip()
                if normalized_value:
                    normalized[normalized_key] = normalized_value
                continue
            normalized[normalized_key] = value

        return normalized

    def validate_submission(
        self,
        current_round_no: int,
        submitted_scenario_id: str,
        session_sequence: List[Dict[str, str]],
    ) -> None:
        """在开启顺序校验时，校验本回合提交的场景是否合法。"""
        if not self._enforce_order:
            return
        if not session_sequence:
            return

        expected_index = min(current_round_no, len(session_sequence) - 1)
        expected_id = session_sequence[expected_index]["id"]
        if str(submitted_scenario_id) != expected_id:
            raise ValueError(
                f"scenario mismatch: expected={expected_id}, submitted={submitted_scenario_id}, round={current_round_no + 1}"
            )

    def _normalize_sequence(self, sequence: Any) -> List[Dict[str, str]]:
        """把任意输入归一成稳定的场景序列结构。"""
        if not isinstance(sequence, list):
            return []

        normalized: List[Dict[str, str]] = []
        for item in sequence:
            if not isinstance(item, dict):
                continue
            scenario_id = item.get("id")
            if not scenario_id:
                continue
            scenario_id_text = str(scenario_id)
            normalized.append(
                {
                    "id": scenario_id_text,
                    "title": str(item.get("title") or scenario_id_text),
                }
            )
        return normalized

    def _normalize_payload_sequence(self, sequence: Any) -> List[Dict[str, Any]]:
        """把完整场景快照归一为稳定结构，并保留扩展字段。"""
        if not isinstance(sequence, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in sequence:
            if not isinstance(item, dict):
                continue
            scenario_id = str(item.get("id") or "").strip()
            if not scenario_id:
                continue
            payload = dict(item)
            payload["id"] = scenario_id
            payload["title"] = str(item.get("title") or scenario_id)
            payload["phase_tags"] = list(item.get("phase_tags") or [])
            payload["branch_tags"] = list(item.get("branch_tags") or [])
            payload["target_skills"] = list(item.get("target_skills") or [])
            payload["risk_tags"] = list(item.get("risk_tags") or [])
            payload["options"] = [dict(option) for option in item.get("options", []) if isinstance(option, dict)]
            payload["next_rules"] = [dict(rule) for rule in item.get("next_rules", []) if isinstance(rule, dict)]
            normalized.append(payload)
        return normalized
