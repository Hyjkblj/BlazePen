"""训练推荐策略测试。"""

from __future__ import annotations

import unittest

from training.recommendation_policy import RecommendationPolicy
from training.scenario_repository import ScenarioRepository


class RecommendationPolicyTestCase(unittest.TestCase):
    """验证短板推荐逻辑已经独立成可测试策略层。"""

    def setUp(self):
        self.policy = RecommendationPolicy()
        self.repository = ScenarioRepository()
        self.scenarios = self.repository.freeze_sequence(
            [
                {"id": "S1", "title": "卢沟桥事变快讯发布"},
                {"id": "S3", "title": "南京失守高冲突信息处置"},
                {"id": "S4", "title": "武汉会战后方动员沟通"},
            ]
        )

    def test_should_recommend_k5_related_scenario_when_source_protection_is_weak(self):
        """当 K5 很弱时，应优先推荐来源保护相关场景。"""
        result = self.policy.recommend_next(
            training_mode="adaptive",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.1,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "S3")

    def test_should_ignore_completed_scenarios(self):
        """已完成场景不应再次被推荐。"""
        result = self.policy.recommend_next(
            training_mode="adaptive",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=["S3"],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.1,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
        )

        self.assertIsNotNone(result)
        self.assertNotEqual(result["id"], "S3")

    def test_supports_mode_should_include_self_paced_aliases(self):
        """推荐策略应同时识别 self-paced 和 self_paced 两种写法。"""
        self.assertTrue(self.policy.supports_mode("adaptive"))
        self.assertTrue(self.policy.supports_mode("self-paced"))
        self.assertTrue(self.policy.supports_mode("self_paced"))
        self.assertFalse(self.policy.supports_mode("guided"))

    def test_is_strict_mode_should_only_require_adaptive(self):
        """只有严格推荐模式才必须命中第一推荐题。"""
        self.assertTrue(self.policy.is_strict_mode("adaptive"))
        self.assertFalse(self.policy.is_strict_mode("self-paced"))
        self.assertFalse(self.policy.is_strict_mode("guided"))

    def test_rank_candidates_should_return_sorted_candidates_with_rank(self):
        """候选排序结果应保留推荐排名，便于 self-paced 展示候选列表。"""
        result = self.policy.rank_candidates(
            training_mode="self_paced",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.1,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
        )

        self.assertEqual([item["id"] for item in result], ["S3", "S1", "S4"])
        self.assertEqual(result[0]["recommendation"]["mode"], "self-paced")
        self.assertEqual(result[0]["recommendation"]["rank"], 1)
        self.assertEqual(result[1]["recommendation"]["rank"], 2)
        self.assertEqual(result[2]["recommendation"]["rank"], 3)

    def test_recent_risk_should_boost_matching_remediation_scenario(self):
        """最近出现的风险应把对应补救题推到更靠前的位置。"""
        result = self.policy.rank_candidates(
            training_mode="adaptive",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.9,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            recent_risk_rounds=[["source_exposure_risk"]],
            current_round_no=0,
            total_rounds=3,
        )

        self.assertEqual(result[0]["id"], "S3")
        self.assertGreater(result[0]["recommendation"]["risk_boost_score"], 0.0)

    def test_consecutive_risk_should_amplify_risk_boost_score(self):
        """同类风险连续出现时，补救题的风险加权应进一步放大。"""
        single_risk_result = self.policy.rank_candidates(
            training_mode="adaptive",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.9,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            recent_risk_rounds=[["source_exposure_risk"]],
            current_round_no=0,
            total_rounds=3,
        )
        consecutive_risk_result = self.policy.rank_candidates(
            training_mode="adaptive",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.9,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            recent_risk_rounds=[["source_exposure_risk"], ["source_exposure_risk"]],
            current_round_no=0,
            total_rounds=3,
        )

        self.assertGreater(
            consecutive_risk_result[0]["recommendation"]["risk_boost_score"],
            single_risk_result[0]["recommendation"]["risk_boost_score"],
        )

    def test_phase_alignment_should_prefer_current_round_neighboring_scenarios(self):
        """能力分接近时，应优先推荐与当前回合阶段更贴近的题目。"""
        result = self.policy.rank_candidates(
            training_mode="adaptive",
            scenario_payload_sequence=self.scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.9,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            current_round_no=2,
            total_rounds=3,
        )

        self.assertEqual(result[0]["id"], "S4")
        self.assertGreater(result[0]["recommendation"]["phase_boost_score"], 0.0)

    def test_stage_window_alignment_should_override_sequence_distance_when_phase_tags_exist(self):
        """命中阶段窗口后，应优先按场景阶段标签推荐，而不是只看原始顺序距离。"""
        scenarios = self.repository.freeze_sequence(
            [
                {"id": "S3", "title": "南京失守高冲突信息处置"},
                {"id": "S1", "title": "卢沟桥事变快讯发布"},
                {"id": "S4", "title": "武汉会战后方动员沟通"},
            ]
        )

        result = self.policy.rank_candidates(
            training_mode="adaptive",
            scenario_payload_sequence=scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.9,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            current_round_no=0,
            total_rounds=3,
        )

        self.assertEqual(result[0]["id"], "S1")
        self.assertGreater(result[0]["recommendation"]["phase_boost_score"], 0.0)

    def test_phase_boost_should_fallback_to_distance_when_scenario_phase_tags_missing(self):
        """如果场景没有阶段标签，阶段推荐应回退到旧的顺序距离兜底逻辑。"""
        scenarios = [
            {"id": "X1", "title": "场景一", "target_skills": ["K1"]},
            {"id": "X2", "title": "场景二", "target_skills": ["K1"]},
            {"id": "X3", "title": "场景三", "target_skills": ["K1"]},
        ]

        result = self.policy.rank_candidates(
            training_mode="adaptive",
            scenario_payload_sequence=scenarios,
            completed_scenario_ids=[],
            k_state={
                "K1": 0.9,
                "K2": 0.9,
                "K3": 0.9,
                "K4": 0.9,
                "K5": 0.9,
                "K6": 0.9,
                "K7": 0.9,
                "K8": 0.9,
            },
            s_state={
                "credibility": 0.6,
                "accuracy": 0.6,
                "public_panic": 0.3,
                "source_safety": 0.65,
                "editor_trust": 0.55,
                "actionability": 0.5,
            },
            current_round_no=2,
            total_rounds=3,
        )

        self.assertEqual(result[0]["id"], "X3")
        self.assertGreater(result[0]["recommendation"]["phase_boost_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
