"""训练回合状态推进策略单元测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from training.consequence_engine import ConsequenceEngine
from training.round_transition_policy import TrainingRoundTransitionPolicy
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.training_outputs import TrainingRoundDecisionContextOutput


class _SourceRiskEvaluator:
    """来源暴露评估器桩。"""

    def evaluate_round(self, **kwargs):
        return {
            "llm_model": "rules_v1",
            "confidence": 0.9,
            "risk_flags": ["source_exposure_risk"],
            "skill_delta": {"K1": 0.1},
            "s_delta": {"source_safety": -0.3},
            "evidence": ["来源保护不足。"],
        }


class _PanicRiskEvaluator:
    """公众恐慌评估器桩。"""

    def evaluate_round(self, **kwargs):
        return {
            "llm_model": "rules_v1",
            "confidence": 0.88,
            "risk_flags": ["high_risk_unverified_publish"],
            "skill_delta": {"K4": -0.05},
            "s_delta": {"public_panic": 0.6},
            "evidence": ["存在未经核实即发布风险。"],
        }


class TrainingRoundTransitionPolicyTestCase(unittest.TestCase):
    """覆盖回合状态推进策略的核心职责。"""

    def setUp(self):
        self.policy = TrainingRoundTransitionPolicy(
            runtime_artifact_policy=TrainingRuntimeArtifactPolicy()
        )
        self.consequence_engine = ConsequenceEngine()
        self.session = SimpleNamespace(
            session_id="s-1",
            current_round_no=0,
            current_scenario_id=None,
            k_state={},
            s_state={},
            session_meta={
                "player_profile": {"name": "林岚", "identity": "记者"},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
            },
        )
        self.decision_context = TrainingRoundDecisionContextOutput.from_payload(
            {
                "mode": "guided",
                "selection_source": "ordered_sequence",
                "selected_scenario_id": "S1",
                "candidate_pool": [],
            }
        )

    def test_build_round_transition_artifacts_should_attach_runtime_results(self):
        """状态推进后应返回可直接落库的评估、运行时状态和 user_action。"""
        result = self.policy.build_round_transition_artifacts(
            session=self.session,
            evaluator=_SourceRiskEvaluator(),
            consequence_engine=self.consequence_engine,
            round_no=1,
            scenario_id="S1",
            user_input="先保护来源再发稿",
            selected_option="A",
            decision_context=self.decision_context,
            k_before={"K1": 0.4},
            s_before={"editor_trust": 0.6, "public_panic": 0.1, "source_safety": 0.5},
            recent_risk_rounds=[],
            scenario_payload={"id": "S1", "title": "卢沟桥"},
        )

        self.assertEqual(result.evaluation_payload["risk_flags"], ["source_exposure_risk"])
        self.assertEqual(result.updated_k_state["K1"], 0.5)
        self.assertEqual(result.updated_s_state["source_safety"], 0.2)
        self.assertTrue(result.runtime_state.runtime_flags.source_exposed)
        self.assertTrue(result.updated_session_meta["runtime_flags"]["source_exposed"])
        self.assertIn("runtime_state", result.user_action)
        self.assertIn("consequence_events", result.user_action)
        self.assertEqual(result.user_action["decision_context"]["selected_scenario_id"], "S1")
        self.assertEqual(result.consequence_result.consequence_events[0].event_type, "source_exposed")

    def test_build_round_transition_artifacts_should_produce_branch_hints_for_high_risk_path(self):
        """连续高风险时应触发高风险路径提示，并把分支线索写回 user_action。"""
        result = self.policy.build_round_transition_artifacts(
            session=self.session,
            evaluator=_PanicRiskEvaluator(),
            consequence_engine=self.consequence_engine,
            round_no=2,
            scenario_id="S2",
            user_input="先发快讯稳定舆情",
            selected_option="B",
            decision_context=self.decision_context,
            k_before={"K4": 0.5},
            s_before={"editor_trust": 0.6, "public_panic": 0.1, "source_safety": 0.8},
            recent_risk_rounds=[["source_exposure_risk"]],
            scenario_payload={"id": "S2", "title": "淞沪会战"},
        )

        self.assertTrue(result.runtime_state.runtime_flags.panic_triggered)
        self.assertTrue(result.runtime_state.runtime_flags.high_risk_path)
        self.assertIn("stability_control", result.consequence_result.branch_hints)
        self.assertIn("high_risk_remediation", result.consequence_result.branch_hints)
        self.assertEqual(
            result.user_action["branch_hints"],
            ["stability_control", "high_risk_remediation"],
        )


if __name__ == "__main__":
    unittest.main()
