"""训练路由层测试：验证响应包装与接口契约。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_training_query_service, get_training_service
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import training
from training.exceptions import (
    TrainingModeUnsupportedError,
    TrainingScenarioMismatchError,
    TrainingSessionNotFoundError,
    TrainingSessionRecoveryStateError,
)


class _FakeTrainingService:
    """最小训练服务桩：只返回稳定数据，不触发真实数据库依赖。"""

    def init_training(self, user_id, character_id=None, training_mode="guided", player_profile=None):
        return {
            "session_id": "s-test",
            "status": "in_progress",
            "round_no": 0,
            "k_state": {"K1": 0.45},
            "s_state": {"credibility": 0.6},
            "player_profile": player_profile,
            "runtime_state": {
                "current_round_no": 0,
                "current_scene_id": "S1",
                "k_state": {"K1": 0.45},
                "s_state": {"credibility": 0.6},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.55,
                    "public_stability": 0.7,
                    "source_safety": 0.65,
                },
            },
            "next_scenario": {"id": "S1"},
            "scenario_candidates": [{"id": "S1"}, {"id": "S2"}],
        }

    def get_next_scenario(self, session_id):
        return {
            "session_id": session_id,
            "status": "completed",
            "round_no": 3,
            "scenario": None,
            "scenario_candidates": [],
            "k_state": {"K1": 0.72},
            "s_state": {"credibility": 0.83},
            "player_profile": {"name": "李敏", "gender": "女", "identity": "战地记者"},
            "runtime_state": {
                "current_round_no": 3,
                "current_scene_id": "S3",
                "k_state": {"K1": 0.72},
                "s_state": {"credibility": 0.83},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.7,
                    "public_stability": 0.82,
                    "source_safety": 0.8,
                },
            },
            "ending": {"ending_type": "steady"},
        }

    def submit_round(self, session_id, scenario_id, user_input, selected_option=None, media_tasks=None):
        return {
            "session_id": session_id,
            "round_no": 1,
            "evaluation": {"eval_mode": "rules_only"},
            "k_state": {"K1": 0.5},
            "s_state": {"credibility": 0.7},
            "player_profile": {"name": "李敏", "gender": "女", "identity": "战地记者"},
            "runtime_state": {
                "current_round_no": 1,
                "current_scene_id": scenario_id,
                "k_state": {"K1": 0.5},
                "s_state": {"credibility": 0.7},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.62,
                    "public_stability": 0.74,
                    "source_safety": 0.68,
                },
            },
            "consequence_events": [
                {
                    "event_type": "editor_trust_recovered",
                    "label": "编辑部信任恢复",
                    "summary": "本轮后编辑部信任回升。",
                    "severity": "low",
                    "round_no": 1,
                    "related_flag": "editor_locked",
                    "state_bar": {
                        "editor_trust": 0.62,
                        "public_stability": 0.74,
                        "source_safety": 0.68,
                    },
                    "payload": {"scenario_id": scenario_id},
                }
            ],
            "is_completed": False,
            "ending": None,
            "decision_context": {
                "mode": "self-paced",
                "selection_source": "candidate_pool",
                "selected_scenario_id": scenario_id,
                "recommended_scenario_id": "S2",
                "candidate_pool": [
                    {"scenario_id": "S2", "title": "推荐题", "rank": 1, "rank_score": 0.8, "is_recommended": True},
                    {"scenario_id": scenario_id, "title": "用户选择题", "rank": 2, "rank_score": 0.7, "is_selected": True},
                ],
                "selected_recommendation": {
                    "mode": "self-paced",
                    "rank": 2,
                    "rank_score": 0.7,
                    "weakness_score": 0.4,
                    "state_boost_score": 0.1,
                    "risk_boost_score": 0.0,
                    "phase_boost_score": 0.2,
                    "reasons": ["用户从候选池中选择了次优题"],
                },
                "recommended_recommendation": {
                    "mode": "self-paced",
                    "rank": 1,
                    "rank_score": 0.8,
                    "weakness_score": 0.6,
                    "state_boost_score": 0.1,
                    "risk_boost_score": 0.0,
                    "phase_boost_score": 0.2,
                    "reasons": ["系统推荐得分最高"],
                },
            },
        }

    def get_session_summary(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "in_progress",
            "training_mode": "self-paced",
            "current_round_no": 1,
            "total_rounds": 6,
            "k_state": {"K1": 0.5},
            "s_state": {"credibility": 0.7},
            "progress_anchor": {
                "current_round_no": 1,
                "total_rounds": 6,
                "completed_rounds": 1,
                "remaining_rounds": 5,
                "progress_percent": 16.67,
                "next_round_no": 2,
            },
            "player_profile": {"name": "Li Min", "identity": "Reporter"},
            "runtime_state": {
                "current_round_no": 1,
                "current_scene_id": "S2",
                "k_state": {"K1": 0.5},
                "s_state": {"credibility": 0.7},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.62,
                    "public_stability": 0.74,
                    "source_safety": 0.68,
                },
            },
            "resumable_scenario": {"id": "S2", "title": "Resume Scenario"},
            "scenario_candidates": [
                {"id": "S2", "title": "Resume Scenario"},
                {"id": "S3", "title": "Alt Scenario"},
            ],
            "can_resume": True,
            "is_completed": False,
            "created_at": "2026-03-20T10:00:00",
            "updated_at": "2026-03-20T10:05:00",
            "end_time": None,
        }

    def get_progress(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "in_progress",
            "round_no": 1,
            "total_rounds": 6,
            "k_state": {"K1": 0.5},
            "s_state": {"credibility": 0.7},
            "player_profile": {"name": "李敏", "gender": "女", "identity": "战地记者"},
            "runtime_state": {
                "current_round_no": 1,
                "current_scene_id": "S1",
                "k_state": {"K1": 0.5},
                "s_state": {"credibility": 0.7},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.62,
                    "public_stability": 0.74,
                    "source_safety": 0.68,
                },
            },
        }

    def get_history(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "in_progress",
            "training_mode": "self-paced",
            "current_round_no": 1,
            "total_rounds": 6,
            "progress_anchor": {
                "current_round_no": 1,
                "total_rounds": 6,
                "completed_rounds": 1,
                "remaining_rounds": 5,
                "progress_percent": 16.67,
                "next_round_no": 2,
            },
            "player_profile": {"name": "Li Min", "identity": "Reporter"},
            "runtime_state": {
                "current_round_no": 1,
                "current_scene_id": "S1",
                "k_state": {"K1": 0.5},
                "s_state": {"credibility": 0.7},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.62,
                    "public_stability": 0.74,
                    "source_safety": 0.68,
                },
            },
            "history": [
                {
                    "round_no": 1,
                    "scenario_id": "S1",
                    "user_input": "hello",
                    "selected_option": None,
                    "evaluation": {"eval_mode": "rules_only"},
                    "k_state_before": {"K1": 0.4},
                    "k_state_after": {"K1": 0.5},
                    "s_state_before": {"credibility": 0.6},
                    "s_state_after": {"credibility": 0.7},
                    "timestamp": "2026-03-16T00:00:00",
                    "consequence_events": [],
                }
            ],
            "is_completed": False,
            "created_at": "2026-03-20T10:00:00",
            "updated_at": "2026-03-20T10:05:00",
            "end_time": None,
        }

    def get_report(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "completed",
            "rounds": 6,
            "k_state_final": {"K1": 0.9},
            "s_state_final": {"credibility": 0.88},
            "improvement": 0.22,
            "player_profile": {"name": "李敏", "gender": "女", "identity": "战地记者"},
            "runtime_state": {
                "current_round_no": 6,
                "current_scene_id": "S6",
                "k_state": {"K1": 0.9},
                "s_state": {"credibility": 0.88},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.88,
                    "public_stability": 0.91,
                    "source_safety": 0.9,
                },
            },
            "ending": {"ending_type": "excellent"},
            "summary": {
                "weighted_score_initial": 0.45,
                "weighted_score_final": 0.9,
                "weighted_score_delta": 0.45,
                "strongest_improved_skill_code": "K1",
                "strongest_improved_skill_delta": 0.45,
                "weakest_skill_code": "K2",
                "weakest_skill_score": 0.61,
                "dominant_risk_flag": "source_exposure_risk",
                "high_risk_round_count": 1,
                "high_risk_round_nos": [1],
                "panic_trigger_round_count": 0,
                "source_exposed_round_count": 1,
                "editor_locked_round_count": 0,
                "high_risk_path_round_count": 0,
                "risk_flag_counts": [{"code": "source_exposure_risk", "count": 1}],
                "completed_scenario_ids": ["S1"],
                "review_suggestions": ["建议优先复盘来源保护相关风险"],
            },
            "ability_radar": [
                {
                    "code": "K1",
                    "initial": 0.45,
                    "final": 0.9,
                    "delta": 0.45,
                    "weight": 0.2,
                    "is_highest_gain": True,
                }
            ],
            "state_radar": [
                {
                    "code": "credibility",
                    "initial": 0.6,
                    "final": 0.88,
                    "delta": 0.28,
                }
            ],
            "growth_curve": [
                {
                    "round_no": 0,
                    "scenario_title": "初始状态",
                    "k_state": {"K1": 0.45},
                    "s_state": {"credibility": 0.6},
                    "weighted_k_score": 0.45,
                    "risk_flags": [],
                },
                {
                    "round_no": 1,
                    "scenario_id": "S1",
                    "scenario_title": "固定题",
                    "k_state": {"K1": 0.5},
                    "s_state": {"credibility": 0.7},
                    "weighted_k_score": 0.5,
                    "is_high_risk": False,
                    "risk_flags": [],
                    "primary_skill_code": "K1",
                }
            ],
            "history": [
                {
                    "round_no": 1,
                    "scenario_id": "S1",
                    "user_input": "hello",
                    "selected_option": None,
                    "evaluation": {"eval_mode": "rules_only"},
                    "k_state_before": {"K1": 0.4},
                    "k_state_after": {"K1": 0.5},
                    "s_state_before": {"credibility": 0.6},
                    "s_state_after": {"credibility": 0.7},
                    "timestamp": "2026-03-16T00:00:00",
                    "decision_context": {
                        "mode": "guided",
                        "selection_source": "ordered_sequence",
                        "selected_scenario_id": "S1",
                        "candidate_pool": [{"scenario_id": "S1", "title": "固定题", "is_selected": True}],
                    },
                    "kt_observation": {
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
                        "skill_observations": [
                            {"code": "K1", "before": 0.4, "delta": 0.1, "after": 0.5, "is_target": True}
                        ],
                        "state_observations": [],
                        "observation_summary": "第1轮场景《固定题》；重点关注 K1",
                    },
                    "runtime_state": {
                        "current_round_no": 1,
                        "current_scene_id": "S1",
                        "k_state": {"K1": 0.5},
                        "s_state": {"credibility": 0.7},
                        "runtime_flags": {
                            "panic_triggered": False,
                            "source_exposed": True,
                            "editor_locked": False,
                            "high_risk_path": False,
                        },
                        "state_bar": {
                            "editor_trust": 0.62,
                            "public_stability": 0.74,
                            "source_safety": 0.3,
                        },
                    },
                    "consequence_events": [
                        {
                            "event_type": "source_exposed",
                            "label": "来源暴露",
                            "summary": "触发了来源保护红线。",
                            "severity": "high",
                            "round_no": 1,
                            "related_flag": "source_exposed",
                            "payload": {"scenario_id": "S1"},
                        }
                    ],
                }
            ],
        }

    def get_diagnostics(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "in_progress",
            "round_no": 1,
            "player_profile": {"name": "李敏", "gender": "女", "identity": "战地记者"},
            "runtime_state": {
                "current_round_no": 1,
                "current_scene_id": "S1",
                "k_state": {"K1": 0.5},
                "s_state": {"credibility": 0.7},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": True,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.62,
                    "public_stability": 0.74,
                    "source_safety": 0.3,
                },
            },
            "summary": {
                "total_recommendation_logs": 1,
                "total_audit_events": 1,
                "total_kt_observations": 1,
                "high_risk_round_count": 0,
                "high_risk_round_nos": [],
                "recommended_vs_selected_mismatch_count": 1,
                "recommended_vs_selected_mismatch_rounds": [1],
                "risk_flag_counts": [],
                "primary_skill_focus_counts": [{"code": "K1", "count": 1}],
                "top_weak_skills": [{"code": "K1", "count": 1}],
                "selection_source_counts": [{"code": "candidate_pool", "count": 1}],
                "event_type_counts": [{"code": "round_submitted", "count": 1}],
                "phase_tag_counts": [{"code": "opening", "count": 1}],
                "phase_transition_count": 0,
                "phase_transition_rounds": [],
                "panic_trigger_round_count": 0,
                "panic_trigger_rounds": [],
                "source_exposed_round_count": 1,
                "source_exposed_rounds": [1],
                "editor_locked_round_count": 0,
                "editor_locked_rounds": [],
                "high_risk_path_round_count": 0,
                "high_risk_path_rounds": [],
                "last_primary_skill_code": "K1",
                "last_event_type": "round_submitted",
                "last_phase_tags": ["opening"],
            },
            "recommendation_logs": [
                {
                    "round_no": 1,
                    "training_mode": "self-paced",
                    "selection_source": "candidate_pool",
                    "recommended_scenario_id": "S2",
                    "selected_scenario_id": "S1",
                    "candidate_pool": [
                        {"scenario_id": "S2", "title": "推荐题", "rank": 1, "rank_score": 0.8, "is_recommended": True}
                    ],
                }
            ],
            "audit_events": [
                {
                    "event_type": "round_submitted",
                    "round_no": 1,
                    "payload": {"scenario_id": "S1"},
                    "timestamp": "2026-03-16T00:00:00",
                }
            ],
            "kt_observations": [
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
        }


class TrainingRouterTestCase(unittest.TestCase):
    """验证训练路由使用了稳定的响应包装和 schema。"""

    def setUp(self):
        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(training.router, prefix="/api")
        fake_service = _FakeTrainingService()
        self.app.dependency_overrides[get_training_service] = lambda: fake_service
        self.app.dependency_overrides[get_training_query_service] = lambda: fake_service
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_init_route_should_return_wrapped_success_payload(self):
        """初始化接口应返回 code/message/data 包装后的结构。"""
        response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": "u-router", "training_mode": "self-paced"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["session_id"], "s-test")
        self.assertEqual(len(payload["data"]["scenario_candidates"]), 2)
        self.assertEqual(payload["data"]["runtime_state"]["current_scene_id"], "S1")

    def test_init_route_should_accept_player_profile(self):
        """初始化接口应允许提交玩家档案，并按原结构回显。"""
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "u-router",
                "training_mode": "self-paced",
                "player_profile": {
                    "name": "李敏",
                    "gender": "女",
                    "identity": "战地记者",
                },
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["player_profile"]["name"], "李敏")
        self.assertEqual(payload["data"]["player_profile"]["identity"], "战地记者")

    def test_init_route_should_reject_story_thread_id_field(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "u-router",
                "training_mode": "self-paced",
                "thread_id": "thread-legacy",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["path"], "/api/v1/training/init")
        self.assertEqual(payload["error"]["details"]["errors"][0]["field"], "thread_id")
        self.assertEqual(payload["error"]["details"]["errors"][0]["type"], "extra_forbidden")

    def test_init_route_should_reject_unknown_player_profile_fields(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "u-router",
                "training_mode": "self-paced",
                "player_profile": {
                    "name": "Li Min",
                    "nickname": "legacy-field",
                },
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["path"], "/api/v1/training/init")
        self.assertEqual(payload["error"]["details"]["errors"][0]["field"], "player_profile.nickname")
        self.assertEqual(payload["error"]["details"]["errors"][0]["type"], "extra_forbidden")

    def test_next_route_should_reject_story_thread_id_field(self):
        response = self.client.post(
            "/api/v1/training/scenario/next",
            json={
                "session_id": "s-test",
                "thread_id": "thread-legacy",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["path"], "/api/v1/training/scenario/next")
        self.assertEqual(payload["error"]["details"]["errors"][0]["field"], "thread_id")
        self.assertEqual(payload["error"]["details"]["errors"][0]["type"], "extra_forbidden")

    def test_next_route_should_keep_completed_payload_shape_stable(self):
        """下一场景接口在 completed 状态下也应返回稳定字段。"""
        response = self.client.post(
            "/api/v1/training/scenario/next",
            json={"session_id": "s-test"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["status"], "completed")
        self.assertIsNone(payload["data"]["scenario"])
        self.assertEqual(payload["data"]["scenario_candidates"], [])
        self.assertEqual(payload["data"]["ending"]["ending_type"], "steady")

    def test_session_summary_route_should_return_recovery_payload(self):
        response = self.client.get("/api/v1/training/sessions/s-test")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["session_id"], "s-test")
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["training_mode"], "self-paced")
        self.assertEqual(payload["data"]["progress_anchor"]["next_round_no"], 2)
        self.assertEqual(payload["data"]["progress_anchor"]["progress_percent"], 16.67)
        self.assertEqual(payload["data"]["resumable_scenario"]["id"], "S2")
        self.assertEqual(len(payload["data"]["scenario_candidates"]), 2)
        self.assertTrue(payload["data"]["can_resume"])

    def test_session_summary_route_should_return_not_found_error_code(self):
        self.app.dependency_overrides[get_training_query_service] = lambda: _MissingSessionTrainingService()

        response = self.client.get("/api/v1/training/sessions/missing-session")

        payload = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_NOT_FOUND")
        self.assertEqual(payload["error"]["details"]["route"], "training.session_summary")

    def test_session_summary_route_should_return_conflict_for_corrupted_recovery_state(self):
        self.app.dependency_overrides[get_training_query_service] = lambda: _CorruptedSessionTrainingService()

        response = self.client.get("/api/v1/training/sessions/s-corrupted")

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_sequence_empty")
        self.assertEqual(payload["error"]["details"]["route"], "training.session_summary")

    def test_history_route_should_return_canonical_history_payload(self):
        response = self.client.get("/api/v1/training/sessions/s-test/history")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["session_id"], "s-test")
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["training_mode"], "self-paced")
        self.assertEqual(payload["data"]["progress_anchor"]["next_round_no"], 2)
        self.assertEqual(payload["data"]["progress_anchor"]["progress_percent"], 16.67)
        self.assertEqual(payload["data"]["history"][0]["scenario_id"], "S1")
        self.assertFalse(payload["data"]["is_completed"])

    def test_history_route_should_return_conflict_for_corrupted_recovery_state(self):
        self.app.dependency_overrides[get_training_query_service] = lambda: _CorruptedSessionTrainingService()

        response = self.client.get("/api/v1/training/sessions/s-corrupted/history")

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.history")

    def test_init_route_should_return_400_for_invalid_training_mode(self):
        """初始化接口遇到训练模式校验失败时应返回 400。"""
        self.app.dependency_overrides[get_training_service] = lambda: _InvalidModeTrainingService()

        response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": "u-router", "training_mode": "sandbox"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["code"], 400)
        self.assertEqual(payload["error"]["code"], "TRAINING_MODE_UNSUPPORTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.init")
        self.assertEqual(payload["error"]["details"]["provided_mode"], "sandbox")
        self.assertEqual(
            payload["error"]["details"]["supported_modes"],
            ["guided", "self-paced", "adaptive"],
        )

    def test_submit_route_should_return_conflict_for_scenario_mismatch(self):
        self.app.dependency_overrides[get_training_service] = lambda: _ScenarioMismatchTrainingService()

        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-test",
                "scenario_id": "S999",
                "user_input": "hello",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SCENARIO_MISMATCH")
        self.assertEqual(payload["error"]["details"]["route"], "training.submit_round")
        self.assertEqual(payload["error"]["details"]["session_id"], "s-test")
        self.assertEqual(payload["error"]["details"]["scenario_id"], "S999")
        self.assertEqual(payload["error"]["details"]["expected_scenario_id"], "S1")
        self.assertEqual(payload["error"]["details"]["round_no"], 1)

    def test_submit_route_should_validate_against_explicit_evaluation_schema(self):
        """提交接口应通过显式评估 schema 返回稳定字段。"""
        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-test",
                "scenario_id": "S1",
                "user_input": "hello",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["evaluation"]["eval_mode"], "rules_only")
        self.assertIn("llm_model", payload["data"]["evaluation"])
        self.assertEqual(payload["data"]["decision_context"]["selection_source"], "candidate_pool")
        self.assertEqual(payload["data"]["decision_context"]["candidate_pool"][0]["rank"], 1)
        self.assertEqual(payload["data"]["consequence_events"][0]["event_type"], "editor_trust_recovered")
        self.assertEqual(payload["data"]["runtime_state"]["state_bar"]["editor_trust"], 0.62)

    def test_submit_route_should_dispatch_pending_and_running_media_tasks(self):
        """媒体任务调度在 TrainingService.submit_round 内完成；路由仅转发。桩服务镜像调度逻辑以便断言。"""
        fake_executor = _FakeMediaTaskExecutor()
        service = _SubmitRoundWithMediaTasksTrainingService()
        service.media_task_executor = fake_executor
        self.app.dependency_overrides[get_training_service] = lambda: service

        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-test",
                "scenario_id": "S1",
                "user_input": "hello",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(len(payload["data"]["media_tasks"]), 3)
        self.assertEqual(
            fake_executor.submitted_task_ids,
            ["task-pending", "task-running"],
        )

    def test_submit_route_should_keep_success_when_media_dispatch_resolution_fails(self):
        """单任务 submit 失败时服务层吞掉异常并仍返回成功；桩行为与 TrainingService 一致。"""

        class _ExplodingMediaTaskExecutor:
            def submit_task(self, task_id: str) -> None:
                raise RuntimeError("dispatch failed")

        service = _SubmitRoundWithMediaTasksTrainingService()
        service.media_task_executor = _ExplodingMediaTaskExecutor()
        self.app.dependency_overrides[get_training_service] = lambda: service

        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-test",
                "scenario_id": "S1",
                "user_input": "hello",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(len(payload["data"]["media_tasks"]), 3)

    def test_submit_route_should_reject_story_thread_id_field(self):
        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-test",
                "scenario_id": "S1",
                "user_input": "hello",
                "thread_id": "thread-legacy",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["path"], "/api/v1/training/round/submit")
        self.assertEqual(payload["error"]["details"]["errors"][0]["field"], "thread_id")
        self.assertEqual(payload["error"]["details"]["errors"][0]["type"], "extra_forbidden")

    def test_report_route_should_expose_decision_context_in_history(self):
        """训练报告接口应把历史回放中的决策上下文透传给前端。"""
        response = self.client.get("/api/v1/training/report/s-test")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["history"][0]["decision_context"]["selection_source"], "ordered_sequence")
        self.assertEqual(payload["data"]["history"][0]["kt_observation"]["primary_skill_code"], "K1")
        self.assertEqual(payload["data"]["summary"]["strongest_improved_skill_code"], "K1")
        self.assertEqual(payload["data"]["ability_radar"][0]["code"], "K1")
        self.assertEqual(payload["data"]["growth_curve"][0]["round_no"], 0)

    def test_diagnostics_route_should_return_structured_training_artifacts(self):
        """训练诊断接口应返回推荐日志、审计事件和 KT 观测。"""
        response = self.client.get("/api/v1/training/diagnostics/s-test")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["code"], 200)
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["recommendation_logs"][0]["selection_source"], "candidate_pool")
        self.assertEqual(payload["data"]["audit_events"][0]["event_type"], "round_submitted")
        self.assertEqual(payload["data"]["kt_observations"][0]["primary_skill_code"], "K1")
        self.assertEqual(payload["data"]["summary"]["recommended_vs_selected_mismatch_rounds"], [1])
        self.assertEqual(payload["data"]["summary"]["selection_source_counts"][0]["code"], "candidate_pool")
        self.assertEqual(payload["data"]["summary"]["source_exposed_round_count"], 1)
        self.assertTrue(payload["data"]["runtime_state"]["runtime_flags"]["source_exposed"])

    def test_diagnostics_route_should_return_conflict_for_corrupted_recovery_state(self):
        self.app.dependency_overrides[get_training_query_service] = lambda: _CorruptedSessionTrainingService()

        response = self.client.get("/api/v1/training/diagnostics/s-corrupted")

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.diagnostics")
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_sequence_empty")


class _MissingSessionTrainingService:
    def get_session_summary(self, session_id):
        raise TrainingSessionNotFoundError(session_id=session_id)

    def get_history(self, session_id):
        raise TrainingSessionNotFoundError(session_id=session_id)


class _CorruptedSessionTrainingService:
    def get_session_summary(self, session_id):
        raise TrainingSessionRecoveryStateError(
            session_id=session_id,
            reason="scenario_sequence_empty",
        )

    def get_history(self, session_id):
        raise TrainingSessionRecoveryStateError(
            session_id=session_id,
            reason="scenario_sequence_empty",
        )

    def get_diagnostics(self, session_id):
        raise TrainingSessionRecoveryStateError(
            session_id=session_id,
            reason="scenario_sequence_empty",
        )


class _InvalidModeTrainingService:
    """用于验证路由错误码分支的失败桩。"""

    def init_training(self, user_id, character_id=None, training_mode="guided", player_profile=None):
        raise TrainingModeUnsupportedError(
            raw_mode=training_mode,
            supported_modes=["guided", "self-paced", "adaptive"],
        )


class _ScenarioMismatchTrainingService:
    def submit_round(self, session_id, scenario_id, user_input, selected_option=None, media_tasks=None):
        raise TrainingScenarioMismatchError(
            submitted_scenario_id=scenario_id,
            expected_scenario_id="S1",
            round_no=1,
        )


def _dispatch_round_media_tasks_like_training_service(executor, media_tasks: list | None) -> None:
    """与 TrainingService.submit_round 中对 round_media_tasks 的调度规则一致（仅测桩使用）。"""
    if executor is None or not media_tasks:
        return
    for item in media_tasks:
        task_id = str((item or {}).get("task_id") or "").strip()
        status = str((item or {}).get("status") or "").strip().lower()
        if not task_id or status not in {"pending", "running"}:
            continue
        try:
            executor.submit_task(task_id)
        except Exception:
            pass


class _SubmitRoundWithMediaTasksTrainingService(_FakeTrainingService):
    def submit_round(self, session_id, scenario_id, user_input, selected_option=None, media_tasks=None):
        payload = super().submit_round(
            session_id=session_id,
            scenario_id=scenario_id,
            user_input=user_input,
            selected_option=selected_option,
            media_tasks=media_tasks,
        )
        payload["media_tasks"] = [
            {"task_id": "task-pending", "task_type": "image", "status": "pending"},
            {"task_id": "task-running", "task_type": "tts", "status": "running"},
            {"task_id": "task-succeeded", "task_type": "text", "status": "succeeded"},
        ]
        _dispatch_round_media_tasks_like_training_service(
            getattr(self, "media_task_executor", None),
            payload["media_tasks"],
        )
        return payload


class _FakeMediaTaskExecutor:
    def __init__(self):
        self.submitted_task_ids: list[str] = []

    def submit_task(self, task_id: str) -> None:
        self.submitted_task_ids.append(task_id)


if __name__ == "__main__":
    unittest.main()
