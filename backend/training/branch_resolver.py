"""训练分支解析器。

这一层负责把运行时 flags 映射成下一场景的分支跳转，
目标是让“世界后果”真正影响后续剧情流转。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

from training.scenario_repository import ScenarioRepository
from training.training_mode import TrainingModeCatalog


def _normalize_text_list(values: Iterable[Any] | None) -> List[str]:
    """统一整理字符串列表，避免规则匹配受脏数据影响。"""
    normalized_values: List[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if not text or text in normalized_values:
            continue
        normalized_values.append(text)
    return normalized_values


@dataclass(slots=True)
class BranchResolution:
    """分支解析结果。"""

    scenario: Dict[str, Any]
    source_scenario_id: str
    target_scenario_id: str
    transition_type: str = "branch"
    reason: str = ""
    matched_rule: Dict[str, Any] | None = None
    triggered_flags: List[str] | None = None

    def to_branch_transition_payload(self) -> Dict[str, Any]:
        """导出可直接附加到场景输出里的分支上下文。"""
        payload = {
            "source_scenario_id": self.source_scenario_id,
            "target_scenario_id": self.target_scenario_id,
            "transition_type": self.transition_type,
            "reason": self.reason,
            "triggered_flags": list(self.triggered_flags or []),
        }
        if self.matched_rule is not None:
            payload["matched_rule"] = dict(self.matched_rule)
        return payload


class BranchResolver:
    """根据场景 `next_rules` 和运行时 flags 解析分支跳转。"""

    def __init__(
        self,
        scenario_repository: ScenarioRepository | None = None,
        runtime_config: Any = None,
    ):
        self.scenario_repository = scenario_repository or ScenarioRepository()
        self.mode_catalog = TrainingModeCatalog(runtime_config=runtime_config)

    def resolve_next_branch(
        self,
        *,
        current_scenario_id: str | None,
        training_mode: str | None,
        runtime_flags: Dict[str, Any] | None,
        scenario_payload_sequence: Sequence[Dict[str, Any]] | None,
        scenario_payload_catalog: Sequence[Dict[str, Any]] | None = None,
    ) -> BranchResolution | None:
        """基于当前场景和运行时状态解析下一步分支。"""
        allow_repository_fallback = not bool(scenario_payload_catalog)
        current_payload = self._find_scenario_payload(
            scenario_id=current_scenario_id,
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
            allow_repository_fallback=allow_repository_fallback,
        )
        if current_payload is None:
            return None

        next_rules = [
            dict(item)
            for item in current_payload.get("next_rules", []) or []
            if isinstance(item, dict)
        ]
        if not next_rules:
            return None

        normalized_training_mode = self.mode_catalog.normalize(
            training_mode,
            default="guided",
            raise_on_unknown=False,
        ) or "guided"
        normalized_runtime_flags = {
            str(key): bool(value)
            for key, value in dict(runtime_flags or {}).items()
            if str(key or "").strip()
        }

        matched_rule = self._match_next_rule(
            next_rules=next_rules,
            training_mode=normalized_training_mode,
            runtime_flags=normalized_runtime_flags,
        )
        if matched_rule is None:
            return None

        target_scenario_id = str(matched_rule.get("go_to") or "").strip()
        if not target_scenario_id:
            return None

        target_payload = self._find_scenario_payload(
            scenario_id=target_scenario_id,
            scenario_payload_sequence=scenario_payload_sequence,
            scenario_payload_catalog=scenario_payload_catalog,
            allow_repository_fallback=allow_repository_fallback,
        )
        if target_payload is None:
            raise ValueError(
                f"branch target scenario not found: source={current_payload.get('id')}, target={target_scenario_id}"
            )

        branch_transition = {
            "source_scenario_id": str(current_payload.get("id") or ""),
            "target_scenario_id": target_scenario_id,
            "transition_type": str(matched_rule.get("transition_type") or "branch"),
            "reason": str(matched_rule.get("reason") or ""),
            # 这里只记录真正命中分支条件的正向 flags，避免把所有为真的运行时状态都污染到报告语义里。
            "triggered_flags": self._resolve_rule_triggered_flags(
                rule=matched_rule,
                runtime_flags=normalized_runtime_flags,
            ),
        }
        branch_transition["matched_rule"] = dict(matched_rule)
        target_payload = dict(target_payload)
        target_payload["branch_transition"] = branch_transition

        return BranchResolution(
            scenario=target_payload,
            source_scenario_id=str(current_payload.get("id") or ""),
            target_scenario_id=target_scenario_id,
            transition_type=branch_transition["transition_type"],
            reason=branch_transition["reason"],
            matched_rule=dict(matched_rule),
            triggered_flags=list(branch_transition["triggered_flags"]),
        )

    def _find_scenario_payload(
        self,
        *,
        scenario_id: str | None,
        scenario_payload_sequence: Sequence[Dict[str, Any]] | None,
        scenario_payload_catalog: Sequence[Dict[str, Any]] | None = None,
        allow_repository_fallback: bool = True,
    ) -> Dict[str, Any] | None:
        """优先在会话冻结快照中查找场景，必要时才兼容回退场景库。"""
        normalized_scenario_id = str(scenario_id or "").strip()
        if not normalized_scenario_id:
            return None

        payload = self._search_payload_collection(scenario_payload_sequence, normalized_scenario_id)
        if payload is not None:
            return payload

        payload = self._search_payload_collection(scenario_payload_catalog, normalized_scenario_id)
        if payload is not None:
            return payload

        if not allow_repository_fallback:
            return None
        repository_payload = self.scenario_repository.get_scenario(normalized_scenario_id)
        return dict(repository_payload) if repository_payload is not None else None

    def _search_payload_collection(
        self,
        payload_collection: Sequence[Dict[str, Any]] | None,
        scenario_id: str,
    ) -> Dict[str, Any] | None:
        """在冻结集合中按场景 ID 查找载荷。"""
        for payload in payload_collection or []:
            if not isinstance(payload, dict):
                continue
            if str(payload.get("id") or "").strip() == scenario_id:
                return dict(payload)
        return None

    def _match_next_rule(
        self,
        *,
        next_rules: Sequence[Dict[str, Any]],
        training_mode: str,
        runtime_flags: Dict[str, bool],
    ) -> Dict[str, Any] | None:
        """按顺序匹配第一条命中的流转规则。"""
        for rule in next_rules:
            if not self._rule_applies_to_mode(rule=rule, training_mode=training_mode):
                continue
            if self._rule_matches_flags(rule=rule, runtime_flags=runtime_flags):
                return dict(rule)
        return None

    def _rule_applies_to_mode(
        self,
        *,
        rule: Dict[str, Any],
        training_mode: str,
    ) -> bool:
        """判断规则是否适用于当前训练模式。"""
        configured_modes = _normalize_text_list(rule.get("modes"))
        if not configured_modes:
            return True

        normalized_modes = {
            normalized_mode
            for item in configured_modes
            for normalized_mode in [self.mode_catalog.normalize(item, raise_on_unknown=False)]
            if normalized_mode
        }
        return training_mode in normalized_modes

    def _rule_matches_flags(
        self,
        *,
        rule: Dict[str, Any],
        runtime_flags: Dict[str, bool],
    ) -> bool:
        """判断规则是否命中当前运行时 flags。"""
        if bool(rule.get("default", False)):
            return True

        when_any_flags = _normalize_text_list(rule.get("when_any_flags"))
        when_all_flags = _normalize_text_list(rule.get("when_all_flags"))
        when_no_flags = _normalize_text_list(rule.get("when_no_flags"))

        if when_any_flags and not any(runtime_flags.get(flag_name, False) for flag_name in when_any_flags):
            return False
        if when_all_flags and not all(runtime_flags.get(flag_name, False) for flag_name in when_all_flags):
            return False
        if when_no_flags and any(runtime_flags.get(flag_name, False) for flag_name in when_no_flags):
            return False

        return bool(when_any_flags or when_all_flags or when_no_flags)

    def _resolve_rule_triggered_flags(
        self,
        *,
        rule: Dict[str, Any],
        runtime_flags: Dict[str, bool],
    ) -> List[str]:
        """提取真正命中当前分支规则的正向 flags。"""
        if bool(rule.get("default", False)):
            return []

        triggered_flags: List[str] = []
        for flag_name in _normalize_text_list(rule.get("when_all_flags")):
            if runtime_flags.get(flag_name, False) and flag_name not in triggered_flags:
                triggered_flags.append(flag_name)

        for flag_name in _normalize_text_list(rule.get("when_any_flags")):
            if runtime_flags.get(flag_name, False) and flag_name not in triggered_flags:
                triggered_flags.append(flag_name)

        return triggered_flags
