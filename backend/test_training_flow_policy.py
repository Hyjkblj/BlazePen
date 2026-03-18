"""训练回合流转策略测试。"""

from __future__ import annotations

import unittest

from training.config_loader import FlowForcedRoundConfig, load_training_runtime_config, model_copy
from training.round_flow_policy import TrainingRoundFlowPolicy
from training.scenario_repository import ScenarioRepository


class TrainingRoundFlowPolicyTestCase(unittest.TestCase):
    """验证下一题解析、提交校验与完成态判断已从服务层拆出。"""

    def setUp(self):
        self.policy = TrainingRoundFlowPolicy()
        self.repository = ScenarioRepository()
        self.session_sequence = [
            {"id": "S1", "title": "卢沟桥事变快讯发布"},
            {"id": "S3", "title": "南京失守高冲突信息处置"},
            {"id": "S4", "title": "武汉会战后方动员沟通"},
        ]
        self.payload_sequence = self.repository.freeze_sequence(self.session_sequence)
        self.payload_catalog = self.repository.freeze_related_catalog(self.session_sequence)
        self.weak_k_state = {
            "K1": 0.9,
            "K2": 0.9,
            "K3": 0.9,
            "K4": 0.9,
            "K5": 0.1,
            "K6": 0.9,
            "K7": 0.9,
            "K8": 0.9,
        }
        self.default_s_state = {
            "credibility": 0.6,
            "accuracy": 0.6,
            "public_panic": 0.3,
            "source_safety": 0.65,
            "editor_trust": 0.55,
            "actionability": 0.5,
        }

    def _build_runtime_config_with_forced_rounds(self, forced_rounds):
        """构建带关键节点规则的运行时配置副本，避免污染全局默认配置。"""
        runtime_config = model_copy(load_training_runtime_config())
        runtime_config.flow.forced_rounds = list(forced_rounds)
        return runtime_config

    def test_self_paced_should_return_primary_scenario_and_candidates(self):
        """自选模式应同时返回推荐题与候选列表。"""
        bundle = self.policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=0,
            session_sequence=self.session_sequence,
            scenario_payload_sequence=self.payload_sequence,
            completed_scenario_ids=[],
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
        )

        payload = bundle.to_dict()
        self.assertEqual(payload["scenario"]["id"], "S3")
        self.assertEqual([item["id"] for item in payload["scenario_candidates"]], ["S3", "S1", "S4"])

    def test_adaptive_should_require_submitting_first_recommended_scenario(self):
        """严格推荐模式下，只允许提交第一推荐题。"""
        with self.assertRaises(ValueError) as cm:
            self.policy.validate_submission(
                training_mode="adaptive",
                current_round_no=0,
                submitted_scenario_id="S1",
                session_sequence=self.session_sequence,
                scenario_payload_sequence=self.payload_sequence,
                completed_scenario_ids=[],
                k_state=self.weak_k_state,
                s_state=self.default_s_state,
            )

        self.assertIn("expected=S3", str(cm.exception))

    def test_recent_risk_should_flow_into_next_scenario_resolution(self):
        """最近风险历史应透传到流转策略，而不是只在推荐策略单测里生效。"""
        custom_sequence = [
            {"id": "S1", "title": "Start"},
            {"id": "S4", "title": "Middle"},
            {"id": "S3", "title": "Remediation"},
        ]
        payload_sequence = self.repository.freeze_sequence(custom_sequence)
        bundle = self.policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=1,
            session_sequence=custom_sequence,
            scenario_payload_sequence=payload_sequence,
            completed_scenario_ids=["S1"],
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
            s_state=self.default_s_state,
            recent_risk_rounds=[["source_exposure_risk"]],
        )

        self.assertEqual(bundle.scenario["id"], "S3")
        self.assertGreater(bundle.scenario["recommendation"]["risk_boost_score"], 0.0)

    def test_forced_round_should_override_recommendation_result(self):
        """命中关键节点轮次时，应优先返回配置指定的场景，而不是继续走推荐排序。"""
        runtime_config = self._build_runtime_config_with_forced_rounds(
            [
                FlowForcedRoundConfig(
                    round_no=1,
                    scenario_id="S1",
                    modes=["self-paced"],
                    reason="固定开场节点",
                )
            ]
        )
        policy = TrainingRoundFlowPolicy(runtime_config=runtime_config)

        bundle = policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=0,
            session_sequence=self.session_sequence,
            scenario_payload_sequence=self.payload_sequence,
            completed_scenario_ids=[],
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
        )

        self.assertEqual(bundle.scenario["id"], "S1")
        self.assertIsNone(bundle.scenario_candidates)

    def test_future_forced_round_should_be_reserved_from_recommendation_candidates(self):
        """未来关键节点在未到触发轮次前，不应被推荐模式提前消费。"""
        runtime_config = self._build_runtime_config_with_forced_rounds(
            [
                FlowForcedRoundConfig(
                    round_no=3,
                    scenario_id="S4",
                    modes=["self-paced"],
                    reason="保留中段关键节点",
                )
            ]
        )
        policy = TrainingRoundFlowPolicy(runtime_config=runtime_config)

        bundle = policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=0,
            session_sequence=self.session_sequence,
            scenario_payload_sequence=self.payload_sequence,
            completed_scenario_ids=[],
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
        )

        self.assertEqual(bundle.scenario["id"], "S3")
        self.assertEqual([item["id"] for item in bundle.scenario_candidates], ["S3", "S1"])

    def test_forced_round_should_require_submitting_configured_scenario(self):
        """命中关键节点轮次时，即使是自选模式，也应校验只能提交配置指定场景。"""
        runtime_config = self._build_runtime_config_with_forced_rounds(
            [
                FlowForcedRoundConfig(
                    round_no=1,
                    scenario_id="S1",
                    modes=["self-paced"],
                    reason="固定开场节点",
                )
            ]
        )
        policy = TrainingRoundFlowPolicy(runtime_config=runtime_config)

        with self.assertRaises(ValueError) as cm:
            policy.validate_submission(
                training_mode="self-paced",
                current_round_no=0,
                submitted_scenario_id="S3",
                session_sequence=self.session_sequence,
                scenario_payload_sequence=self.payload_sequence,
                completed_scenario_ids=[],
                k_state=self.weak_k_state,
                s_state=self.default_s_state,
            )

        self.assertIn("expected=S1", str(cm.exception))

    def test_recommendation_mode_should_fallback_to_ordered_validation_when_candidates_empty(self):
        """推荐候选为空时，应回退到固定顺序校验而不是放行任意场景。"""
        with self.assertRaises(ValueError) as cm:
            self.policy.validate_submission(
                training_mode="adaptive",
                current_round_no=0,
                submitted_scenario_id="S9",
                session_sequence=[{"id": "S1", "title": "Only"}],
                scenario_payload_sequence=[],
                completed_scenario_ids=[],
                k_state=self.weak_k_state,
                s_state=self.default_s_state,
            )

        self.assertIn("expected=S1", str(cm.exception))

    def test_recommendation_fallback_should_skip_completed_scenarios(self):
        """推荐兜底时，不应把已完成场景再次返回给前端。"""
        bundle = self.policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=0,
            session_sequence=[{"id": "S1", "title": "Only"}],
            scenario_payload_sequence=self.repository.freeze_sequence([{"id": "S1", "title": "Only"}]),
            completed_scenario_ids=["S1"],
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
        )

        self.assertIsNone(bundle.scenario)

    def test_recommendation_fallback_should_return_first_unresolved_scenario_when_only_reserved_left(self):
        """如果非保留场景都已完成，兜底路径应返回未完成场景，而不是重复返回历史题目。"""
        runtime_config = self._build_runtime_config_with_forced_rounds(
            [
                FlowForcedRoundConfig(
                    round_no=3,
                    scenario_id="S4",
                    modes=["self-paced"],
                    reason="保留结尾节点",
                )
            ]
        )
        policy = TrainingRoundFlowPolicy(runtime_config=runtime_config)

        bundle = policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=1,
            session_sequence=self.session_sequence,
            scenario_payload_sequence=self.payload_sequence,
            completed_scenario_ids=["S1", "S3"],
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
        )

        self.assertEqual(bundle.scenario["id"], "S4")

    def test_recommendation_fallback_validation_should_match_first_unresolved_scenario(self):
        """推荐兜底校验应与下一题解析保持一致，按首个未完成场景校验。"""
        runtime_config = self._build_runtime_config_with_forced_rounds(
            [
                FlowForcedRoundConfig(
                    round_no=3,
                    scenario_id="S4",
                    modes=["self-paced"],
                    reason="保留结尾节点",
                )
            ]
        )
        policy = TrainingRoundFlowPolicy(runtime_config=runtime_config)

        with self.assertRaises(ValueError) as cm:
            policy.validate_submission(
                training_mode="self-paced",
                current_round_no=1,
                submitted_scenario_id="S3",
                session_sequence=self.session_sequence,
                scenario_payload_sequence=self.payload_sequence,
                completed_scenario_ids=["S1", "S3"],
                k_state=self.weak_k_state,
                s_state=self.default_s_state,
            )

        self.assertIn("expected=S4", str(cm.exception))

    def test_branch_should_override_recommendation_result(self):
        """运行时分支命中后，应优先返回分支场景而不是推荐结果。"""
        bundle = self.policy.build_next_scenario_bundle(
            training_mode="self-paced",
            current_round_no=1,
            session_sequence=self.session_sequence,
            scenario_payload_sequence=self.payload_sequence,
            completed_scenario_ids=["S1"],
            scenario_payload_catalog=self.payload_catalog,
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
            runtime_flags={"panic_triggered": True},
            current_scenario_id="S1",
        )

        self.assertEqual(bundle.scenario["id"], "S2B")
        self.assertIsNone(bundle.scenario_candidates)
        self.assertEqual(bundle.scenario["branch_transition"]["source_scenario_id"], "S1")

    def test_branch_validation_should_reject_mainline_submission_when_branch_locked(self):
        """命中分支后，提交流转校验应拒绝主线原场景。"""
        with self.assertRaises(ValueError) as cm:
            self.policy.validate_submission(
                training_mode="guided",
                current_round_no=1,
                submitted_scenario_id="S3",
                session_sequence=self.session_sequence,
                scenario_payload_sequence=self.payload_sequence,
                completed_scenario_ids=["S1"],
                scenario_payload_catalog=self.payload_catalog,
                k_state=self.weak_k_state,
                s_state=self.default_s_state,
                runtime_flags={"panic_triggered": True},
                current_scenario_id="S1",
            )

        self.assertIn("expected=S2B", str(cm.exception))

    def test_branch_recovery_should_resolve_before_default_return(self):
        """补救条件满足时，应先进入恢复节点而不是默认回主线。"""
        bundle = self.policy.build_next_scenario_bundle(
            training_mode="guided",
            current_round_no=2,
            session_sequence=self.session_sequence,
            scenario_payload_sequence=self.payload_sequence,
            completed_scenario_ids=["S1", "S2B"],
            scenario_payload_catalog=self.payload_catalog,
            k_state=self.weak_k_state,
            s_state=self.default_s_state,
            runtime_flags={"panic_triggered": False},
            current_scenario_id="S2B",
        )

        self.assertEqual(bundle.scenario["id"], "S3R")
        self.assertEqual(bundle.scenario["branch_transition"]["source_scenario_id"], "S2B")

    def test_is_terminal_state_should_consider_ending_status_and_round_count(self):
        """完成态判断应统一兼容结局已落库、会话已完成和轮次数达标三种情况。"""
        self.assertTrue(
            self.policy.is_terminal_state(
                round_no=3,
                session_sequence=self.session_sequence,
            )
        )
        self.assertTrue(
            self.policy.is_terminal_state(
                round_no=1,
                session_sequence=self.session_sequence,
                session_status="completed",
            )
        )
        self.assertTrue(
            self.policy.is_terminal_state(
                round_no=1,
                session_sequence=self.session_sequence,
                has_ending=True,
            )
        )
        self.assertFalse(
            self.policy.is_terminal_state(
                round_no=1,
                session_sequence=self.session_sequence,
            )
        )


if __name__ == "__main__":
    unittest.main()
