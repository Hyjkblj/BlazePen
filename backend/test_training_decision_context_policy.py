"""训练回合决策上下文策略单元测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from training.decision_context_policy import TrainingDecisionContextPolicy


class TrainingDecisionContextPolicyTestCase(unittest.TestCase):
    """覆盖决策上下文策略的主要来源判定分支。"""

    def setUp(self):
        self.policy = TrainingDecisionContextPolicy()

    def test_guided_mode_should_mark_ordered_sequence_without_recommendation(self):
        """guided 模式下没有推荐元信息时，应按固定主线顺序记录来源。"""
        bundle = SimpleNamespace(
            scenario={"id": "S1", "title": "卢沟桥"},
            scenario_candidates=[{"id": "S1", "title": "卢沟桥"}],
        )

        result = self.policy.build_round_decision_context(
            training_mode="guided",
            submitted_scenario_id="S1",
            next_scenario_bundle=bundle,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.selection_source, "ordered_sequence")
        self.assertIsNone(result.recommended_scenario_id)
        self.assertEqual(result.candidate_pool[0].scenario_id, "S1")

    def test_recommendation_mode_should_mark_fallback_sequence_when_recommendation_missing(self):
        """支持推荐的模式如果缺少推荐元信息，应显式标记为回退顺序。"""
        bundle = SimpleNamespace(
            scenario={"id": "S2", "title": "淞沪会战"},
            scenario_candidates=[
                {"id": "S2", "title": "淞沪会战"},
                {"id": "S3", "title": "南京报道"},
            ],
        )

        result = self.policy.build_round_decision_context(
            training_mode="self-paced",
            submitted_scenario_id="S2",
            next_scenario_bundle=bundle,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.selection_source, "fallback_sequence")
        self.assertIsNone(result.recommended_scenario_id)

    def test_should_mark_top_recommendation_when_selected_matches_recommended(self):
        """提交题目与推荐题一致时，应标记为命中首选推荐。"""
        bundle = SimpleNamespace(
            scenario={
                "id": "S3",
                "title": "南京报道",
                "recommendation": {"mode": "self-paced", "rank": 1, "rank_score": 0.91},
            },
            scenario_candidates=[
                {
                    "id": "S3",
                    "title": "南京报道",
                    "recommendation": {"mode": "self-paced", "rank": 1, "rank_score": 0.91},
                },
                {
                    "id": "S1",
                    "title": "卢沟桥",
                    "recommendation": {"mode": "self-paced", "rank": 2, "rank_score": 0.55},
                },
            ],
        )

        result = self.policy.build_round_decision_context(
            training_mode="self-paced",
            submitted_scenario_id="S3",
            next_scenario_bundle=bundle,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.selection_source, "top_recommendation")
        self.assertEqual(result.recommended_scenario_id, "S3")
        self.assertTrue(result.candidate_pool[0].is_selected)
        self.assertTrue(result.candidate_pool[0].is_recommended)

    def test_should_mark_candidate_pool_when_selected_is_not_top_recommendation(self):
        """命中候选池但没有选择首推题时，应保留候选池来源信息。"""
        bundle = SimpleNamespace(
            scenario={
                "id": "S3",
                "title": "南京报道",
                "recommendation": {"mode": "self-paced", "rank": 1, "rank_score": 0.91},
            },
            scenario_candidates=[
                {
                    "id": "S3",
                    "title": "南京报道",
                    "recommendation": {"mode": "self-paced", "rank": 1, "rank_score": 0.91},
                },
                {
                    "id": "S1",
                    "title": "卢沟桥",
                    "recommendation": {"mode": "self-paced", "rank": 2, "rank_score": 0.55},
                },
            ],
        )

        result = self.policy.build_round_decision_context(
            training_mode="self-paced",
            submitted_scenario_id="S1",
            next_scenario_bundle=bundle,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.selection_source, "candidate_pool")
        self.assertEqual(result.recommended_scenario_id, "S3")
        self.assertEqual(result.selected_recommendation.rank, 2)
        self.assertEqual(result.recommended_recommendation.rank, 1)
        self.assertTrue(result.candidate_pool[1].is_selected)
        self.assertFalse(result.candidate_pool[1].is_recommended)

    def test_branch_transition_should_override_other_selection_sources(self):
        """一旦场景携带分支跳转信息，应优先按分支来源记录。"""
        bundle = SimpleNamespace(
            scenario={
                "id": "S2B",
                "title": "补救分支",
                "branch_transition": {
                    "source_scenario_id": "S1",
                    "target_scenario_id": "S2B",
                    "transition_type": "branch",
                    "triggered_flags": ["panic_triggered"],
                },
            },
            scenario_candidates=[
                {
                    "id": "S2B",
                    "title": "补救分支",
                    "branch_transition": {
                        "source_scenario_id": "S1",
                        "target_scenario_id": "S2B",
                        "transition_type": "branch",
                        "triggered_flags": ["panic_triggered"],
                    },
                }
            ],
        )

        result = self.policy.build_round_decision_context(
            training_mode="guided",
            submitted_scenario_id="S2B",
            next_scenario_bundle=bundle,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.selection_source, "branch_transition")
        self.assertEqual(result.selected_branch_transition.target_scenario_id, "S2B")
        self.assertEqual(result.selected_branch_transition.triggered_flags, ["panic_triggered"])


if __name__ == "__main__":
    unittest.main()
