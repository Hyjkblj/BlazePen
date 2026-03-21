"""会话场景快照策略测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from training.exceptions import TrainingSessionRecoveryStateError
from training.scenario_repository import ScenarioRepository
from training.session_snapshot_policy import SessionScenarioSnapshotPolicy


class _MemoryTrainingStore:
    """最小内存存储桩：仅覆盖快照回填需要的更新接口。"""

    def __init__(self):
        self.sessions = {}

    def update_training_session(self, session_id, updates):
        session = self.sessions.get(session_id)
        if session is None:
            return None
        for key, value in updates.items():
            setattr(session, key, value)
        return session


class _FailOnRepositoryRead:
    """用于验证目录快照存在时不会回退读取实时仓储。"""

    def get_scenario(self, scenario_id):
        raise AssertionError(f"unexpected repository fallback: {scenario_id}")


class _FallbackRepository:
    """用于验证目录缺失时会回退读取实时仓储。"""

    def __init__(self):
        self.requested_ids = []

    def get_scenario(self, scenario_id):
        self.requested_ids.append(str(scenario_id))
        return {
            "id": str(scenario_id),
            "title": f"fallback-{scenario_id}",
            "options": [],
            "next_rules": [],
        }


class SessionScenarioSnapshotPolicyTestCase(unittest.TestCase):
    """验证会话场景快照策略的冻结、回填与解析行为。"""

    def setUp(self):
        self.repository = ScenarioRepository()
        self.policy = SessionScenarioSnapshotPolicy(scenario_repository=self.repository)

    def test_freeze_session_snapshots_should_include_reachable_branch_catalog(self):
        """新会话冻结时，应一次性产出主线快照与可达分支目录。"""
        bundle = self.policy.freeze_session_snapshots(
            [
                {"id": "S1", "title": "卢沟桥"},
                {"id": "S2", "title": "淞沪"},
                {"id": "S3", "title": "南京"},
                {"id": "S4", "title": "武汉"},
            ]
        )

        self.assertEqual(bundle.scenario_payload_sequence[0]["id"], "S1")
        catalog_ids = [item["id"] for item in bundle.scenario_payload_catalog]
        self.assertIn("S2B", catalog_ids)
        self.assertIn("S3R", catalog_ids)

    def test_ensure_session_snapshots_should_backfill_missing_payloads_and_catalog(self):
        """历史会话只有摘要序列时，应惰性补齐完整快照并回写存储层。"""
        store = _MemoryTrainingStore()
        session = SimpleNamespace(
            session_id="s-backfill",
            session_meta={
                "scenario_sequence": [
                    {"id": "S1", "title": "卢沟桥"},
                    {"id": "S2", "title": "淞沪"},
                    {"id": "S3", "title": "南京"},
                    {"id": "S4", "title": "武汉"},
                ]
            },
        )
        store.sessions[session.session_id] = session

        bundle = self.policy.ensure_session_snapshots(session=session, training_store=store)

        self.assertEqual(bundle.session.session_id, "s-backfill")
        self.assertTrue(bundle.scenario_payload_sequence)
        self.assertTrue(bundle.scenario_payload_catalog)
        self.assertIn("scenario_payload_sequence", session.session_meta)
        self.assertIn("scenario_payload_catalog", session.session_meta)

    def test_require_session_snapshots_should_raise_typed_error_when_payloads_are_missing(self):
        session = SimpleNamespace(
            session_id="s-corrupted",
            current_round_no=1,
            session_meta={
                "scenario_sequence": [
                    {"id": "S1", "title": "卢沟桥"},
                    {"id": "S2", "title": "淞沪"},
                ]
            },
        )

        with self.assertRaises(TrainingSessionRecoveryStateError) as cm:
            self.policy.require_session_snapshots(session_id="s-corrupted", session=session)

        self.assertEqual(cm.exception.reason, "scenario_snapshots_missing")
        self.assertEqual(
            cm.exception.details["missing_fields"],
            ["scenario_payload_sequence", "scenario_payload_catalog"],
        )

    def test_resolve_scenario_payload_by_id_should_prefer_catalog_without_repository_fallback(self):
        """目录快照存在时，应直接从目录解析分支场景，不回退实时仓储。"""
        bundle = self.policy.freeze_session_snapshots(
            [
                {"id": "S1", "title": "卢沟桥"},
                {"id": "S2", "title": "淞沪"},
                {"id": "S3", "title": "南京"},
                {"id": "S4", "title": "武汉"},
            ]
        )
        policy = SessionScenarioSnapshotPolicy(scenario_repository=_FailOnRepositoryRead())

        payload = policy.resolve_scenario_payload_by_id(
            scenario_id="S2B",
            scenario_payload_sequence=bundle.scenario_payload_sequence,
            scenario_payload_catalog=bundle.scenario_payload_catalog,
        )

        self.assertIsNotNone(payload)
        self.assertEqual(payload["id"], "S2B")

    def test_resolve_scenario_payload_by_id_should_fallback_to_repository_when_catalog_missing(self):
        """旧链路缺少目录快照时，应回退到实时仓储读取场景。"""
        fallback_repository = _FallbackRepository()
        policy = SessionScenarioSnapshotPolicy(scenario_repository=fallback_repository)

        payload = policy.resolve_scenario_payload_by_id(
            scenario_id="S2B",
            scenario_payload_sequence=[{"id": "S1", "title": "卢沟桥"}],
            scenario_payload_catalog=None,
        )

        self.assertIsNotNone(payload)
        self.assertEqual(payload["id"], "S2B")
        self.assertEqual(payload["title"], "fallback-S2B")
        self.assertEqual(fallback_repository.requested_ids, ["S2B"])

    def test_resolve_scenario_payload_by_id_should_not_fallback_when_catalog_exists_but_not_matched(self):
        """目录快照已存在但未命中时，应返回空而不是偷偷回退实时仓储。"""
        policy = SessionScenarioSnapshotPolicy(scenario_repository=_FailOnRepositoryRead())

        payload = policy.resolve_scenario_payload_by_id(
            scenario_id="S2B",
            scenario_payload_sequence=[{"id": "S1", "title": "卢沟桥"}],
            scenario_payload_catalog=[{"id": "S3", "title": "南京"}],
        )

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
