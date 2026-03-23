"""训练输出 DTO 测试。"""

from __future__ import annotations

import unittest

from training.training_outputs import (
    TrainingDiagnosticsOutput,
    TrainingDiagnosticsSummaryOutput,
    TrainingInitOutput,
    TrainingNextScenarioOutput,
    TrainingReportHistoryItemOutput,
    TrainingReportOutput,
    TrainingRoundDecisionContextOutput,
    TrainingRoundSubmitOutput,
    TrainingScenarioOutput,
)


class TrainingOutputsTestCase(unittest.TestCase):
    """验证训练输出 DTO 的序列化行为稳定。"""

    def test_init_output_should_omit_empty_optional_candidates(self):
        """没有候选列表时，不应额外吐出可选字段。"""
        payload = TrainingInitOutput(
            session_id="s-1",
            status="in_progress",
            round_no=0,
            k_state={"K1": 0.4},
            s_state={"credibility": 0.6},
            next_scenario={"id": "S1"},
            scenario_candidates=None,
        ).to_dict()

        self.assertNotIn("scenario_candidates", payload)
        self.assertEqual(payload["next_scenario"]["id"], "S1")

    def test_next_output_should_keep_empty_candidates_for_completed_state(self):
        """已完成状态下，空候选列表也应显式保留。"""
        payload = TrainingNextScenarioOutput(
            session_id="s-1",
            status="completed",
            round_no=3,
            scenario=None,
            scenario_candidates=[],
            k_state={"K1": 0.8},
            s_state={"credibility": 0.9},
            ending={"type": "steady"},
        ).to_dict()

        self.assertIn("scenario_candidates", payload)
        self.assertEqual(payload["scenario_candidates"], [])
        self.assertEqual(payload["ending"]["type"], "steady")

    def test_report_output_should_serialize_nested_history_items(self):
        """训练报告应把嵌套历史项一并导出成稳定字典。"""
        payload = TrainingReportOutput(
            session_id="s-1",
            status="completed",
            rounds=2,
            k_state_final={"K1": 0.8},
            s_state_final={"credibility": 0.9},
            improvement=0.2,
            ending={"type": "excellent"},
            summary={
                "weighted_score_initial": 0.45,
                "weighted_score_final": 0.8,
                "weighted_score_delta": 0.35,
                "strongest_improved_skill_code": "K1",
                "strongest_improved_skill_delta": 0.3,
                "weakest_skill_code": "K2",
                "weakest_skill_score": 0.55,
                "dominant_risk_flag": "source_exposure_risk",
                "high_risk_round_count": 1,
                "high_risk_round_nos": [2],
                "risk_flag_counts": [{"code": "source_exposure_risk", "count": 1}],
                "completed_scenario_ids": ["S1", "S2"],
                "review_suggestions": ["建议优先补练 K2"],
            },
            ability_radar=[
                {"code": "K1", "initial": 0.5, "final": 0.8, "delta": 0.3, "weight": 0.2, "is_highest_gain": True}
            ],
            state_radar=[
                {"code": "credibility", "initial": 0.6, "final": 0.9, "delta": 0.3}
            ],
            growth_curve=[
                {
                    "round_no": 0,
                    "scenario_title": "初始状态",
                    "k_state": {"K1": 0.5},
                    "s_state": {"credibility": 0.6},
                    "weighted_k_score": 0.45,
                },
                {
                    "round_no": 1,
                    "scenario_id": "S1",
                    "scenario_title": "场景1",
                    "k_state": {"K1": 0.8},
                    "s_state": {"credibility": 0.9},
                    "weighted_k_score": 0.8,
                    "is_high_risk": False,
                    "risk_flags": [],
                },
            ],
            history=[
                TrainingReportHistoryItemOutput(
                    round_no=1,
                    scenario_id="S1",
                    user_input="hello",
                    selected_option="A",
                    evaluation={"confidence": 0.8},
                    k_state_before={"K1": 0.4},
                    k_state_after={"K1": 0.5},
                    s_state_before={"credibility": 0.6},
                    s_state_after={"credibility": 0.7},
                    timestamp="2026-03-16T00:00:00",
                )
            ],
        ).to_dict()

        self.assertEqual(payload["history"][0]["scenario_id"], "S1")
        self.assertEqual(payload["history"][0]["evaluation"]["confidence"], 0.8)
        self.assertEqual(payload["summary"]["strongest_improved_skill_code"], "K1")
        self.assertEqual(payload["ability_radar"][0]["weight"], 0.2)
        self.assertEqual(payload["state_radar"][0]["code"], "credibility")
        self.assertEqual(payload["growth_curve"][0]["round_no"], 0)
        self.assertEqual(payload["growth_curve"][1]["scenario_id"], "S1")

    def test_scenario_output_should_serialize_options_recommendation_and_extra_fields(self):
        """场景 DTO 应保留推荐信息、选项和扩展字段。"""
        scenario = TrainingScenarioOutput.from_payload(
            {
                "id": "S1",
                "title": "标题",
                "mission": "任务",
                "target_skills": ["K1"],
                "risk_tags": ["risk_a"],
                "options": [{"id": "A", "label": "选项A", "impact_hint": "提示"}],
                "recommendation": {
                    "mode": "self-paced",
                    "rank_score": 0.9,
                    "weakness_score": 0.8,
                    "state_boost_score": 0.1,
                    "risk_boost_score": 0.2,
                    "phase_boost_score": 0.05,
                    "reasons": ["因为短板"],
                    "rank": 1,
                },
                "custom_field": "extra",
            }
        )

        payload = scenario.to_dict()
        self.assertEqual(payload["options"][0]["id"], "A")
        self.assertEqual(payload["recommendation"]["mode"], "self-paced")
        self.assertEqual(payload["recommendation"]["risk_boost_score"], 0.2)
        self.assertEqual(payload["recommendation"]["phase_boost_score"], 0.05)
        self.assertEqual(payload["custom_field"], "extra")

    def test_round_submit_output_should_normalize_evaluation_and_keep_extra_fields(self):
        """提交结果中的评估应被对象化，并保留扩展字段。"""
        payload = TrainingRoundSubmitOutput(
            session_id="s-1",
            round_no=1,
            evaluation={"eval_mode": "rules_only", "custom_flag": "extra"},
            k_state={"K1": 0.5},
            s_state={"credibility": 0.7},
            is_completed=False,
        ).to_dict()

        self.assertEqual(payload["evaluation"]["eval_mode"], "rules_only")
        self.assertIn("llm_model", payload["evaluation"])
        self.assertEqual(payload["evaluation"]["custom_flag"], "extra")

    def test_round_submit_output_should_serialize_decision_context(self):
        """提交结果应显式导出结构化决策上下文，便于前端回放推荐过程。"""
        payload = TrainingRoundSubmitOutput(
            session_id="s-1",
            round_no=1,
            evaluation={"eval_mode": "rules_only"},
            k_state={"K1": 0.5},
            s_state={"credibility": 0.7},
            is_completed=False,
            decision_context={
                "mode": "self-paced",
                "selection_source": "candidate_pool",
                "selected_scenario_id": "S1",
                "recommended_scenario_id": "S3",
                "candidate_pool": [
                    {
                        "id": "S3",
                        "title": "推荐题",
                        "recommendation": {"rank": 1, "rank_score": 0.91},
                        "is_recommended": True,
                    },
                    {
                        "scenario_id": "S1",
                        "title": "用户选择题",
                        "rank": 2,
                        "rank_score": 0.72,
                        "is_selected": True,
                    },
                ],
                "selected_recommendation": {"mode": "self-paced", "rank": 2, "rank_score": 0.72},
                "recommended_recommendation": {"mode": "self-paced", "rank": 1, "rank_score": 0.91},
            },
        ).to_dict()

        self.assertEqual(payload["decision_context"]["selection_source"], "candidate_pool")
        self.assertEqual(payload["decision_context"]["candidate_pool"][0]["rank"], 1)
        self.assertEqual(payload["decision_context"]["candidate_pool"][0]["rank_score"], 0.91)
        self.assertTrue(payload["decision_context"]["candidate_pool"][1]["is_selected"])

    def test_report_history_item_should_serialize_decision_context(self):
        """报告历史项应保留提交时的决策上下文，供训练复盘使用。"""
        decision_context = TrainingRoundDecisionContextOutput.from_payload(
            {
                "mode": "guided",
                "selection_source": "ordered_sequence",
                "selected_scenario_id": "S1",
                "candidate_pool": [{"scenario_id": "S1", "title": "固定题", "is_selected": True}],
            }
        )
        payload = TrainingReportHistoryItemOutput(
            round_no=1,
            scenario_id="S1",
            user_input="hello",
            selected_option="A",
            evaluation={"confidence": 0.8},
            k_state_before={"K1": 0.4},
            k_state_after={"K1": 0.5},
            s_state_before={"credibility": 0.6},
            s_state_after={"credibility": 0.7},
            timestamp="2026-03-16T00:00:00",
            decision_context=decision_context,
        ).to_dict()

        self.assertEqual(payload["decision_context"]["mode"], "guided")
        self.assertEqual(payload["decision_context"]["candidate_pool"][0]["scenario_id"], "S1")

    def test_report_history_item_should_serialize_kt_observation(self):
        """报告历史项应显式导出 KT 结构化观测，便于前端直接做诊断展示。"""
        payload = TrainingReportHistoryItemOutput(
            round_no=1,
            scenario_id="S1",
            user_input="hello",
            selected_option="A",
            evaluation={"confidence": 0.8},
            k_state_before={"K1": 0.4},
            k_state_after={"K1": 0.5},
            s_state_before={"credibility": 0.6},
            s_state_after={"credibility": 0.7},
            kt_observation={
                "round_no": 1,
                "scenario_id": "S1",
                "scenario_title": "固定题",
                "training_mode": "guided",
                "primary_skill_code": "K1",
                "is_high_risk": False,
                "target_skills": ["K1"],
                "weak_skills_before": ["K1"],
                "risk_flags": [],
                "focus_tags": ["K1"],
                "evidence": ["ok"],
                "skill_observations": [{"code": "K1", "before": 0.4, "delta": 0.1, "after": 0.5, "is_target": True}],
                "state_observations": [],
                "observation_summary": "第1轮场景《固定题》；重点关注 K1",
            },
        ).to_dict()

        self.assertEqual(payload["kt_observation"]["primary_skill_code"], "K1")
        self.assertEqual(payload["kt_observation"]["skill_observations"][0]["code"], "K1")

    def test_diagnostics_output_should_serialize_nested_training_artifacts(self):
        """训练诊断输出应稳定导出推荐日志、审计事件和 KT 观测。"""
        payload = TrainingDiagnosticsOutput(
            session_id="s-1",
            status="in_progress",
            round_no=1,
            summary=TrainingDiagnosticsSummaryOutput(
                total_recommendation_logs=1,
                total_audit_events=1,
                total_kt_observations=1,
                high_risk_round_count=0,
                high_risk_round_nos=[],
                recommended_vs_selected_mismatch_count=1,
                recommended_vs_selected_mismatch_rounds=[1],
                risk_flag_counts=[],
                primary_skill_focus_counts=[{"code": "K1", "count": 1}],
                top_weak_skills=[{"code": "K1", "count": 1}],
                selection_source_counts=[{"code": "candidate_pool", "count": 1}],
                event_type_counts=[{"code": "round_submitted", "count": 1}],
                last_primary_skill_code="K1",
                last_event_type="round_submitted",
            ),
            recommendation_logs=[
                {
                    "round_no": 1,
                    "training_mode": "self-paced",
                    "selection_source": "candidate_pool",
                    "recommended_scenario_id": "S2",
                    "selected_scenario_id": "S1",
                    "candidate_pool": [{"scenario_id": "S2", "title": "推荐题", "rank": 1, "rank_score": 0.9}],
                }
            ],
            audit_events=[
                {
                    "event_type": "round_submitted",
                    "round_no": 1,
                    "payload": {"scenario_id": "S1"},
                    "timestamp": "2026-03-17T00:00:00",
                }
            ],
            kt_observations=[
                {
                    "round_no": 1,
                    "scenario_id": "S1",
                    "scenario_title": "固定题",
                    "training_mode": "guided",
                    "primary_skill_code": "K1",
                    "is_high_risk": False,
                    "target_skills": ["K1"],
                    "weak_skills_before": ["K1"],
                    "risk_flags": [],
                    "focus_tags": ["K1"],
                    "evidence": ["ok"],
                    "skill_observations": [],
                    "state_observations": [],
                    "observation_summary": "第1轮场景《固定题》；重点关注 K1",
                }
            ],
        ).to_dict()

        self.assertEqual(payload["recommendation_logs"][0]["selected_scenario_id"], "S1")
        self.assertEqual(payload["audit_events"][0]["event_type"], "round_submitted")
        self.assertEqual(payload["kt_observations"][0]["scenario_id"], "S1")
        self.assertEqual(payload["summary"]["recommended_vs_selected_mismatch_rounds"], [1])
        self.assertEqual(payload["summary"]["selection_source_counts"][0]["code"], "candidate_pool")

    def test_scenario_output_should_backfill_brief_from_legacy_briefing(self):
        scenario = TrainingScenarioOutput.from_payload(
            {
                "id": "S-legacy",
                "title": "legacy",
                "briefing": "legacy-only-briefing",
            }
        )

        payload = scenario.to_dict()
        self.assertEqual(payload["brief"], "legacy-only-briefing")
        self.assertNotIn("briefing", payload)

    def test_scenario_output_should_prefer_brief_as_canonical_source(self):
        scenario = TrainingScenarioOutput.from_payload(
            {
                "id": "S-canonical",
                "title": "canonical",
                "brief": "canonical-brief",
                "briefing": "stale-legacy-briefing",
            }
        )

        payload = scenario.to_dict()
        self.assertEqual(payload["brief"], "canonical-brief")
        self.assertNotIn("briefing", payload)


if __name__ == "__main__":
    unittest.main()
