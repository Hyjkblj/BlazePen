"""训练输出装配策略单元测试。"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from training.output_assembler_policy import TrainingOutputAssemblerPolicy
from training.runtime_events import RuntimeConsequenceEvent
from training.runtime_state import GameRuntimeFlags, GameRuntimeState


class TrainingOutputAssemblerPolicyTestCase(unittest.TestCase):
    """覆盖输出装配策略的主要 DTO 转换路径。"""

    def setUp(self):
        self.policy = TrainingOutputAssemblerPolicy()

    def test_build_scenario_output_list_should_filter_invalid_payloads(self):
        """候选场景列表应自动过滤空值和无效场景。"""
        outputs = self.policy.build_scenario_output_list(
            [
                None,
                {},
                {"id": "   "},
                {
                    "id": "S1",
                    "title": "卢沟桥",
                    "options": [
                        {"id": "A", "label": "先核验"},
                        {"label": "缺少 id 的无效选项"},
                    ],
                },
                {
                    "id": "S2",
                    "title": "武汉会战",
                    "recommendation": {
                        "mode": "guided",
                        "rank": 1,
                        "rank_score": 0.95,
                        "reasons": ["补强 K1"],
                    },
                },
            ]
        )

        self.assertIsNotNone(outputs)
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0].id, "S1")
        self.assertEqual(len(outputs[0].options), 1)
        self.assertEqual(outputs[1].recommendation.rank, 1)

    def test_build_runtime_state_output_should_support_runtime_object(self):
        """运行时对象应能被统一转成稳定 DTO。"""
        runtime_state = GameRuntimeState.from_session(
            SimpleNamespace(
                session_id="s-1",
                current_round_no=1,
                current_scenario_id="S1",
                k_state={"K1": 0.6},
                s_state={"editor_trust": 0.7, "public_panic": 0.2, "source_safety": 0.8},
                session_meta={},
            ),
            round_no=2,
            current_scene_id="S2",
            player_profile={"name": "李明", "identity": "战地记者"},
            runtime_flags=GameRuntimeFlags(source_exposed=True),
        )

        output = self.policy.build_runtime_state_output(runtime_state)

        self.assertIsNotNone(output)
        self.assertEqual(output.current_round_no, 2)
        self.assertEqual(output.current_scene_id, "S2")
        self.assertTrue(output.runtime_flags.source_exposed)
        self.assertEqual(output.player_profile.name, "李明")
        self.assertEqual(output.state_bar.public_stability, 0.8)

    def test_build_consequence_event_outputs_should_support_object_and_dict_mix(self):
        """后果事件批量转换应兼容对象和字典混合输入。"""
        outputs = self.policy.build_consequence_event_outputs(
            [
                RuntimeConsequenceEvent(
                    event_type="source_exposed",
                    label="来源暴露",
                    summary="线人存在暴露风险。",
                    related_flag="source_exposed",
                ),
                {
                    "event_type": "public_panic_triggered",
                    "label": "群众恐慌",
                    "summary": "群众稳定度下降。",
                    "severity": "high",
                },
                None,
            ]
        )

        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0].event_type, "source_exposed")
        self.assertEqual(outputs[0].related_flag, "source_exposed")
        self.assertEqual(outputs[1].severity, "high")

    def test_build_kt_observation_output_should_read_row_attributes(self):
        """KT 观测 DTO 应从行对象属性中稳定提取。"""
        row = SimpleNamespace(
            round_no=3,
            scenario_id="S3",
            scenario_title="南京保卫战",
            training_mode="guided",
            primary_skill_code="K4",
            primary_risk_flag="source_exposure_risk",
            is_high_risk=True,
            target_skills=["K4"],
            weak_skills_before=["K4", "K5"],
            risk_flags=["source_exposure_risk"],
            focus_tags=["求证", "来源保护"],
            evidence=["线索单一"],
            skill_observations=[
                {"code": "K4", "before": 0.3, "delta": 0.2, "after": 0.5, "is_target": True}
            ],
            state_observations=[
                {"code": "editor_trust", "before": 0.5, "delta": -0.1, "after": 0.4}
            ],
            observation_summary="本回合应优先补强来源保护。",
        )

        output = self.policy.build_kt_observation_output(row)

        self.assertIsNotNone(output)
        self.assertEqual(output.round_no, 3)
        self.assertEqual(output.scenario_title, "南京保卫战")
        self.assertEqual(output.skill_observations[0].code, "K4")
        self.assertTrue(output.is_high_risk)

    def test_build_recommendation_log_output_should_convert_nested_fields(self):
        """推荐日志 DTO 应保留候选池、推荐信息和决策上下文。"""
        row = SimpleNamespace(
            round_no=2,
            training_mode="self-paced",
            selection_source="weak_skill_priority",
            recommended_scenario_id="S2",
            selected_scenario_id="S2",
            candidate_pool=[
                {
                    "scenario_id": "S2",
                    "title": "淞沪会战",
                    "rank": 1,
                    "rank_score": 0.91,
                    "is_selected": True,
                    "is_recommended": True,
                }
            ],
            recommended_recommendation={"mode": "self-paced", "rank": 1, "rank_score": 0.91},
            selected_recommendation={"mode": "self-paced", "rank": 1, "rank_score": 0.91},
            decision_context={
                "mode": "self-paced",
                "selection_source": "weak_skill_priority",
                "selected_scenario_id": "S2",
                "candidate_pool": [],
            },
        )

        output = self.policy.build_recommendation_log_output(row)

        self.assertIsNotNone(output)
        self.assertEqual(output.round_no, 2)
        self.assertEqual(output.training_mode, "self-paced")
        self.assertEqual(output.candidate_pool[0].scenario_id, "S2")
        self.assertEqual(output.decision_context.selection_source, "weak_skill_priority")

    def test_build_audit_event_outputs_should_filter_empty_rows_and_format_timestamp(self):
        """审计事件批量转换应过滤空值，并统一输出 ISO 时间。"""
        outputs = self.policy.build_audit_event_outputs(
            [
                SimpleNamespace(
                    event_type="round_submitted",
                    round_no=2,
                    payload={"scenario_id": "S2"},
                    created_at=datetime(2026, 3, 19, 12, 30, 0),
                ),
                None,
            ]
        )

        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0].event_type, "round_submitted")
        self.assertEqual(outputs[0].timestamp, "2026-03-19T12:30:00")


if __name__ == "__main__":
    unittest.main()
