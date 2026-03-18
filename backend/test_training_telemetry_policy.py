"""训练观测策略测试。"""

from __future__ import annotations

import unittest

from training.phase_policy import TrainingPhaseSnapshot
from training.telemetry_policy import TrainingTelemetryPolicy


class TrainingTelemetryPolicyTestCase(unittest.TestCase):
    """验证训练观测策略能稳定产出结构化工件。"""

    def setUp(self):
        self.policy = TrainingTelemetryPolicy()

    def test_should_build_session_initialized_audit_event(self):
        """初始化事件应产出稳定审计载荷，并带上初始阶段信息。"""
        event = self.policy.build_session_initialized_audit_event(
            training_mode="adaptive",
            scenario_bank_version="v1",
            scenario_count=4,
            phase_snapshot=TrainingPhaseSnapshot(
                round_no=1,
                phase_tags=["opening"],
                window_reasons=["开场阶段"],
                matched_window_count=1,
            ),
        )

        payload = event.to_dict()
        self.assertEqual(payload["event_type"], "session_initialized")
        self.assertEqual(payload["payload"]["training_mode"], "adaptive")
        self.assertEqual(payload["payload"]["scenario_count"], 4)
        self.assertEqual(payload["payload"]["phase"]["phase_tags"], ["opening"])

    def test_should_build_recommendation_log(self):
        """推荐日志应保留候选池和最终选择信息。"""
        decision_context = type(
            "DecisionContext",
            (),
            {
                "selection_source": "candidate_pool",
                "recommended_scenario_id": "S3",
                "selected_scenario_id": "S1",
                "candidate_pool": [
                    type(
                        "Candidate",
                        (),
                        {
                            "to_dict": staticmethod(
                                lambda: {
                                    "scenario_id": "S3",
                                    "title": "来源保护",
                                    "rank": 1,
                                    "rank_score": 1.2,
                                    "is_selected": False,
                                    "is_recommended": True,
                                }
                            )
                        },
                    )()
                ],
                "recommended_recommendation": None,
                "selected_recommendation": None,
                "to_dict": staticmethod(
                    lambda: {
                        "mode": "self-paced",
                        "selection_source": "candidate_pool",
                        "selected_scenario_id": "S1",
                        "recommended_scenario_id": "S3",
                        "candidate_pool": [],
                    }
                ),
            },
        )()

        payload = self.policy.build_recommendation_log("self-paced", decision_context).to_dict()
        self.assertEqual(payload["training_mode"], "self-paced")
        self.assertEqual(payload["recommended_scenario_id"], "S3")
        self.assertEqual(payload["selected_scenario_id"], "S1")

    def test_should_build_kt_observation(self):
        """KT 观察应能提炼主能力和风险标签。"""
        observation = self.policy.build_kt_observation(
            training_mode="self-paced",
            round_no=2,
            scenario_payload={
                "id": "S3",
                "title": "来源保护",
                "target_skills": ["K5"],
                "risk_tags": ["source"],
            },
            k_before={"K1": 0.8, "K5": 0.2},
            k_after={"K1": 0.8, "K5": 0.35},
            s_before={"credibility": 0.6},
            s_after={"credibility": 0.7},
            evaluation_payload={
                "risk_flags": ["source_exposure_risk"],
                "skill_delta": {"K5": 0.15},
                "s_delta": {"credibility": 0.1},
                "evidence": ["需要加强来源保护"],
            },
        )

        payload = observation.to_dict()
        self.assertEqual(payload["scenario_id"], "S3")
        self.assertEqual(payload["primary_skill_code"], "K5")
        self.assertEqual(payload["primary_risk_flag"], "source_exposure_risk")
        self.assertTrue(payload["is_high_risk"])
        self.assertIn("K5", payload["focus_tags"])

    def test_should_append_phase_transition_audit_event_when_phase_changes(self):
        """阶段切换时，应额外生成 phase_transition 审计事件。"""
        events = self.policy.build_round_audit_events(
            training_mode="guided",
            round_no=3,
            scenario_id="S3",
            selected_option="B",
            evaluation_payload={
                "confidence": 0.8,
                "risk_flags": [],
                "skill_delta": {},
                "s_delta": {},
                "evidence": ["ok"],
            },
            decision_context=None,
            phase_snapshot=TrainingPhaseSnapshot(
                round_no=3,
                phase_tags=["middle"],
                window_reasons=["进入中段"],
                matched_window_count=1,
            ),
            previous_phase_snapshot=TrainingPhaseSnapshot(
                round_no=2,
                phase_tags=["opening"],
                window_reasons=["开场阶段"],
                matched_window_count=1,
            ),
            is_completed=False,
            ending_payload=None,
        )

        self.assertEqual(events[0].event_type, "round_submitted")
        self.assertEqual(events[0].payload["phase"]["phase_tags"], ["middle"])
        self.assertEqual(events[1].event_type, "phase_transition")
        self.assertEqual(events[1].payload["from_phase"]["phase_tags"], ["opening"])
        self.assertEqual(events[1].payload["to_phase"]["phase_tags"], ["middle"])


if __name__ == "__main__":
    unittest.main()
