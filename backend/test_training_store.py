"""训练存储适配层测试。"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from training.training_store import (
    DatabaseTrainingStore,
    EndingResultRecord,
    KtObservationRecord,
    RoundEvaluationRecord,
    ScenarioRecommendationLogRecord,
    TrainingAuditEventRecord,
    TrainingRoundRecord,
    TrainingSessionRecord,
)


class _FakeStoreDbManager:
    """最小数据库桩：用于验证适配层的返回对象映射。"""

    def __init__(self):
        self.session_row = SimpleNamespace(
            session_id="s-1",
            user_id="u-1",
            character_id=1,
            training_mode="self-paced",
            status="in_progress",
            current_round_no=2,
            current_scenario_id="S2",
            k_state={"K1": 0.7},
            s_state={"credibility": 0.8},
            session_meta={"scenario_sequence": [{"id": "S1", "title": "t"}]},
            end_time=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.round_row = SimpleNamespace(
            round_id="r-1",
            session_id="s-1",
            round_no=2,
            scenario_id="S2",
            user_input_raw="hello",
            selected_option="A",
            user_action={"selected_option": "A"},
            state_before={"credibility": 0.7},
            state_after={"credibility": 0.8},
            kt_before={"K1": 0.6},
            kt_after={"K1": 0.7},
            feedback_text="ok",
            created_at=datetime.utcnow(),
        )
        self.evaluation_row = SimpleNamespace(
            round_id="r-1",
            llm_model="rules_v1",
            raw_payload={"confidence": 0.8},
            risk_flags=["source_exposure_risk"],
        )
        self.ending_row = SimpleNamespace(
            session_id="s-1",
            report_payload={"type": "steady"},
        )
        self.recommendation_log_row = SimpleNamespace(
            recommendation_log_id="rec-1",
            session_id="s-1",
            round_no=2,
            training_mode="self-paced",
            selection_source="candidate_pool",
            recommended_scenario_id="S3",
            selected_scenario_id="S2",
            candidate_pool=[{"scenario_id": "S3", "rank": 1}, {"scenario_id": "S2", "rank": 2}],
            recommended_recommendation={"mode": "self-paced", "rank": 1},
            selected_recommendation={"mode": "self-paced", "rank": 2},
            decision_context={"selection_source": "candidate_pool"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.audit_event_row = SimpleNamespace(
            event_id="audit-1",
            session_id="s-1",
            event_type="round_submitted",
            round_no=2,
            payload={"scenario_id": "S2"},
            created_at=datetime.utcnow(),
        )
        self.kt_observation_row = SimpleNamespace(
            observation_id="obs-1",
            session_id="s-1",
            round_no=2,
            scenario_id="S2",
            scenario_title="战地采访",
            training_mode="self-paced",
            primary_skill_code="K5",
            primary_risk_flag=None,
            is_high_risk=False,
            target_skills=["K5"],
            weak_skills_before=["K5", "K2"],
            risk_flags=[],
            focus_tags=["K5", "source"],
            evidence=["ok"],
            skill_observations=[{"code": "K5", "before": 0.3, "delta": 0.1, "after": 0.4, "is_target": True}],
            state_observations=[],
            observation_summary="第2轮场景《战地采访》；重点关注 K5；能力变化 K5+0.1000",
            raw_payload={"scenario_id": "S2"},
            created_at=datetime.utcnow(),
        )

    def create_training_session_artifacts(self, **kwargs):
        return self.session_row

    def create_training_session(self, **kwargs):
        return self.session_row

    def get_training_session(self, session_id):
        return self.session_row

    def get_training_rounds(self, session_id):
        return [self.round_row]

    def get_training_round_by_session_round(self, session_id, round_no):
        return self.round_row

    def get_round_evaluations_by_session(self, session_id):
        return [self.evaluation_row]

    def get_round_evaluation_by_round_id(self, round_id):
        return self.evaluation_row

    def create_kt_snapshot(self, session_id, round_no, k_state):
        return SimpleNamespace()

    def create_narrative_snapshot(self, session_id, round_no, s_state):
        return SimpleNamespace()

    def save_training_round_artifacts(self, **kwargs):
        return self.round_row

    def get_ending_result(self, session_id):
        return self.ending_row

    def get_scenario_recommendation_logs(self, session_id):
        return [self.recommendation_log_row]

    def get_training_audit_events(self, session_id):
        return [self.audit_event_row]

    def create_training_audit_event(self, session_id, event_type, round_no=None, payload=None):
        return self.audit_event_row

    def get_kt_observations(self, session_id):
        return [self.kt_observation_row]

    def create_kt_observation(self, session_id, round_no, payload):
        return self.kt_observation_row


class _LegacySaveArtifactsDbManager(_FakeStoreDbManager):
    """模拟旧版自定义 db_manager：提交接口还不认识新增的可选参数。"""

    def save_training_round_artifacts(
        self,
        session_id,
        round_no,
        scenario_id,
        user_input_raw,
        selected_option,
        user_action,
        state_before,
        state_after,
        kt_before,
        kt_after,
        feedback_text,
        evaluation_payload,
        ending_payload,
        status,
        end_time,
    ):
        return self.round_row


class DatabaseTrainingStoreTestCase(unittest.TestCase):
    """验证训练存储适配层会输出稳定记录模型。"""

    def setUp(self):
        self.store = DatabaseTrainingStore(_FakeStoreDbManager())

    def test_should_map_session_and_round_records(self):
        """会话和回合读取应返回明确的数据记录对象。"""
        session = self.store.get_training_session("s-1")
        rounds = self.store.get_training_rounds("s-1")

        self.assertIsInstance(session, TrainingSessionRecord)
        self.assertEqual(session.training_mode, "self-paced")
        self.assertIsInstance(rounds[0], TrainingRoundRecord)
        self.assertEqual(rounds[0].scenario_id, "S2")

    def test_should_map_evaluation_and_ending_records(self):
        """评估和结局读取也应返回稳定记录对象。"""
        evaluation = self.store.get_round_evaluation_by_round_id("r-1")
        ending = self.store.get_ending_result("s-1")

        self.assertIsInstance(evaluation, RoundEvaluationRecord)
        self.assertEqual(evaluation.risk_flags, ["source_exposure_risk"])
        self.assertIsInstance(ending, EndingResultRecord)
        self.assertEqual(ending.report_payload["type"], "steady")

    def test_should_map_recommendation_log_audit_event_and_kt_observation_records(self):
        """推荐日志、审计事件和 KT 观测都应被适配成稳定记录模型。"""
        recommendation_logs = self.store.get_scenario_recommendation_logs("s-1")
        audit_events = self.store.get_training_audit_events("s-1")
        kt_observations = self.store.get_kt_observations("s-1")

        self.assertIsInstance(recommendation_logs[0], ScenarioRecommendationLogRecord)
        self.assertEqual(recommendation_logs[0].recommended_scenario_id, "S3")
        self.assertIsInstance(audit_events[0], TrainingAuditEventRecord)
        self.assertEqual(audit_events[0].event_type, "round_submitted")
        self.assertIsInstance(kt_observations[0], KtObservationRecord)
        self.assertEqual(kt_observations[0].primary_skill_code, "K5")

    def test_should_compatibly_call_legacy_save_artifacts_signature(self):
        """适配层应兼容旧版 db_manager 的提交签名，避免新增可选参数直接打断注入式测试桩。"""
        store = DatabaseTrainingStore(_LegacySaveArtifactsDbManager())

        row = store.save_training_round_artifacts(
            session_id="s-1",
            round_no=1,
            scenario_id="S1",
            user_input_raw="hello",
            selected_option=None,
            user_action={},
            state_before={},
            state_after={},
            kt_before={},
            kt_after={},
            feedback_text="ok",
            evaluation_payload={"confidence": 0.8},
            ending_payload=None,
            status="in_progress",
            end_time=None,
            recommendation_log_payload={"training_mode": "guided"},
            audit_event_payloads=[{"event_type": "round_submitted"}],
            kt_observation_payload={"scenario_id": "S1"},
        )

        self.assertIsInstance(row, TrainingRoundRecord)
        self.assertEqual(row.scenario_id, "S2")


if __name__ == "__main__":
    unittest.main()
