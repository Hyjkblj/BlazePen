"""训练运行时状态模型。

这一层负责把训练会话里分散的 K/S 状态、玩家档案和世界 flags
聚合成统一的运行时对象，供后果引擎、报告和接口输出复用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """统一裁剪数值区间，避免前后端看到越界状态。"""
    return max(lower, min(upper, float(value)))


def _resolve_state_value(
    override_state: Dict[str, Any] | None,
    session_state: Dict[str, Any] | None,
    code: str,
    default_value: float,
) -> float:
    """统一读取状态值，优先使用显式覆盖值。"""
    if isinstance(override_state, dict) and code in override_state:
        return float(override_state.get(code, default_value) or 0.0)
    if isinstance(session_state, dict) and code in session_state:
        return float(session_state.get(code, default_value) or 0.0)
    return float(default_value)


@dataclass(slots=True)
class GameRuntimeFlags:
    """运行时世界 flags。

    第一阶段只保留最核心的四个世界状态开关，
    后续如要扩展失败分支、补救分支，再继续加字段。
    """

    panic_triggered: bool = False
    source_exposed: bool = False
    editor_locked: bool = False
    high_risk_path: bool = False

    @classmethod
    def from_payload(cls, payload: Dict[str, Any] | None) -> "GameRuntimeFlags":
        """从任意字典恢复稳定 flags 结构。"""
        source = payload if isinstance(payload, dict) else {}
        return cls(
            panic_triggered=bool(source.get("panic_triggered", False)),
            source_exposed=bool(source.get("source_exposed", False)),
            editor_locked=bool(source.get("editor_locked", False)),
            high_risk_path=bool(source.get("high_risk_path", False)),
        )

    def to_dict(self) -> Dict[str, bool]:
        """导出稳定 flags 字典。"""
        return {
            "panic_triggered": bool(self.panic_triggered),
            "source_exposed": bool(self.source_exposed),
            "editor_locked": bool(self.editor_locked),
            "high_risk_path": bool(self.high_risk_path),
        }


@dataclass(slots=True)
class GameStateBar:
    """前端/CLI 可直接消费的状态条。"""

    editor_trust: float = 0.0
    public_stability: float = 0.0
    source_safety: float = 0.0

    @classmethod
    def from_s_state(cls, s_state: Dict[str, Any] | None) -> "GameStateBar":
        """从 S 状态映射出玩家能直接感知的世界状态条。"""
        source = s_state if isinstance(s_state, dict) else {}
        public_panic = _clamp(source.get("public_panic", DEFAULT_S_STATE.get("public_panic", 0.0)))
        return cls(
            editor_trust=round(_clamp(source.get("editor_trust", DEFAULT_S_STATE.get("editor_trust", 0.0))), 4),
            public_stability=round(_clamp(1.0 - public_panic), 4),
            source_safety=round(_clamp(source.get("source_safety", DEFAULT_S_STATE.get("source_safety", 0.0))), 4),
        )

    def to_dict(self) -> Dict[str, float]:
        """导出稳定状态条。"""
        return {
            "editor_trust": round(_clamp(self.editor_trust), 4),
            "public_stability": round(_clamp(self.public_stability), 4),
            "source_safety": round(_clamp(self.source_safety), 4),
        }


@dataclass(slots=True)
class GameRuntimeState:
    """训练引擎升级后的统一运行时状态。"""

    session_id: str
    current_round_no: int
    current_scene_id: str | None = None
    k_state: Dict[str, float] = field(default_factory=dict)
    s_state: Dict[str, float] = field(default_factory=dict)
    player_profile: Dict[str, Any] = field(default_factory=dict)
    runtime_flags: GameRuntimeFlags = field(default_factory=GameRuntimeFlags)
    state_bar: GameStateBar = field(default_factory=GameStateBar)

    @classmethod
    def from_session(
        cls,
        session: Any,
        *,
        round_no: int | None = None,
        current_scene_id: str | None = None,
        k_state: Dict[str, Any] | None = None,
        s_state: Dict[str, Any] | None = None,
        player_profile: Dict[str, Any] | None = None,
        runtime_flags: Dict[str, Any] | GameRuntimeFlags | None = None,
    ) -> "GameRuntimeState":
        """基于会话对象聚合出统一运行时状态。"""
        session_meta = getattr(session, "session_meta", None)
        session_meta = session_meta if isinstance(session_meta, dict) else {}
        session_k_state = getattr(session, "k_state", None)
        session_s_state = getattr(session, "s_state", None)

        normalized_k_state = {
            code: round(_clamp(_resolve_state_value(k_state, session_k_state, code, DEFAULT_K_STATE[code])), 4)
            for code in DEFAULT_K_STATE.keys()
        }
        normalized_s_state = {
            code: round(_clamp(_resolve_state_value(s_state, session_s_state, code, DEFAULT_S_STATE[code])), 4)
            for code in DEFAULT_S_STATE.keys()
        }

        normalized_runtime_flags = (
            runtime_flags
            if isinstance(runtime_flags, GameRuntimeFlags)
            else GameRuntimeFlags.from_payload(runtime_flags or session_meta.get("runtime_flags"))
        )
        normalized_player_profile = dict(player_profile or session_meta.get("player_profile") or {})

        return cls(
            session_id=str(getattr(session, "session_id", "") or ""),
            current_round_no=int(
                round_no
                if round_no is not None
                else getattr(session, "current_round_no", 0) or 0
            ),
            current_scene_id=(
                str(current_scene_id)
                if current_scene_id is not None and str(current_scene_id).strip()
                else (
                    str(getattr(session, "current_scenario_id"))
                    if getattr(session, "current_scenario_id", None) is not None
                    and str(getattr(session, "current_scenario_id")).strip()
                    else None
                )
            ),
            k_state=normalized_k_state,
            s_state=normalized_s_state,
            player_profile=normalized_player_profile,
            runtime_flags=normalized_runtime_flags,
            state_bar=GameStateBar.from_s_state(normalized_s_state),
        )

    def to_dict(self) -> Dict[str, Any]:
        """导出运行时状态字典，供接口和持久化复用。"""
        payload: Dict[str, Any] = {
            "current_round_no": int(self.current_round_no),
            "k_state": dict(self.k_state),
            "s_state": dict(self.s_state),
            "runtime_flags": self.runtime_flags.to_dict(),
            "state_bar": self.state_bar.to_dict(),
        }
        if self.current_scene_id is not None:
            payload["current_scene_id"] = self.current_scene_id
        if self.player_profile:
            payload["player_profile"] = dict(self.player_profile)
        return payload
