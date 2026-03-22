"""训练模式规范化与判定工具。"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Set

from training.constants import TRAINING_RUNTIME_CONFIG
from training.exceptions import TrainingModeUnsupportedError


class TrainingModeCatalog:
    """统一处理训练模式别名、规范化和值域校验。"""

    _CANONICAL_ORDER: List[str] = ["guided", "self-paced", "adaptive"]
    _KNOWN_MODES: Set[str] = set(_CANONICAL_ORDER)

    def __init__(self, runtime_config: Any = None):
        self.runtime_config = runtime_config or TRAINING_RUNTIME_CONFIG
        self._recommendation_modes = self._normalize_mode_set(self.runtime_config.recommendation.enabled_modes)
        self._strict_modes = self._normalize_mode_set(self.runtime_config.recommendation.strict_modes)
        self._fallback_mode = self.normalize(
            getattr(self.runtime_config.recommendation, "fallback_mode", "guided"),
            default="guided",
            raise_on_unknown=False,
        ) or "guided"

    @property
    def fallback_mode(self) -> str:
        """返回推荐失败时的兜底模式。"""
        return self._fallback_mode

    def supported_modes(self) -> List[str]:
        """返回对外暴露的训练模式列表。"""
        return list(self._CANONICAL_ORDER)

    def normalize(
        self,
        training_mode: Any,
        default: str | None = None,
        raise_on_unknown: bool = True,
    ) -> Optional[str]:
        """把用户输入或配置值归一为稳定的模式编码。"""
        raw_text = str(training_mode or "").strip()
        if not raw_text:
            if default is None:
                return None
            return self.normalize(default, raise_on_unknown=raise_on_unknown)

        # 把空格、下划线统一折叠成连字符，避免别名散落在业务代码里。
        normalized = re.sub(r"[\s_]+", "-", raw_text.lower())
        if normalized in self._KNOWN_MODES:
            return normalized

        if raise_on_unknown:
            raise TrainingModeUnsupportedError(
                raw_mode=raw_text,
                supported_modes=self.supported_modes(),
            )
        return None

    def is_recommendation_mode(self, training_mode: Any) -> bool:
        """判断当前模式是否启用推荐排序。"""
        normalized = self.normalize(training_mode, raise_on_unknown=False)
        return bool(normalized and normalized in self._recommendation_modes)

    def is_strict_mode(self, training_mode: Any) -> bool:
        """判断当前模式是否必须命中推荐第一题。"""
        normalized = self.normalize(training_mode, raise_on_unknown=False)
        return bool(normalized and normalized in self._strict_modes)

    def _normalize_mode_set(self, modes: Iterable[Any]) -> Set[str]:
        """把配置中的模式列表归一为 canonical set。"""
        normalized_modes: Set[str] = set()
        for item in modes or []:
            normalized = self.normalize(item, raise_on_unknown=False)
            if normalized:
                normalized_modes.add(normalized)
        return normalized_modes
