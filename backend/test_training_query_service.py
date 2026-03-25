"""Training query service tests.

These tests protect PR-BE-07 query boundaries:
1. GET paths must not write session state
2. Missing persisted snapshots must fail with typed recovery errors
"""

from __future__ import annotations

import unittest

from api.services.training_service import TrainingService
from backend.test_training_service import _FakeDbManager, _FakeEvaluator
from training.exceptions import TrainingSessionRecoveryStateError
from training.training_query_service import TrainingQueryService


class _RecordingFakeDbManager(_FakeDbManager):
    def __init__(self):
        super().__init__()
        self.update_calls = []

    def update_training_session(self, session_id, updates):
        self.update_calls.append((session_id, dict(updates or {})))
        return super().update_training_session(session_id, updates)


class _CountingTrainingStore:
    """记录 query 路径对 training_store 的调用次数，防止回归到 N+1 或写路径泄漏。"""

    def __init__(self, delegate):
        self._delegate = delegate
        self.calls: dict[str, int] = {}

    def __getattr__(self, name):
        target = getattr(self._delegate, name)
        if not callable(target):
            return target

        def _wrapped(*args, **kwargs):
            self.calls[name] = self.calls.get(name, 0) + 1
            return target(*args, **kwargs)

        return _wrapped


class TrainingQueryServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.db = _RecordingFakeDbManager()
        self.service = TrainingService(
            db_manager=self.db,
            evaluator=_FakeEvaluator(),
        )
        self.query_service = TrainingQueryService(
            training_store=self.service.training_store,
            scenario_policy=self.service.scenario_policy,
            session_snapshot_policy=self.service.session_snapshot_policy,
            flow_policy=self.service.flow_policy,
            reporting_policy=self.service.reporting_policy,
            report_context_policy=self.service.report_context_policy,
            runtime_artifact_policy=self.service.runtime_artifact_policy,
            output_assembler_policy=self.service.output_assembler_policy,
            mode_catalog=self.service.mode_catalog,
        )

    def _create_seeded_session(self):
        init_result = self.service.init_training(
            user_id="u-query",
            character_id=42,
            training_mode="self-paced",
            player_profile={"name": "Li Min", "identity": "Reporter"},
        )
        session_id = init_result["session_id"]
        scenario_id = init_result["next_scenario"]["id"]
        self.service.submit_round(
            session_id=session_id,
            scenario_id=scenario_id,
            user_input="hello",
        )
        self.db.update_calls.clear()
        return session_id, scenario_id

    def test_get_session_summary_should_not_write_during_query(self):
        session_id, _ = self._create_seeded_session()

        summary = self.query_service.get_session_summary(session_id)

        self.assertEqual(summary["session_id"], session_id)
        self.assertEqual(summary["character_id"], 42)
        self.assertEqual(self.db.update_calls, [])

    def test_get_session_summary_should_backfill_legacy_briefing_from_persisted_snapshots(self):
        session_id, _ = self._create_seeded_session()
        session = self.db.sessions[session_id]

        legacy_sequence = []
        for payload in session.session_meta.get("scenario_payload_sequence", []):
            normalized = dict(payload)
            normalized.pop("brief", None)
            normalized["briefing"] = f"legacy-sequence-{normalized['id']}"
            legacy_sequence.append(normalized)

        legacy_catalog = []
        for payload in session.session_meta.get("scenario_payload_catalog", []):
            normalized = dict(payload)
            normalized.pop("brief", None)
            normalized["briefing"] = f"legacy-catalog-{normalized['id']}"
            legacy_catalog.append(normalized)

        session.session_meta["scenario_payload_sequence"] = legacy_sequence
        session.session_meta["scenario_payload_catalog"] = legacy_catalog

        summary = self.query_service.get_session_summary(session_id)

        self.assertEqual(summary["session_id"], session_id)
        self.assertIn("legacy", summary["resumable_scenario"]["brief"])
        self.assertNotIn("briefing", summary["resumable_scenario"])
        if summary["scenario_candidates"]:
            self.assertNotIn("briefing", summary["scenario_candidates"][0])
        self.assertEqual(self.db.update_calls, [])

    def test_get_progress_should_not_write_during_query(self):
        session_id, scenario_id = self._create_seeded_session()

        progress = self.query_service.get_progress(session_id)

        self.assertEqual(progress["session_id"], session_id)
        self.assertEqual(progress["character_id"], 42)
        self.assertEqual(progress["decision_context"]["selected_scenario_id"], scenario_id)
        self.assertIn("consequence_events", progress)
        self.assertIsInstance(progress["consequence_events"], list)
        self.assertEqual(self.db.update_calls, [])

    def test_query_read_models_should_freeze_progress_percent_as_real_percentage(self):
        service = TrainingService(
            db_manager=_RecordingFakeDbManager(),
            evaluator=_FakeEvaluator(),
            scenario_sequence=[
                {"id": "S1", "title": "Intro"},
                {"id": "S2", "title": "Follow Up"},
            ],
        )
        query_service = TrainingQueryService(
            training_store=service.training_store,
            scenario_policy=service.scenario_policy,
            session_snapshot_policy=service.session_snapshot_policy,
            flow_policy=service.flow_policy,
            reporting_policy=service.reporting_policy,
            report_context_policy=service.report_context_policy,
            runtime_artifact_policy=service.runtime_artifact_policy,
            output_assembler_policy=service.output_assembler_policy,
            mode_catalog=service.mode_catalog,
        )
        init_result = service.init_training(user_id="u-progress-percent", training_mode="self-paced")
        session_id = init_result["session_id"]
        service.submit_round(
            session_id=session_id,
            scenario_id="S1",
            user_input="hello",
        )

        summary = query_service.get_session_summary(session_id)
        history = query_service.get_history(session_id)

        self.assertEqual(summary["progress_anchor"]["progress_percent"], 50.0)
        self.assertEqual(history["progress_anchor"]["progress_percent"], 50.0)

    def test_get_history_should_not_write_during_query(self):
        session_id, scenario_id = self._create_seeded_session()

        history = self.query_service.get_history(session_id)

        self.assertEqual(history["session_id"], session_id)
        self.assertEqual(history["character_id"], 42)
        self.assertEqual(history["history"][0]["scenario_id"], scenario_id)
        self.assertEqual(self.db.update_calls, [])

    def test_get_report_should_not_write_during_query(self):
        session_id, scenario_id = self._create_seeded_session()

        report = self.query_service.get_report(session_id)

        self.assertEqual(report["session_id"], session_id)
        self.assertEqual(report["character_id"], 42)
        self.assertEqual(report["history"][0]["scenario_id"], scenario_id)
        self.assertEqual(self.db.update_calls, [])

    def test_get_diagnostics_should_not_write_during_query(self):
        session_id, _ = self._create_seeded_session()

        diagnostics = self.query_service.get_diagnostics(session_id)

        self.assertEqual(diagnostics["session_id"], session_id)
        self.assertEqual(diagnostics["character_id"], 42)
        self.assertEqual(self.db.update_calls, [])

    def test_get_session_summary_should_raise_typed_error_when_snapshots_are_missing(self):
        session_id, _ = self._create_seeded_session()
        session = self.db.sessions[session_id]
        session.session_meta.pop("scenario_payload_sequence", None)
        session.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.query_service.get_session_summary(session_id)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(
            cm.exception.details["missing_fields"],
            ["scenario_payload_sequence", "scenario_payload_catalog"],
        )
        self.assertEqual(self.db.update_calls, [])

    def test_get_session_summary_should_raise_typed_error_when_flow_policy_build_fails(self):
        session_id, _ = self._create_seeded_session()

        def _broken_build_next_scenario_bundle(**kwargs):
            raise ValueError("forced round scenario not found in session sequence")

        self.query_service.flow_policy.build_next_scenario_bundle = _broken_build_next_scenario_bundle

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.query_service.get_session_summary(session_id)

        self.assertEqual(cm.exception.reason, "scenario_flow_unavailable")
        self.assertEqual(cm.exception.details["phase"], "summary_resume")
        self.assertIn("forced round scenario not found", cm.exception.details["flow_error"])
        self.assertEqual(self.db.update_calls, [])

    def test_get_progress_should_raise_typed_error_when_snapshots_are_missing(self):
        session_id, _ = self._create_seeded_session()
        session = self.db.sessions[session_id]
        session.session_meta.pop("scenario_payload_sequence", None)
        session.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.query_service.get_progress(session_id)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(self.db.update_calls, [])

    def test_get_report_should_raise_typed_error_when_snapshots_are_missing(self):
        session_id, _ = self._create_seeded_session()
        session = self.db.sessions[session_id]
        session.session_meta.pop("scenario_payload_sequence", None)
        session.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.query_service.get_report(session_id)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(self.db.update_calls, [])

    def test_get_diagnostics_should_raise_typed_error_when_snapshots_are_missing(self):
        session_id, _ = self._create_seeded_session()
        session = self.db.sessions[session_id]
        session.session_meta.pop("scenario_payload_sequence", None)
        session.session_meta.pop("scenario_payload_catalog", None)

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.query_service.get_diagnostics(session_id)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(self.db.update_calls, [])

    def test_get_report_should_use_constant_store_read_calls_without_write_side_effects(self):
        """报告读取应保持常量级 store 读取次数，避免回归到逐回合查询或写路径泄漏。"""
        init_result = self.service.init_training(
            user_id="u-query-perf",
            character_id=77,
            training_mode="self-paced",
        )
        session_id = init_result["session_id"]
        first_scenario_id = init_result["next_scenario"]["id"]

        # 扩大回合规模，验证 report 查询不会随轮次增加额外 store 往返次数。
        self.service.submit_round(
            session_id=session_id,
            scenario_id=first_scenario_id,
            user_input="round-1",
        )
        self.service.submit_round(
            session_id=session_id,
            scenario_id="S2",
            user_input="round-2",
        )
        self.service.submit_round(
            session_id=session_id,
            scenario_id="S3",
            user_input="round-3",
        )

        counting_store = _CountingTrainingStore(self.service.training_store)
        query_service = TrainingQueryService(
            training_store=counting_store,
            scenario_policy=self.service.scenario_policy,
            session_snapshot_policy=self.service.session_snapshot_policy,
            flow_policy=self.service.flow_policy,
            reporting_policy=self.service.reporting_policy,
            report_context_policy=self.service.report_context_policy,
            runtime_artifact_policy=self.service.runtime_artifact_policy,
            output_assembler_policy=self.service.output_assembler_policy,
            mode_catalog=self.service.mode_catalog,
        )

        report = query_service.get_report(session_id)

        self.assertEqual(report["session_id"], session_id)
        self.assertEqual(report["rounds"], 3)
        self.assertEqual(report["character_id"], 77)

        self.assertEqual(counting_store.calls.get("get_training_session", 0), 1)
        self.assertEqual(counting_store.calls.get("get_training_rounds", 0), 1)
        self.assertEqual(counting_store.calls.get("get_round_evaluations_by_session", 0), 1)
        self.assertEqual(counting_store.calls.get("get_kt_observations", 0), 1)
        self.assertEqual(counting_store.calls.get("get_ending_result", 0), 1)

        self.assertEqual(counting_store.calls.get("update_training_session", 0), 0)
        self.assertEqual(counting_store.calls.get("save_training_round_artifacts", 0), 0)
        self.assertEqual(counting_store.calls.get("create_training_session", 0), 0)


if __name__ == "__main__":
    unittest.main()
