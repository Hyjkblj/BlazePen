"""运行时状态聚合单元测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from training.runtime_state import GameRuntimeFlags, GameRuntimeState


class GameRuntimeStateTestCase(unittest.TestCase):
    """验证运行时状态的聚合逻辑。"""

    def test_from_session_should_merge_state_and_runtime_flags(self):
        """运行时状态应优先使用显式覆盖值，并保留 session_meta 中的 flags。"""
        session = SimpleNamespace(
            session_id="s-runtime",
            current_round_no=2,
            current_scenario_id="S2",
            k_state={"K1": 0.4, "K2": 0.5},
            s_state={
                "credibility": 0.6,
                "accuracy": 0.7,
                "public_panic": 0.2,
                "source_safety": 0.8,
                "editor_trust": 0.9,
                "actionability": 0.5,
            },
            session_meta={
                "player_profile": {"name": "李敏", "identity": "战地记者"},
                "runtime_flags": {
                    "panic_triggered": True,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": True,
                },
            },
        )

        runtime_state = GameRuntimeState.from_session(
            session,
            round_no=3,
            current_scene_id="S3",
            k_state={"K1": 0.8},
            s_state={"public_panic": 0.35, "source_safety": 0.6, "editor_trust": 0.55},
        )

        self.assertEqual(runtime_state.current_round_no, 3)
        self.assertEqual(runtime_state.current_scene_id, "S3")
        self.assertEqual(runtime_state.player_profile["name"], "李敏")
        self.assertEqual(runtime_state.k_state["K1"], 0.8)
        self.assertAlmostEqual(runtime_state.state_bar.public_stability, 0.65)
        self.assertTrue(runtime_state.runtime_flags.panic_triggered)
        self.assertTrue(runtime_state.runtime_flags.high_risk_path)

    def test_runtime_flags_to_dict_should_keep_stable_shape(self):
        """运行时 flags 导出时应保持稳定结构。"""
        flags = GameRuntimeFlags(source_exposed=True)

        self.assertEqual(
            flags.to_dict(),
            {
                "panic_triggered": False,
                "source_exposed": True,
                "editor_locked": False,
                "high_risk_path": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
