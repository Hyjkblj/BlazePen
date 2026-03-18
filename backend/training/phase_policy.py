"""训练阶段解析策略。

这一层负责把“当前轮次处于哪个训练阶段”从推荐策略和服务编排里抽离出来，
让推荐、审计、诊断都复用同一套阶段解析结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from training.constants import TRAINING_RUNTIME_CONFIG
from training.training_mode import TrainingModeCatalog


@dataclass(slots=True)
class TrainingPhaseSnapshot:
    """单个训练轮次的阶段快照。"""

    round_no: int
    phase_tags: List[str] = field(default_factory=list)
    window_reasons: List[str] = field(default_factory=list)
    matched_window_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定字典，便于审计事件和诊断接口复用。"""
        return {
            "round_no": int(self.round_no),
            "phase_tags": list(self.phase_tags),
            "window_reasons": list(self.window_reasons),
            "matched_window_count": int(self.matched_window_count),
        }


class TrainingPhasePolicy:
    """统一解析训练阶段窗口。"""

    def __init__(self, runtime_config: Any = None):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self.mode_catalog = TrainingModeCatalog(runtime_config=self.runtime_config)

    def resolve_next_round_phase(
        self,
        training_mode: str,
        current_round_no: int,
        total_rounds: int,
    ) -> TrainingPhaseSnapshot:
        """按“当前已完成轮次”解析下一轮将进入的阶段。"""
        next_round_no = self._normalize_round_no(int(current_round_no) + 1, total_rounds)
        return self.resolve_round_phase(
            training_mode=training_mode,
            round_no=next_round_no,
            total_rounds=total_rounds,
        )

    def resolve_round_phase(
        self,
        training_mode: str,
        round_no: int,
        total_rounds: int,
    ) -> TrainingPhaseSnapshot:
        """按具体轮次解析当前阶段。"""
        normalized_round_no = self._normalize_round_no(round_no, total_rounds)
        phase_tags: List[str] = []
        window_reasons: List[str] = []
        matched_window_count = 0

        for stage_window in getattr(self.runtime_config.flow, "stage_windows", []) or []:
            if not self._stage_window_applies_to_mode(stage_window, training_mode):
                continue

            start_round = max(int(getattr(stage_window, "start_round", 1) or 1), 1)
            raw_end_round = getattr(stage_window, "end_round", None)
            if raw_end_round in (None, ""):
                end_round = max(start_round, int(total_rounds or start_round))
            else:
                end_round = max(start_round, int(raw_end_round))
            if not start_round <= normalized_round_no <= end_round:
                continue

            matched_window_count += 1
            for phase_tag in self._normalize_text_list(getattr(stage_window, "phase_tags", [])):
                if phase_tag not in phase_tags:
                    phase_tags.append(phase_tag)

            reason = str(getattr(stage_window, "reason", "") or "").strip()
            if reason and reason not in window_reasons:
                window_reasons.append(reason)

        return TrainingPhaseSnapshot(
            round_no=normalized_round_no,
            phase_tags=phase_tags,
            window_reasons=window_reasons,
            matched_window_count=matched_window_count,
        )

    def has_phase_transition(
        self,
        previous_phase_snapshot: TrainingPhaseSnapshot | None,
        current_phase_snapshot: TrainingPhaseSnapshot | None,
    ) -> bool:
        """判断当前轮是否发生了阶段切换。"""
        if previous_phase_snapshot is None or current_phase_snapshot is None:
            return False
        return list(previous_phase_snapshot.phase_tags) != list(current_phase_snapshot.phase_tags)

    def _normalize_round_no(self, round_no: int, total_rounds: int) -> int:
        """把轮次统一收敛到安全区间，避免脏参数影响阶段解析。"""
        normalized_round_no = max(int(round_no), 1)
        if total_rounds > 0:
            normalized_round_no = min(normalized_round_no, int(total_rounds))
        return normalized_round_no

    def _stage_window_applies_to_mode(self, stage_window: Any, training_mode: str) -> bool:
        """判断阶段窗口是否适用于当前训练模式。"""
        configured_modes = list(getattr(stage_window, "modes", []) or [])
        if not configured_modes:
            return True

        normalized_training_mode = self.mode_catalog.normalize(
            training_mode,
            default="guided",
            raise_on_unknown=False,
        ) or "guided"
        normalized_modes = {
            normalized_mode
            for item in configured_modes
            for normalized_mode in [self.mode_catalog.normalize(item, raise_on_unknown=False)]
            if normalized_mode
        }
        return normalized_training_mode in normalized_modes

    def _normalize_text_list(self, values: Sequence[Any] | None) -> List[str]:
        """把标签数组规整成去重后的稳定字符串列表。"""
        normalized_values: List[str] = []
        for value in values or []:
            text = str(value or "").strip()
            if not text or text in normalized_values:
                continue
            normalized_values.append(text)
        return normalized_values
