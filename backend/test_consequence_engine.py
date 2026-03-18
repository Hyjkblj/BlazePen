"""运行时后果引擎单元测试。"""

from __future__ import annotations

import unittest

from training.consequence_engine import ConsequenceEngine
from training.runtime_state import GameRuntimeFlags, GameRuntimeState


class ConsequenceEngineTestCase(unittest.TestCase):
    """验证后果引擎的关键规则。"""

    def setUp(self):
        self.engine = ConsequenceEngine()

    def _build_runtime_state(self, **overrides) -> GameRuntimeState:
        """构建测试用运行时状态。"""
        base_state = GameRuntimeState(
            session_id="s-engine",
            current_round_no=0,
            current_scene_id="S1",
            k_state={"K1": 0.45, "K2": 0.45, "K3": 0.45, "K4": 0.45, "K5": 0.45, "K6": 0.45, "K7": 0.45, "K8": 0.45},
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            player_profile={"name": "李敏"},
            runtime_flags=GameRuntimeFlags(),
        )
        for key, value in overrides.items():
            setattr(base_state, key, value)
        return GameRuntimeState.from_session(
            base_state,
            round_no=base_state.current_round_no,
            current_scene_id=base_state.current_scene_id,
            k_state=base_state.k_state,
            s_state=base_state.s_state,
            player_profile=base_state.player_profile,
            runtime_flags=base_state.runtime_flags,
        )

    def test_apply_should_trigger_source_exposed_flag(self):
        """来源暴露风险应触发来源暴露事件。"""
        runtime_state = self._build_runtime_state()

        result = self.engine.apply(
            runtime_state=runtime_state,
            evaluation_payload={"risk_flags": ["source_exposure_risk"]},
            round_no=1,
            scenario_payload={"id": "S3", "title": "南京失守高冲突信息处置"},
            selected_option="A",
            recent_risk_rounds=[],
        )

        self.assertTrue(result.runtime_state.runtime_flags.source_exposed)
        self.assertEqual(result.consequence_events[0].event_type, "source_exposed")
        self.assertIn("source_protection", result.branch_hints)

    def test_apply_should_trigger_public_panic_and_high_risk_path(self):
        """连续高风险时，应同时进入公众恐慌和高风险路径。"""
        runtime_state = self._build_runtime_state(
            s_state={
                "credibility": 0.55,
                "accuracy": 0.52,
                "public_panic": 0.82,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            }
        )

        result = self.engine.apply(
            runtime_state=runtime_state,
            evaluation_payload={"risk_flags": ["high_risk_unverified_publish"]},
            round_no=2,
            scenario_payload={"id": "S2", "title": "淞沪会战连续战况"},
            selected_option="B",
            recent_risk_rounds=[["high_risk_unverified_publish"]],
        )

        self.assertTrue(result.runtime_state.runtime_flags.panic_triggered)
        self.assertTrue(result.runtime_state.runtime_flags.high_risk_path)
        self.assertEqual(
            {item.event_type for item in result.consequence_events},
            {"public_panic_triggered", "high_risk_path"},
        )


if __name__ == "__main__":
    unittest.main()
