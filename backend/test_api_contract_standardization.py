"""API contract regression tests for the backend-only PR-02 slice."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_story_service_bundle, get_training_query_service, get_training_service
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import characters, game, training
from story.exceptions import (
    StorySessionAccessDeniedError,
    StorySessionExpiredError,
    StorySessionNotFoundError,
)
from story.story_asset_service import StoryAssetService
from training.exceptions import (
    TrainingModeUnsupportedError,
    TrainingScenarioMismatchError,
    TrainingSessionNotFoundError,
    TrainingSessionRecoveryStateError,
)


class _FakeGameService:
    story_asset_service = StoryAssetService()

    def init_game(self, user_id=None, character_id=None, game_mode="solo"):
        return {
            "thread_id": "thread-001",
            "user_id": user_id or "user-001",
            "game_mode": game_mode,
        }

    def initialize_story(
        self,
        thread_id: str,
        character_id: int,
        scene_id: str = "school",
        character_image_url=None,
        opening_event_id=None,
    ):
        return {
            "event_title": "初遇",
            "story_background": "背景",
            "scene": scene_id,
            "character_dialogue": "你好",
            "player_options": [{"id": 1, "text": "继续"}],
            "scene_image_url": "/static/images/scenes/a.png",
            "composite_image_url": None,
            "round_no": 0,
            "snapshot": {
                "thread_id": thread_id,
                "status": "in_progress",
                "round_no": 0,
                "scene": scene_id,
            },
        }

    def process_input(self, thread_id: str, user_input: str, option_id=None):
        return {
            "character_dialogue": f"收到:{user_input or option_id}",
            "player_options": [{"id": 1, "text": "下一步"}],
            "story_background": "处理中",
            "event_title": "回合",
            "scene": "school_gate",
            "is_event_finished": True,
            "is_game_finished": False,
            "round_no": 1,
            "snapshot": {
                "thread_id": thread_id,
                "status": "in_progress",
                "round_no": 1,
                "scene": "school_gate",
            },
        }

    def check_ending(self, thread_id: str):
        return {"has_ending": False, "ending": None}

    def trigger_ending(self, thread_id: str):
        return {
            "event_title": "结局",
            "story_background": "结束",
            "scene": "ending",
            "ending_type": "open_ending",
            "character_dialogue": "再见",
            "player_options": [],
            "is_game_finished": True,
            "round_no": 3,
            "snapshot": {
                "thread_id": thread_id,
                "status": "completed",
                "round_no": 3,
                "scene": "ending",
            },
        }

    def get_story_session_snapshot(self, thread_id: str):
        return {
            "thread_id": thread_id,
            "status": "in_progress",
            "round_no": 2,
            "character_dialogue": "继续中",
            "player_options": [{"id": 1, "text": "继续"}],
            "story_background": "快照背景",
            "event_title": "快照事件",
            "scene": "library",
            "snapshot": {
                "thread_id": thread_id,
                "status": "in_progress",
                "round_no": 2,
                "scene": "library",
                "updated_at": "2026-03-19T12:00:00",
                "expires_at": "2026-03-20T12:00:00",
            },
            "updated_at": "2026-03-19T12:00:00",
            "expires_at": "2026-03-20T12:00:00",
        }

    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ):
        return {
            "user_id": user_id,
            "sessions": [
                {
                    "thread_id": "thread-001",
                    "user_id": user_id,
                    "character_id": 7,
                    "game_mode": "solo",
                    "status": "in_progress",
                    "round_no": 2,
                    "scene": "library",
                    "event_title": "Snapshot Event",
                    "is_initialized": True,
                    "has_ending": False,
                    "can_resume": True,
                    "updated_at": "2026-03-19T12:00:00",
                    "expires_at": "2026-03-20T12:00:00",
                }
            ][:limit],
        }

    def submit_story_turn(
        self,
        *,
        thread_id: str,
        user_input: str,
        option_id=None,
        user_id=None,
        character_id=None,
    ):
        return self.process_input(thread_id=thread_id, user_input=user_input, option_id=option_id)

    def normalize_story_turn_payload(self, result, *, thread_id: str):
        from api.story_contract_utils import normalize_story_turn_payload

        return normalize_story_turn_payload(
            result,
            thread_id=thread_id,
            story_asset_service=self.story_asset_service,
        )

    @property
    def session_manager(self):
        return _FakeSessionManager(self)


class _FakeSession:
    def __init__(self):
        self.lock = _NoopLock()


class _NoopLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSessionManager:
    def __init__(self, service: _FakeGameService):
        self.service = service

    def get_session(self, thread_id: str):
        return _FakeSession()


class _RestoringGameService(_FakeGameService):
    def submit_story_turn(
        self,
        *,
        thread_id: str,
        user_input: str,
        option_id=None,
        user_id=None,
        character_id=None,
    ):
        return {
            "thread_id": "thread-restored",
            "character_dialogue": "会话已恢复",
            "player_options": [{"id": 1, "text": "继续"}],
            "story_background": "恢复成功",
            "event_title": "初遇",
            "scene": "school",
            "round_no": 0,
            "session_restored": True,
            "need_reselect_option": True,
            "restored_from_thread_id": thread_id,
            "snapshot": {
                "thread_id": "thread-restored",
                "status": "in_progress",
                "round_no": 0,
                "scene": "school",
            },
        }


class _NotFoundInitGameService(_FakeGameService):
    def initialize_story(
        self,
        thread_id: str,
        character_id: int,
        scene_id: str = "school",
        character_image_url=None,
        opening_event_id=None,
    ):
        raise StorySessionNotFoundError(thread_id=thread_id)


class _ExpiredInitGameService(_FakeGameService):
    def initialize_story(
        self,
        thread_id: str,
        character_id: int,
        scene_id: str = "school",
        character_image_url=None,
        opening_event_id=None,
    ):
        raise StorySessionExpiredError(thread_id=thread_id)


class _NotFoundCheckEndingGameService(_FakeGameService):
    def check_ending(self, thread_id: str):
        raise StorySessionNotFoundError(thread_id=thread_id)


class _ExpiredCheckEndingGameService(_FakeGameService):
    def check_ending(self, thread_id: str):
        raise StorySessionExpiredError(thread_id=thread_id)


class _DeniedSessionsGameService(_FakeGameService):
    def list_story_sessions(
        self,
        *,
        user_id: str,
        limit: int = 10,
        actor_user_id: str | None = None,
    ):
        raise StorySessionAccessDeniedError(
            requested_user_id=user_id,
            actor_user_id=actor_user_id,
            policy_mode="actor_header_match",
        )


def _build_story_bundle(service: _FakeGameService):
    return SimpleNamespace(
        story_asset_service=service.story_asset_service,
        story_session_service=SimpleNamespace(
            init_game=service.init_game,
            get_session_snapshot=service.get_story_session_snapshot,
            list_recent_sessions=service.list_story_sessions,
        ),
        story_turn_service=SimpleNamespace(
            initialize_story=service.initialize_story,
            submit_turn=service.submit_story_turn,
        ),
        story_ending_service=SimpleNamespace(
            check_ending=service.check_ending,
            get_ending_summary=lambda thread_id: {
                "thread_id": thread_id,
                "status": "completed",
                "round_no": 3,
                "has_ending": bool(service.check_ending(thread_id).get("has_ending", False)),
                "ending": service.check_ending(thread_id).get("ending"),
            },
            trigger_ending=service.trigger_ending,
        ),
        story_history_service=SimpleNamespace(
            get_story_history=lambda thread_id: {
                "thread_id": thread_id,
                "status": "in_progress",
                "current_round_no": 0,
                "history": [],
            },
        ),
    )


class _FakeTrainingService:
    def init_training(self, user_id, character_id=None, training_mode="guided", player_profile=None):
        if training_mode == "sandbox":
            raise TrainingModeUnsupportedError(
                raw_mode=training_mode,
                supported_modes=["guided", "self-paced", "adaptive"],
            )
        return {
            "session_id": "s-001",
            "character_id": 42 if character_id is None else character_id,
            "status": "in_progress",
            "round_no": 0,
            "k_state": {"K1": 0.4},
            "s_state": {"credibility": 0.6},
            "player_profile": player_profile,
            "runtime_state": {
                "current_round_no": 0,
                "current_scene_id": "S1",
                "k_state": {"K1": 0.4},
                "s_state": {"credibility": 0.6},
                "runtime_flags": {
                    "panic_triggered": False,
                    "source_exposed": False,
                    "editor_locked": False,
                    "high_risk_path": False,
                },
                "state_bar": {
                    "editor_trust": 0.5,
                    "public_stability": 0.7,
                    "source_safety": 0.8,
                },
            },
            "next_scenario": {"id": "S1"},
            "scenario_candidates": [{"id": "S1"}],
        }

    def get_next_scenario(self, session_id):
        if session_id == "missing":
            raise TrainingSessionNotFoundError(session_id=session_id)
        if session_id == "corrupted":
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_flow_unavailable",
                details={"phase": "resume_bundle"},
            )
        return {
            "session_id": session_id,
            "status": "in_progress",
            "round_no": 1,
            "scenario": {"id": "S2"},
            "scenario_candidates": [{"id": "S2"}],
            "k_state": {"K1": 0.5},
            "s_state": {"credibility": 0.7},
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
                    "editor_trust": 0.55,
                    "public_stability": 0.75,
                    "source_safety": 0.82,
                },
            },
            "ending": None,
        }

    def submit_round(self, session_id, scenario_id, user_input, selected_option=None):
        if scenario_id == "S999":
            raise TrainingScenarioMismatchError(
                submitted_scenario_id=scenario_id,
                expected_scenario_id="S1",
                round_no=1,
            )
        if scenario_id == "S-BROKEN":
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_flow_unavailable",
                details={"phase": "submit_validation"},
            )
        return {
            "session_id": session_id,
            "round_no": 1,
            "evaluation": {"llm_model": "rules_v1"},
            "k_state": {"K1": 0.5},
            "s_state": {"credibility": 0.7},
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
                    "editor_trust": 0.55,
                    "public_stability": 0.75,
                    "source_safety": 0.82,
                },
            },
            "consequence_events": [],
            "is_completed": False,
        }

    def get_session_summary(self, session_id):
        if session_id == "missing":
            raise TrainingSessionNotFoundError(session_id=session_id)
        if session_id == "corrupted":
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_sequence_empty",
            )
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
            "resumable_scenario": {"id": "S2", "title": "Resume Scenario"},
            "scenario_candidates": [{"id": "S2", "title": "Resume Scenario"}],
            "can_resume": True,
            "is_completed": False,
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
        }

    def get_history(self, session_id):
        if session_id == "missing":
            raise TrainingSessionNotFoundError(session_id=session_id)
        if session_id == "corrupted":
            raise TrainingSessionRecoveryStateError(
                session_id=session_id,
                reason="scenario_sequence_empty",
            )
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
            "history": [],
            "is_completed": False,
        }

    def get_report(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "completed",
            "rounds": 1,
            "k_state_final": {"K1": 0.5},
            "s_state_final": {"credibility": 0.7},
            "improvement": 0.1,
            "history": [],
        }

    def get_diagnostics(self, session_id):
        return {
            "session_id": session_id,
            "character_id": 42,
            "status": "in_progress",
            "round_no": 1,
            "recommendation_logs": [],
            "audit_events": [],
            "kt_observations": [],
        }


class ApiContractStandardizationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(game.router, prefix="/api")
        self.app.include_router(characters.router, prefix="/api")
        self.app.include_router(training.router, prefix="/api")
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_FakeGameService())
        )
        fake_training_service = _FakeTrainingService()
        self.app.dependency_overrides[get_training_service] = lambda: fake_training_service
        self.app.dependency_overrides[get_training_query_service] = lambda: fake_training_service
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_story_init_returns_stable_status(self):
        response = self.client.post(
            "/api/v1/game/init",
            json={"game_mode": "solo", "character_id": "7", "user_id": "u-001"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], "thread-001")
        self.assertEqual(payload["data"]["status"], "initialized")

    def test_story_turn_response_always_carries_current_thread_id(self):
        response = self.client.post(
            "/api/v1/game/input",
            json={"thread_id": "thread-001", "user_input": "继续", "character_id": "7"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], "thread-001")
        self.assertEqual(payload["data"]["status"], "in_progress")
        self.assertEqual(payload["data"]["round_no"], 1)
        self.assertFalse(payload["data"]["session_restored"])

    def test_story_invalid_option_format_returns_error_code_and_trace(self):
        response = self.client.post(
            "/api/v1/game/input",
            json={"thread_id": "thread-001", "user_input": "option:abc", "character_id": "7"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertTrue(payload["error"]["traceId"])

    def test_story_initialize_route_returns_normalized_payload(self):
        response = self.client.post(
            "/api/v1/characters/initialize-story",
            json={"thread_id": "thread-001", "character_id": "7", "scene_id": "school"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], "thread-001")
        self.assertEqual(payload["data"]["status"], "in_progress")
        self.assertEqual(payload["data"]["round_no"], 0)
        self.assertEqual(payload["data"]["scene"], "school")
        self.assertEqual(payload["data"]["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(payload["data"]["assets"]["composite_image"]["status"], "failed")

    def test_story_initialize_route_is_also_available_under_story_domain(self):
        response = self.client.post(
            "/api/v1/game/initialize-story",
            json={"thread_id": "thread-001", "character_id": "7", "scene_id": "school"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], "thread-001")
        self.assertEqual(payload["data"]["status"], "in_progress")
        self.assertEqual(payload["data"]["scene"], "school")
        self.assertEqual(payload["data"]["assets"]["scene_image"]["status"], "ready")

    def test_story_initialize_routes_share_validation_contract(self):
        for route_path in (
            "/api/v1/characters/initialize-story",
            "/api/v1/game/initialize-story",
        ):
            response = self.client.post(
                route_path,
                json={"thread_id": "thread-001", "character_id": "not-an-int", "scene_id": "school"},
            )

            payload = response.json()
            self.assertEqual(response.status_code, 422)
            self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_story_initialize_routes_share_not_found_contract(self):
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_NotFoundInitGameService())
        )

        for route_path in (
            "/api/v1/characters/initialize-story",
            "/api/v1/game/initialize-story",
        ):
            response = self.client.post(
                route_path,
                json={"thread_id": "missing-thread", "character_id": "7", "scene_id": "school"},
            )

            payload = response.json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(payload["error"]["code"], "STORY_SESSION_NOT_FOUND")

    def test_story_initialize_routes_share_expired_contract(self):
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_ExpiredInitGameService())
        )

        for route_path in (
            "/api/v1/characters/initialize-story",
            "/api/v1/game/initialize-story",
        ):
            response = self.client.post(
                route_path,
                json={"thread_id": "expired-thread", "character_id": "7", "scene_id": "school"},
            )

            payload = response.json()
            self.assertEqual(response.status_code, 410)
            self.assertEqual(payload["error"]["code"], "STORY_SESSION_EXPIRED")

    def test_story_restore_path_returns_reselect_contract(self):
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_RestoringGameService())
        )

        response = self.client.post(
            "/api/v1/game/input",
            json={"thread_id": "thread-old", "user_input": "option:1", "character_id": "7"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["message"], "会话已恢复，请重新选择选项")
        self.assertTrue(payload["data"]["session_restored"])
        self.assertTrue(payload["data"]["need_reselect_option"])
        self.assertEqual(payload["data"]["status"], "reselect_required")

    def test_story_snapshot_route_returns_restorable_payload(self):
        response = self.client.get("/api/v1/game/sessions/thread-001")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["thread_id"], "thread-001")
        self.assertEqual(payload["data"]["round_no"], 2)
        self.assertEqual(payload["data"]["scene"], "library")
        self.assertEqual(payload["data"]["updated_at"], "2026-03-19T12:00:00")

    def test_story_sessions_route_returns_stable_forbidden_error_code(self):
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_DeniedSessionsGameService())
        )

        response = self.client.get(
            "/api/v1/game/sessions",
            params={"user_id": "u-001"},
            headers={"X-Story-Actor-Id": "u-999"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_ACCESS_DENIED")
        self.assertEqual(payload["error"]["details"]["route"], "story.sessions_list")
        self.assertTrue(payload["error"]["traceId"])

    def test_story_check_ending_route_returns_stable_not_found_error_code(self):
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_NotFoundCheckEndingGameService())
        )

        response = self.client.get("/api/v1/game/check-ending/missing-thread")

        payload = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_NOT_FOUND")
        self.assertTrue(payload["error"]["traceId"])

    def test_story_check_ending_route_returns_stable_expired_error_code(self):
        self.app.dependency_overrides[get_story_service_bundle] = (
            lambda: _build_story_bundle(_ExpiredCheckEndingGameService())
        )

        response = self.client.get("/api/v1/game/check-ending/expired-thread")

        payload = response.json()
        self.assertEqual(response.status_code, 410)
        self.assertEqual(payload["error"]["code"], "STORY_SESSION_EXPIRED")
        self.assertTrue(payload["error"]["traceId"])

    def test_training_session_summary_route_returns_stable_envelope(self):
        response = self.client.get("/api/v1/training/sessions/s-001")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["session_id"], "s-001")
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["training_mode"], "self-paced")
        self.assertEqual(payload["data"]["progress_anchor"]["next_round_no"], 2)
        self.assertEqual(payload["data"]["progress_anchor"]["progress_percent"], 16.67)
        self.assertEqual(payload["data"]["resumable_scenario"]["id"], "S2")
        self.assertNotIn("briefing", payload["data"]["resumable_scenario"])
        self.assertNotIn("briefing", payload["data"]["scenario_candidates"][0])

    def test_training_init_route_returns_canonical_character_id(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": "u-001", "character_id": 7, "training_mode": "guided"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["session_id"], "s-001")
        self.assertEqual(payload["data"]["character_id"], 7)
        self.assertNotIn("briefing", payload["data"]["next_scenario"])
        self.assertNotIn("briefing", payload["data"]["scenario_candidates"][0])

    def test_training_session_summary_route_returns_stable_recovery_conflict(self):
        response = self.client.get("/api/v1/training/sessions/corrupted")

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.session_summary")
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_sequence_empty")
        self.assertTrue(payload["error"]["traceId"])

    def test_training_history_route_returns_stable_envelope(self):
        response = self.client.get("/api/v1/training/sessions/s-001/history")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["session_id"], "s-001")
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["training_mode"], "self-paced")
        self.assertEqual(payload["data"]["progress_anchor"]["next_round_no"], 2)
        self.assertEqual(payload["data"]["progress_anchor"]["progress_percent"], 16.67)
        self.assertEqual(payload["data"]["history"], [])

    def test_training_progress_route_returns_canonical_character_id(self):
        response = self.client.get("/api/v1/training/progress/s-001")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["session_id"], "s-001")
        self.assertEqual(payload["data"]["character_id"], 42)
        self.assertEqual(payload["data"]["round_no"], 1)
        self.assertEqual(payload["data"]["total_rounds"], 6)

    def test_training_history_route_returns_stable_recovery_conflict(self):
        response = self.client.get("/api/v1/training/sessions/corrupted/history")

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.history")
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_sequence_empty")
        self.assertTrue(payload["error"]["traceId"])

    def test_training_init_invalid_mode_returns_stable_error_code(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={"user_id": "u-001", "training_mode": "sandbox"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], "TRAINING_MODE_UNSUPPORTED")
        self.assertEqual(payload["error"]["details"]["provided_mode"], "sandbox")
        self.assertEqual(
            payload["error"]["details"]["supported_modes"],
            ["guided", "self-paced", "adaptive"],
        )
        self.assertTrue(payload["error"]["traceId"])

    def test_training_submit_scenario_mismatch_returns_stable_error_code(self):
        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-001",
                "scenario_id": "S999",
                "user_input": "继续",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SCENARIO_MISMATCH")
        self.assertEqual(payload["error"]["details"]["route"], "training.submit_round")
        self.assertEqual(payload["error"]["details"]["session_id"], "s-001")
        self.assertEqual(payload["error"]["details"]["scenario_id"], "S999")
        self.assertEqual(payload["error"]["details"]["expected_scenario_id"], "S1")
        self.assertEqual(payload["error"]["details"]["round_no"], 1)
        self.assertTrue(payload["error"]["traceId"])

    def test_training_request_validation_rejects_story_fields_with_stable_error_envelope(self):
        cases = (
            (
                "/api/v1/training/init",
                {
                    "user_id": "u-001",
                    "training_mode": "guided",
                    "thread_id": "thread-legacy",
                },
            ),
            (
                "/api/v1/training/scenario/next",
                {
                    "session_id": "s-001",
                    "thread_id": "thread-legacy",
                },
            ),
            (
                "/api/v1/training/round/submit",
                {
                    "session_id": "s-001",
                    "scenario_id": "S1",
                    "user_input": "继续",
                    "thread_id": "thread-legacy",
                },
            ),
        )

        for route_path, payload in cases:
            response = self.client.post(route_path, json=payload)

            error_payload = response.json()
            self.assertEqual(response.status_code, 422)
            self.assertEqual(error_payload["error"]["code"], "VALIDATION_ERROR")
            self.assertEqual(error_payload["error"]["details"]["path"], route_path)
            self.assertEqual(error_payload["error"]["details"]["method"], "POST")
            self.assertEqual(error_payload["error"]["details"]["errors"][0]["source"], "body")
            self.assertEqual(error_payload["error"]["details"]["errors"][0]["field"], "thread_id")
            self.assertEqual(error_payload["error"]["details"]["errors"][0]["type"], "extra_forbidden")
            self.assertTrue(error_payload["error"]["traceId"])

    def test_training_init_validation_reports_nested_unknown_player_profile_field(self):
        response = self.client.post(
            "/api/v1/training/init",
            json={
                "user_id": "u-001",
                "training_mode": "guided",
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
        self.assertEqual(payload["error"]["details"]["errors"][0]["source"], "body")
        self.assertEqual(payload["error"]["details"]["errors"][0]["field"], "player_profile.nickname")
        self.assertEqual(payload["error"]["details"]["errors"][0]["type"], "extra_forbidden")
        self.assertTrue(payload["error"]["traceId"])

    def test_training_next_not_found_returns_stable_error_code(self):
        response = self.client.post(
            "/api/v1/training/scenario/next",
            json={"session_id": "missing"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_NOT_FOUND")
        self.assertTrue(payload["error"]["traceId"])

    def test_training_next_corrupted_state_returns_stable_error_code(self):
        response = self.client.post(
            "/api/v1/training/scenario/next",
            json={"session_id": "corrupted"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.next")
        self.assertEqual(payload["error"]["details"]["session_id"], "corrupted")
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_flow_unavailable")
        self.assertEqual(payload["error"]["details"]["recovery_details"]["phase"], "resume_bundle")
        self.assertTrue(payload["error"]["traceId"])

    def test_training_submit_recovery_conflict_returns_stable_error_code(self):
        response = self.client.post(
            "/api/v1/training/round/submit",
            json={
                "session_id": "s-001",
                "scenario_id": "S-BROKEN",
                "user_input": "continue",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "TRAINING_SESSION_RECOVERY_STATE_CORRUPTED")
        self.assertEqual(payload["error"]["details"]["route"], "training.submit_round")
        self.assertEqual(payload["error"]["details"]["session_id"], "s-001")
        self.assertEqual(payload["error"]["details"]["scenario_id"], "S-BROKEN")
        self.assertEqual(payload["error"]["details"]["recovery_reason"], "scenario_flow_unavailable")
        self.assertEqual(payload["error"]["details"]["recovery_details"]["phase"], "submit_validation")
        self.assertTrue(payload["error"]["traceId"])


if __name__ == "__main__":
    unittest.main()
