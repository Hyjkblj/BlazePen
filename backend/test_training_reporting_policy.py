"""训练报告与诊断聚合策略测试。"""

from __future__ import annotations

import unittest

from training.reporting_policy import TrainingReportingPolicy
from training.training_outputs import (
    TrainingAuditEventOutput,
    TrainingKtObservationOutput,
    TrainingRecommendationLogOutput,
)


class TrainingReportingPolicyTestCase(unittest.TestCase):
    """验证训练报告与诊断聚合逻辑稳定可回归。"""

    def setUp(self):
        self.policy = TrainingReportingPolicy()

    def test_diagnostics_summary_should_aggregate_counts_and_last_markers(self):
        """诊断摘要应稳定聚合推荐偏差、事件统计和风险计数。"""
        summary = self.policy.build_diagnostics_summary(
            recommendation_logs=[
                TrainingRecommendationLogOutput.from_payload(
                    {
                        "round_no": 1,
                        "training_mode": "self-paced",
                        "selection_source": "candidate_pool",
                        "recommended_scenario_id": "S2",
                        "selected_scenario_id": "S1",
                    }
                )
            ],
            audit_events=[
                TrainingAuditEventOutput.from_payload(
                    {
                        "event_type": "round_submitted",
                        "round_no": 1,
                        "payload": {},
                        "timestamp": "2026-03-17T00:00:00",
                    }
                )
            ],
            kt_observations=[
                TrainingKtObservationOutput.from_payload(
                    {
                        "round_no": 1,
                        "scenario_id": "S1",
                        "scenario_title": "固定题",
                        "training_mode": "guided",
                        "primary_skill_code": "K5",
                        "primary_risk_flag": "source_exposure_risk",
                        "is_high_risk": True,
                        "weak_skills_before": ["K5"],
                        "risk_flags": ["source_exposure_risk"],
                    }
                )
            ],
        )

        payload = summary.to_dict()
        self.assertEqual(payload["high_risk_round_nos"], [1])
        self.assertEqual(payload["recommended_vs_selected_mismatch_rounds"], [1])
        self.assertEqual(payload["risk_flag_counts"][0]["code"], "source_exposure_risk")
        self.assertEqual(payload["last_primary_skill_code"], "K5")
        self.assertEqual(payload["last_event_type"], "round_submitted")

    def test_diagnostics_summary_should_include_phase_counts_and_transitions(self):
        """诊断摘要应输出阶段分布、最近阶段和阶段切换轮次。"""
        summary = self.policy.build_diagnostics_summary(
            recommendation_logs=[],
            audit_events=[
                TrainingAuditEventOutput.from_payload(
                    {
                        "event_type": "session_initialized",
                        "round_no": 0,
                        "payload": {
                            "phase": {
                                "round_no": 1,
                                "phase_tags": ["opening"],
                            }
                        },
                    }
                ),
                TrainingAuditEventOutput.from_payload(
                    {
                        "event_type": "round_submitted",
                        "round_no": 1,
                        "payload": {
                            "phase": {
                                "round_no": 1,
                                "phase_tags": ["opening"],
                            }
                        },
                    }
                ),
                TrainingAuditEventOutput.from_payload(
                    {
                        "event_type": "round_submitted",
                        "round_no": 3,
                        "payload": {
                            "phase": {
                                "round_no": 3,
                                "phase_tags": ["middle"],
                            }
                        },
                    }
                ),
                TrainingAuditEventOutput.from_payload(
                    {
                        "event_type": "phase_transition",
                        "round_no": 3,
                        "payload": {
                            "from_phase": {"round_no": 2, "phase_tags": ["opening"]},
                            "to_phase": {"round_no": 3, "phase_tags": ["middle"]},
                        },
                    }
                ),
            ],
            kt_observations=[],
        )

        payload = summary.to_dict()
        phase_tag_counts = {item["code"]: item["count"] for item in payload["phase_tag_counts"]}
        self.assertEqual(phase_tag_counts["opening"], 1)
        self.assertEqual(phase_tag_counts["middle"], 1)
        self.assertEqual(payload["phase_transition_count"], 1)
        self.assertEqual(payload["phase_transition_rounds"], [3])
        self.assertEqual(payload["last_phase_tags"], ["middle"])
        self.assertEqual(payload["last_event_type"], "phase_transition")

    def test_report_artifacts_should_include_round_zero_and_review_suggestions(self):
        """报告聚合结果应包含 round=0 起点和可直接展示的复盘建议。"""
        artifacts = self.policy.build_report_artifacts(
            initial_k_state={"K1": 0.45, "K2": 0.45, "K3": 0.45, "K4": 0.45, "K5": 0.2, "K6": 0.45, "K7": 0.45, "K8": 0.45},
            initial_s_state={"credibility": 0.6, "accuracy": 0.6, "public_panic": 0.3, "source_safety": 0.65, "editor_trust": 0.55, "actionability": 0.5},
            final_k_state={"K1": 0.6, "K2": 0.5, "K3": 0.48, "K4": 0.47, "K5": 0.3, "K6": 0.5, "K7": 0.46, "K8": 0.45},
            final_s_state={"credibility": 0.7, "accuracy": 0.66, "public_panic": 0.3, "source_safety": 0.52, "editor_trust": 0.58, "actionability": 0.55},
            round_snapshots=[
                {
                    "round_no": 1,
                    "scenario_id": "S1",
                    "scenario_title": "固定题",
                    "k_state": {"K1": 0.6, "K2": 0.5, "K3": 0.48, "K4": 0.47, "K5": 0.3, "K6": 0.5, "K7": 0.46, "K8": 0.45},
                    "s_state": {"credibility": 0.7, "accuracy": 0.66, "public_panic": 0.3, "source_safety": 0.52, "editor_trust": 0.58, "actionability": 0.55},
                    "weighted_k_score": 0.53,
                    "is_high_risk": True,
                    "risk_flags": ["source_exposure_risk"],
                    "primary_skill_code": "K5",
                    "timestamp": "2026-03-17T00:00:00",
                }
            ],
        )

        self.assertEqual(artifacts.growth_curve[0].round_no, 0)
        self.assertEqual(artifacts.growth_curve[1].scenario_id, "S1")
        self.assertEqual(artifacts.summary.high_risk_round_nos, [1])
        self.assertEqual(artifacts.summary.completed_scenario_ids, ["S1"])
        self.assertEqual(artifacts.summary.weakest_skill_code, "K5")
        self.assertTrue(len(artifacts.summary.review_suggestions) >= 1)


if __name__ == "__main__":
    unittest.main()
