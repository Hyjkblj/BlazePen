"""训练报告上下文策略单元测试。"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from training.constants import DEFAULT_K_STATE, DEFAULT_S_STATE
from training.report_context_policy import TrainingReportContextPolicy


class TrainingReportContextPolicyTestCase(unittest.TestCase):
    """覆盖报告起点、history 和 round_snapshots 的主要组装逻辑。"""

    def setUp(self):
        self.policy = TrainingReportContextPolicy()

    def test_resolve_report_initial_states_should_prefer_first_round_before_states(self):
        """有历史回合时，报告起点应优先使用首轮 before 状态。"""
        session = SimpleNamespace(
            k_state={"K1": 0.9},
            s_state={"editor_trust": 0.9},
        )
        rounds = [
            SimpleNamespace(
                kt_before={"K1": 0.2},
                state_before={"editor_trust": 0.4, "public_panic": 0.1, "source_safety": 0.8},
            )
        ]

        initial_k_state, initial_s_state = self.policy.resolve_report_initial_states(
            session=session,
            rounds=rounds,
        )

        self.assertEqual(initial_k_state["K1"], 0.2)
        self.assertEqual(initial_s_state["editor_trust"], 0.4)

    def test_build_report_history_should_restore_runtime_artifacts(self):
        """报告 history 应能从 user_action 中恢复决策上下文、运行时状态和后果事件。"""
        round_row = SimpleNamespace(
            round_id="r-1",
            round_no=1,
            scenario_id="S1",
            user_input_raw="hello",
            selected_option="A",
            kt_before={"K1": 0.2},
            kt_after={"K1": 0.5},
            state_before={"editor_trust": 0.5, "public_panic": 0.1, "source_safety": 0.8},
            state_after={"editor_trust": 0.6, "public_panic": 0.0, "source_safety": 0.8},
            created_at=datetime(2026, 3, 19, 12, 0, 0),
            user_action={
                "decision_context": {
                    "mode": "guided",
                    "selection_source": "ordered_sequence",
                    "selected_scenario_id": "S1",
                    "candidate_pool": [],
                },
                "runtime_state": {
                    "current_round_no": 1,
                    "current_scene_id": "S1",
                    "k_state": {"K1": 0.5},
                    "s_state": {"editor_trust": 0.6, "public_panic": 0.0, "source_safety": 0.8},
                    "runtime_flags": {"source_exposed": True},
                    "state_bar": {"editor_trust": 0.6, "public_stability": 1.0, "source_safety": 0.8},
                },
                "consequence_events": [
                    {
                        "event_type": "source_exposed",
                        "label": "来源暴露",
                        "summary": "来源保护不足。",
                        "severity": "medium",
                    }
                ],
            },
        )
        evaluation_row = SimpleNamespace(
            raw_payload={
                "llm_model": "rules_v1",
                "confidence": 0.8,
                "risk_flags": ["source_exposure_risk"],
                "skill_delta": {"K1": 0.3},
                "s_delta": {},
                "evidence": ["ok"],
            }
        )
        kt_observation_row = SimpleNamespace(
            round_no=1,
            scenario_id="S1",
            scenario_title="卢沟桥",
            training_mode="guided",
            primary_skill_code="K1",
            primary_risk_flag="source_exposure_risk",
            is_high_risk=True,
            target_skills=["K1"],
            weak_skills_before=["K1"],
            risk_flags=["source_exposure_risk"],
            focus_tags=["K1"],
            evidence=["ok"],
            skill_observations=[],
            state_observations=[],
            observation_summary="summary",
        )

        history = self.policy.build_report_history(
            rounds=[round_row],
            eval_map={"r-1": evaluation_row},
            kt_observation_map={1: kt_observation_row},
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].evaluation.risk_flags, ["source_exposure_risk"])
        self.assertEqual(history[0].decision_context.selection_source, "ordered_sequence")
        self.assertTrue(history[0].runtime_state.runtime_flags.source_exposed)
        self.assertEqual(history[0].consequence_events[0].event_type, "source_exposed")
        self.assertEqual(history[0].kt_observation.primary_skill_code, "K1")

    def test_build_report_round_snapshots_should_fallback_to_evaluation_risk_flags(self):
        """缺少 KT 观测时，round_snapshots 应回退到评估结果补齐风险字段。"""
        round_row = SimpleNamespace(
            round_id="r-1",
            round_no=1,
            scenario_id="S1",
            kt_after={"K1": 0.5},
            state_after={"editor_trust": 0.6, "public_panic": 0.2, "source_safety": 0.8},
            created_at=datetime(2026, 3, 19, 12, 0, 0),
            user_action={
                "decision_context": {
                    "mode": "guided",
                    "selection_source": "branch_transition",
                    "selected_scenario_id": "S1",
                    "candidate_pool": [],
                    "selected_branch_transition": {
                        "source_scenario_id": "S0",
                        "target_scenario_id": "S1",
                        "transition_type": "branch",
                        "triggered_flags": ["panic_triggered"],
                    },
                },
                "runtime_state": {
                    "current_round_no": 1,
                    "k_state": {"K1": 0.5},
                    "s_state": {"editor_trust": 0.6, "public_panic": 0.2, "source_safety": 0.8},
                    "runtime_flags": {"panic_triggered": True},
                    "state_bar": {"editor_trust": 0.6, "public_stability": 0.8, "source_safety": 0.8},
                },
                "consequence_events": [
                    {
                        "event_type": "public_panic_triggered",
                        "label": "公众恐慌",
                        "summary": "公众稳定度下降。",
                        "severity": "high",
                    }
                ],
            },
        )
        evaluation_row = SimpleNamespace(
            raw_payload={
                "risk_flags": ["high_risk_unverified_publish"],
                "skill_delta": {},
                "s_delta": {},
                "evidence": ["risk"],
            }
        )

        snapshots = self.policy.build_report_round_snapshots(
            rounds=[round_row],
            eval_map={"r-1": evaluation_row},
            kt_observation_map={},
            scenario_title_map={"S1": "卢沟桥"},
        )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["scenario_title"], "卢沟桥")
        self.assertEqual(snapshots[0]["risk_flags"], ["high_risk_unverified_publish"])
        self.assertTrue(snapshots[0]["runtime_flags"]["panic_triggered"])
        self.assertEqual(snapshots[0]["consequence_events"][0]["event_type"], "public_panic_triggered")
        self.assertEqual(snapshots[0]["branch_transition"]["target_scenario_id"], "S1")

    def test_build_report_history_should_tolerate_dirty_state_values(self):
        """脏历史状态值不应打挂报告 history，应逐字段回退默认值或裁剪边界。"""
        round_row = SimpleNamespace(
            round_id="r-dirty-history",
            round_no=1,
            scenario_id="S1",
            user_input_raw="dirty",
            selected_option="A",
            kt_before={"K1": "bad"},
            kt_after={"K1": "1.5"},
            state_before={"editor_trust": "bad", "public_panic": "-1", "source_safety": "nan"},
            state_after={"editor_trust": "0.7", "public_panic": "1.4", "source_safety": None},
            created_at=datetime(2026, 3, 19, 12, 10, 0),
            user_action={},
        )

        history = self.policy.build_report_history(
            rounds=[round_row],
            eval_map={},
            kt_observation_map={},
        )

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].k_state_before["K1"], DEFAULT_K_STATE["K1"])
        self.assertEqual(history[0].k_state_after["K1"], 1.0)
        self.assertEqual(history[0].s_state_before["editor_trust"], DEFAULT_S_STATE["editor_trust"])
        self.assertEqual(history[0].s_state_before["public_panic"], 0.0)
        self.assertEqual(history[0].s_state_before["source_safety"], DEFAULT_S_STATE["source_safety"])
        self.assertEqual(history[0].s_state_after["editor_trust"], 0.7)
        self.assertEqual(history[0].s_state_after["public_panic"], 1.0)
        self.assertEqual(history[0].s_state_after["source_safety"], DEFAULT_S_STATE["source_safety"])

    def test_build_report_round_snapshots_should_tolerate_dirty_state_values(self):
        """脏历史状态值不应打挂 round_snapshots，应输出安全归一化后的快照。"""
        round_row = SimpleNamespace(
            round_id="r-dirty-snapshot",
            round_no=2,
            scenario_id="S2",
            kt_after={"K1": "bad", "K2": "0.8"},
            state_after={"editor_trust": "oops", "public_panic": "inf", "source_safety": "-0.3"},
            created_at=datetime(2026, 3, 19, 12, 20, 0),
            user_action={},
        )
        evaluation_row = SimpleNamespace(
            raw_payload={
                "risk_flags": ["source_exposure_risk"],
                "skill_delta": {},
                "s_delta": {},
                "evidence": ["risk"],
            }
        )

        snapshots = self.policy.build_report_round_snapshots(
            rounds=[round_row],
            eval_map={"r-dirty-snapshot": evaluation_row},
            kt_observation_map={},
            scenario_title_map={"S2": "淞沪会战"},
        )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["scenario_title"], "淞沪会战")
        self.assertEqual(snapshots[0]["k_state"]["K1"], DEFAULT_K_STATE["K1"])
        self.assertEqual(snapshots[0]["k_state"]["K2"], 0.8)
        self.assertEqual(snapshots[0]["s_state"]["editor_trust"], DEFAULT_S_STATE["editor_trust"])
        self.assertEqual(snapshots[0]["s_state"]["public_panic"], DEFAULT_S_STATE["public_panic"])
        self.assertEqual(snapshots[0]["s_state"]["source_safety"], 0.0)
        self.assertEqual(snapshots[0]["risk_flags"], ["source_exposure_risk"])


if __name__ == "__main__":
    unittest.main()
