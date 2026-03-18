"""训练运行时后果事件定义。

这一层负责把“世界发生了什么”做成稳定、可回放、可审计的结构化事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from training.runtime_state import GameStateBar

EVENT_PUBLIC_PANIC_TRIGGERED = "public_panic_triggered"
EVENT_SOURCE_EXPOSED = "source_exposed"
EVENT_EDITOR_LOCKED = "editor_locked"
EVENT_HIGH_RISK_PATH = "high_risk_path"
EVENT_STABILITY_RESTORED = "stability_restored"
EVENT_EDITOR_TRUST_RECOVERED = "editor_trust_recovered"


@dataclass(slots=True)
class RuntimeConsequenceEvent:
    """单个运行时后果事件。"""

    event_type: str
    label: str
    summary: str
    severity: str = "medium"
    round_no: int | None = None
    related_flag: str | None = None
    state_bar: GameStateBar | None = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """导出稳定事件字典。"""
        event_payload: Dict[str, Any] = {
            "event_type": self.event_type,
            "label": self.label,
            "summary": self.summary,
            "severity": self.severity,
            "payload": dict(self.payload),
        }
        if self.round_no is not None:
            event_payload["round_no"] = int(self.round_no)
        if self.related_flag is not None:
            event_payload["related_flag"] = self.related_flag
        if self.state_bar is not None:
            event_payload["state_bar"] = self.state_bar.to_dict()
        return event_payload
