"""训练运行时工件策略单元测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeFlags, GameRuntimeState


class TrainingRuntimeArtifactPolicyTestCase(unittest.TestCase):
    """覆盖运行时 flags、运行时状态和回合工件的主要契约。"""

    def setUp(self):
        self.policy = TrainingRuntimeArtifactPolicy()

    def test_resolve_session_runtime_flags_should_return_stable_default_shape(self):
        """会话缺少 session_meta 时，也应返回稳定的默认 flags 结构。"""
        session = SimpleNamespace(session_meta=None)

        result = self.policy.resolve_session_runtime_flags(session)

        self.assertEqual(
            result,
            {
                "panic_triggered": False,
                "source_exposed": False,
                "editor_locked": False,
                "high_risk_path": False,
            },
        )

    def test_merge_session_meta_runtime_flags_should_preserve_other_fields(self):
        """合并 runtime_flags 时，不应覆盖 session_meta 里的其他业务字段。"""
        session_meta = {
            "scenario_payload_sequence": [{"id": "S1"}],
            "player_profile": {"name": "李敏"},
        }

        result = self.policy.merge_session_meta_runtime_flags(
            session_meta=session_meta,
            runtime_flags={"panic_triggered": True},
        )

        self.assertEqual(result["scenario_payload_sequence"], [{"id": "S1"}])
        self.assertEqual(result["player_profile"]["name"], "李敏")
        self.assertTrue(result["runtime_flags"]["panic_triggered"])
        self.assertFalse(result["runtime_flags"]["source_exposed"])

    def test_build_runtime_state_should_include_player_profile_and_override_flags(self):
        """构建运行时状态时，应优先使用显式覆盖值，并带上玩家档案。"""
        session = SimpleNamespace(
            session_id="s-1",
            current_round_no=2,
            current_scenario_id="S2",
            k_state={"K1": 0.4},
            s_state={"editor_trust": 0.6, "public_panic": 0.2, "source_safety": 0.9},
            session_meta={
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": True,
                    "editor_locked": False,
                    "high_risk_path": False,
                }
            },
        )

        runtime_state = self.policy.build_runtime_state(
            session=session,
            player_profile={"name": "李敏", "identity": "记者"},
            current_round_no=3,
            current_scene_id="S3",
            k_state={"K1": 0.8},
            s_state={"editor_trust": 0.7, "public_panic": 0.1, "source_safety": 0.95},
            runtime_flags={"panic_triggered": True},
        )

        self.assertEqual(runtime_state.current_round_no, 3)
        self.assertEqual(runtime_state.current_scene_id, "S3")
        self.assertEqual(runtime_state.player_profile["name"], "李敏")
        self.assertAlmostEqual(runtime_state.k_state["K1"], 0.8)
        self.assertTrue(runtime_state.runtime_flags.panic_triggered)
        self.assertFalse(runtime_state.runtime_flags.source_exposed)
        self.assertAlmostEqual(runtime_state.state_bar.public_stability, 0.9)

    def test_round_user_action_should_store_and_restore_runtime_artifacts(self):
        """回合 user_action 应能稳定写入并恢复决策上下文、运行时状态和后果事件。"""
        decision_context = {
            "mode": "guided",
            "selection_source": "ordered_sequence",
            "selected_scenario_id": "S1",
            "candidate_pool": [],
        }
        runtime_state = GameRuntimeState(
            session_id="s-1",
            current_round_no=1,
            current_scene_id="S1",
            k_state={"K1": 0.6},
            s_state={"editor_trust": 0.7, "public_panic": 0.1, "source_safety": 0.9},
            player_profile={"name": "李敏"},
            runtime_flags=GameRuntimeFlags(source_exposed=True),
            state_bar=GameRuntimeState.from_session(
                SimpleNamespace(session_id="s-1", current_round_no=1, current_scenario_id="S1", k_state={}, s_state={}),
                s_state={"editor_trust": 0.7, "public_panic": 0.1, "source_safety": 0.9},
            ).state_bar,
        )
        consequence_event = RuntimeConsequenceEvent(
            event_type="source_exposed",
            label="来源暴露",
            summary="来源保护不足，后续需要优先补救。",
            related_flag="source_exposed",
        )

        user_action = self.policy.build_round_user_action(
            user_input="我会先核实消息再写稿。",
            selected_option="A",
            decision_context=self.policy.extract_round_decision_context(
                {"decision_context": decision_context}
            ),
        )
        enriched_user_action = self.policy.attach_runtime_artifacts_to_user_action(
            user_action=user_action,
            runtime_state=runtime_state,
            consequence_events=[consequence_event],
            branch_hints=["source_protection"],
        )

        restored_decision_context = self.policy.extract_round_decision_context(enriched_user_action)
        restored_runtime_state = self.policy.extract_round_runtime_state(enriched_user_action)
        restored_consequence_events = self.policy.extract_round_consequence_events(enriched_user_action)

        self.assertEqual(restored_decision_context.selection_source, "ordered_sequence")
        self.assertTrue(restored_runtime_state.runtime_flags.source_exposed)
        self.assertEqual(restored_consequence_events[0].event_type, "source_exposed")
        self.assertEqual(
            self.policy.extract_round_runtime_flags(enriched_user_action)["source_exposed"],
            True,
        )


if __name__ == "__main__":
    unittest.main()
