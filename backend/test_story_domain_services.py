from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest

from api.services.game_service import GameService
from story.exceptions import StorySessionNotFoundError, StorySessionRestoreFailedError
from story.story_asset_service import StoryAssetService
from story.story_ending_service import StoryEndingService
from story.story_session_service import StorySessionService
from story.story_turn_service import StoryTurnService


def _make_states(**overrides):
    payload = {
        "favorability": 10,
        "trust": 20,
        "hostility": 5,
        "dependence": 15,
        "emotion": 60,
        "stress": 10,
        "anxiety": 8,
        "happiness": 55,
        "sadness": 6,
        "confidence": 50,
        "initiative": 40,
        "caution": 45,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class _FakeSnapshotRecord:
    def __init__(
        self,
        *,
        thread_id="thread-001",
        round_no=0,
        status="in_progress",
        response_payload=None,
        updated_at=None,
        expires_at=None,
    ):
        self.thread_id = thread_id
        self.round_no = round_no
        self.status = status
        self.response_payload = dict(response_payload or {})
        self.updated_at = updated_at
        self.expires_at = expires_at

    def to_summary(self):
        return {
            "thread_id": self.thread_id,
            "status": self.status,
            "round_no": self.round_no,
            "scene": self.response_payload.get("scene"),
        }


class _FakeSessionRecord:
    def __init__(self, *, expired=False):
        now = datetime.utcnow()
        self.character_id = 7
        self.status = "expired" if expired else "in_progress"
        self.current_round_no = 2
        self.current_scene_id = "library"
        self.updated_at = now
        self.expires_at = now + timedelta(hours=1)

    def is_expired(self):
        return self.status == "expired"


class _FakeStoryEngine:
    def __init__(self):
        self.current_scene = None
        self.current_event = {"scene": "library", "title": "图书馆事件", "story_background": "背景"}
        self.dialogue_history = []
        self.current_event_count = 0
        self.previous_event_contexts = []

    def get_opening_event(self, *, character_id, scene_id, opening_event_id=None):
        return {
            "title": "初遇",
            "story_background": "开场背景",
            "scene": "library",
        }

    def get_next_dialogue_round(self, character_id):
        return {
            "character_dialogue": "你好",
            "player_options": [{"id": 1, "text": "继续"}],
        }

    def record_character_dialogue(self, dialogue):
        self.dialogue_history.append({"type": "character", "content": dialogue})

    def is_game_finished(self):
        return True

    def get_ending_event(self, character_id):
        return {
            "title": "结局",
            "story_background": "结局背景",
            "scene": "ending",
            "ending_type": "open_ending",
        }


class _FakeSession:
    def __init__(self):
        self.thread_id = "thread-001"
        self.user_id = "user-001"
        self.character_id = 7
        self.game_mode = "solo"
        self.is_initialized = False
        self.current_dialogue_round = None
        self.db_manager = SimpleNamespace(get_character_states=lambda character_id: _make_states())
        self.story_engine = _FakeStoryEngine()


class _PendingAssetService(StoryAssetService):
    def __init__(self):
        super().__init__()
        self.submitted = False

    def resolve_scene_image_url(self, scene_id):
        return None

    def find_latest_composite_image_url(self, *, character_id, scene_id):
        return None

    def submit_opening_asset_generation(self, **kwargs):
        self.submitted = True
        return True


class _ReadyEndingAssetService(StoryAssetService):
    def resolve_scene_image_url(self, scene_id):
        return "/static/images/scenes/ending.png"

    def find_latest_composite_image_url(self, *, character_id, scene_id):
        return "/static/images/composite/ending.png"


class _RecoveredSnapshotAssetService(StoryAssetService):
    def resolve_scene_image_url(self, scene_id):
        return "/static/images/scenes/library.png"

    def find_latest_composite_image_url(self, *, character_id, scene_id):
        return "/static/images/composite/library.png"


class _FakeSessionManagerForSnapshot:
    def __init__(self):
        self.story_store = SimpleNamespace(mark_story_session_expired=lambda thread_id: None)
        self.snapshot = _FakeSnapshotRecord(
            round_no=2,
            response_payload={
                "character_dialogue": "继续",
                "player_options": [{"id": 1, "text": "继续"}],
                "scene": "library",
            },
            updated_at=datetime(2026, 3, 19, 12, 0, 0),
            expires_at=datetime(2026, 3, 20, 12, 0, 0),
        )

    def get_session_record(self, thread_id):
        return _FakeSessionRecord()

    def get_latest_snapshot(self, thread_id):
        return self.snapshot


class _FakeSessionManagerWithoutSnapshot:
    def __init__(self):
        self.story_store = SimpleNamespace(mark_story_session_expired=lambda thread_id: None)
        self.record = _FakeSessionRecord()

    def get_session_record(self, thread_id):
        return self.record

    def get_latest_snapshot(self, thread_id):
        return None


class _FakeSessionManagerForTurn:
    def __init__(self):
        self.session = _FakeSession()
        self.saved = None

    def get_session(self, thread_id):
        return self.session

    def get_latest_snapshot(self, thread_id):
        return None

    def save_story_snapshot(self, *, session, round_no, response_payload, status):
        self.saved = {
            "session": session,
            "round_no": round_no,
            "response_payload": response_payload,
            "status": status,
        }
        return _FakeSnapshotRecord(
            thread_id=session.thread_id,
            round_no=round_no,
            status=status,
            response_payload=response_payload,
        )

    def evict_runtime_session(self, thread_id):
        raise AssertionError("should not evict runtime session on happy path")


class _RestoreSessionService:
    def __init__(self, next_thread_id="thread-restored"):
        self.next_thread_id = next_thread_id
        self.calls = []

    def init_game(self, *, user_id, character_id, game_mode):
        self.calls.append(
            {
                "user_id": user_id,
                "character_id": character_id,
                "game_mode": game_mode,
            }
        )
        return {"thread_id": self.next_thread_id}


class _SubmitTurnRestoreService(StoryTurnService):
    def __init__(self, *, story_session_service, restore_failure=None):
        super().__init__(
            session_manager=SimpleNamespace(),
            character_service=SimpleNamespace(db_manager=SimpleNamespace()),
            story_session_service=story_session_service,
            story_asset_service=StoryAssetService(),
            image_executor=None,
        )
        self.restore_failure = restore_failure
        self.lock_calls = []
        self.init_calls = []

    def _process_input_with_session_lock(self, *, thread_id: str, user_input: str, option_id: int | None):
        self.lock_calls.append(
            {
                "thread_id": thread_id,
                "user_input": user_input,
                "option_id": option_id,
            }
        )
        if thread_id == "thread-old":
            raise StorySessionNotFoundError(thread_id=thread_id)
        if self.restore_failure is not None:
            raise self.restore_failure
        return {
            "thread_id": thread_id,
            "character_dialogue": "恢复后继续",
            "player_options": [{"id": 1, "text": "继续"}],
            "round_no": 1,
        }

    def initialize_story(
        self,
        thread_id: str,
        character_id: int,
        scene_id: str = "school",
        character_image_url: str | None = None,
        opening_event_id: str | None = None,
    ):
        self.init_calls.append(
            {
                "thread_id": thread_id,
                "character_id": character_id,
                "scene_id": scene_id,
            }
        )
        if self.restore_failure is not None:
            raise self.restore_failure
        return {
            "thread_id": thread_id,
            "character_dialogue": "恢复初始化",
            "player_options": [{"id": 1, "text": "继续"}],
            "round_no": 0,
        }


class _FakeSessionManagerForEnding:
    def __init__(self):
        self.session = _FakeSession()
        self.saved = None

    def get_session(self, thread_id):
        self.session.is_initialized = True
        return self.session

    def get_session_record(self, thread_id):
        return SimpleNamespace(current_round_no=3)

    def save_story_snapshot(self, *, session, round_no, response_payload, status):
        self.saved = {
            "round_no": round_no,
            "response_payload": response_payload,
            "status": status,
        }
        return _FakeSnapshotRecord(
            thread_id=session.thread_id,
            round_no=round_no,
            status=status,
            response_payload=response_payload,
        )


class StoryDomainServicesTestCase(unittest.TestCase):
    def test_story_session_service_should_backfill_assets_on_snapshot_read(self):
        service = StorySessionService(
            session_manager=_FakeSessionManagerForSnapshot(),
            story_asset_service=StoryAssetService(),
        )

        result = service.get_session_snapshot("thread-001")

        self.assertEqual(result["thread_id"], "thread-001")
        self.assertEqual(result["round_no"], 2)
        self.assertEqual(result["assets"]["scene_image"]["status"], "failed")
        self.assertEqual(result["assets"]["composite_image"]["status"], "failed")
        self.assertEqual(result["updated_at"], "2026-03-19T12:00:00")

    def test_story_turn_service_should_mark_opening_assets_pending(self):
        session_manager = _FakeSessionManagerForTurn()
        asset_service = _PendingAssetService()
        service = StoryTurnService(
            session_manager=session_manager,
            character_service=SimpleNamespace(db_manager=SimpleNamespace()),
            story_asset_service=asset_service,
            image_executor=SimpleNamespace(),
        )

        result = service.initialize_story(
            "thread-001",
            7,
            scene_id="school",
            character_image_url="/tmp/portrait.png",
        )

        self.assertTrue(asset_service.submitted)
        self.assertEqual(result["assets"]["scene_image"]["status"], "pending")
        self.assertEqual(result["assets"]["composite_image"]["status"], "pending")
        self.assertEqual(session_manager.saved["status"], "in_progress")
        self.assertEqual(
            session_manager.saved["response_payload"]["assets"]["composite_image"]["detail"],
            "generation_pending",
        )

    def test_story_session_service_should_upgrade_pending_assets_to_ready_after_async_completion(self):
        session_manager = _FakeSessionManagerForSnapshot()
        session_manager.snapshot.response_payload.update(
            {
                "scene_image_url": None,
                "composite_image_url": None,
                "assets": {
                    "scene_image": {
                        "type": "scene_image",
                        "status": "pending",
                        "url": None,
                        "detail": "generation_pending",
                    },
                    "composite_image": {
                        "type": "composite_image",
                        "status": "pending",
                        "url": None,
                        "detail": "generation_pending",
                    },
                },
            }
        )
        service = StorySessionService(
            session_manager=session_manager,
            story_asset_service=_RecoveredSnapshotAssetService(),
        )

        result = service.get_session_snapshot("thread-001")

        self.assertEqual(result["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(result["assets"]["scene_image"]["url"], "/static/images/scenes/library.png")
        self.assertEqual(result["assets"]["composite_image"]["status"], "ready")
        self.assertEqual(result["assets"]["composite_image"]["url"], "/static/images/composite/library.png")

    def test_story_session_service_should_return_stable_contract_without_snapshot_record(self):
        service = StorySessionService(
            session_manager=_FakeSessionManagerWithoutSnapshot(),
            story_asset_service=_RecoveredSnapshotAssetService(),
        )

        result = service.get_session_snapshot("thread-001")

        self.assertEqual(result["thread_id"], "thread-001")
        self.assertEqual(result["status"], "in_progress")
        self.assertEqual(result["round_no"], 2)
        self.assertEqual(result["scene"], "library")
        self.assertEqual(result["updated_at"], result["snapshot"]["updated_at"])
        self.assertEqual(result["expires_at"], result["snapshot"]["expires_at"])
        self.assertEqual(result["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(result["assets"]["composite_image"]["status"], "ready")

    def test_story_turn_service_should_restore_free_text_submission_on_new_thread(self):
        restore_session_service = _RestoreSessionService(next_thread_id="thread-restored")
        service = _SubmitTurnRestoreService(story_session_service=restore_session_service)

        result = service.submit_turn(
            thread_id="thread-old",
            user_input="继续追问",
            option_id=None,
            user_id="user-001",
            character_id="7",
        )

        self.assertEqual(result["thread_id"], "thread-restored")
        self.assertTrue(result["session_restored"])
        self.assertEqual(result["restored_from_thread_id"], "thread-old")
        self.assertEqual(restore_session_service.calls[0]["character_id"], 7)
        self.assertEqual(service.init_calls[0]["thread_id"], "thread-restored")
        self.assertEqual(service.lock_calls[-1]["thread_id"], "thread-restored")

    def test_story_turn_service_should_require_reselect_after_option_restore(self):
        restore_session_service = _RestoreSessionService(next_thread_id="thread-restored")
        service = _SubmitTurnRestoreService(story_session_service=restore_session_service)

        result = service.submit_turn(
            thread_id="thread-old",
            user_input="",
            option_id=0,
            user_id="user-001",
            character_id="7",
        )

        self.assertEqual(result["thread_id"], "thread-restored")
        self.assertTrue(result["session_restored"])
        self.assertTrue(result["need_reselect_option"])
        self.assertEqual(result["restored_from_thread_id"], "thread-old")

    def test_story_turn_service_should_raise_restore_failed_when_rebuild_fails(self):
        restore_session_service = _RestoreSessionService(next_thread_id="thread-restored")
        service = _SubmitTurnRestoreService(
            story_session_service=restore_session_service,
            restore_failure=RuntimeError("restore boom"),
        )

        with self.assertRaises(StorySessionRestoreFailedError):
            service.submit_turn(
                thread_id="thread-old",
                user_input="继续追问",
                option_id=None,
                user_id="user-001",
                character_id="7",
            )

    def test_story_ending_service_should_persist_completed_payload_with_assets(self):
        session_manager = _FakeSessionManagerForEnding()
        service = StoryEndingService(
            session_manager=session_manager,
            story_asset_service=_ReadyEndingAssetService(),
        )

        result = service.trigger_ending("thread-001")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(result["assets"]["composite_image"]["status"], "ready")
        self.assertTrue(session_manager.saved["response_payload"]["is_game_finished"])

    def test_game_service_should_delegate_to_story_domain_services(self):
        session_service = SimpleNamespace(
            init_game=lambda **kwargs: {"delegated": "session.init", **kwargs},
            get_session_snapshot=lambda thread_id: {"delegated": "session.snapshot", "thread_id": thread_id},
        )
        turn_service = SimpleNamespace(
            initialize_story=lambda **kwargs: {"delegated": "turn.init", **kwargs},
            process_input=lambda **kwargs: {"delegated": "turn.input", **kwargs},
            submit_turn=lambda **kwargs: {"delegated": "turn.submit", **kwargs},
        )
        ending_service = SimpleNamespace(
            check_ending=lambda thread_id: {"delegated": "ending.check", "thread_id": thread_id},
            trigger_ending=lambda thread_id: {"delegated": "ending.trigger", "thread_id": thread_id},
        )
        history_service = SimpleNamespace(
            get_story_history=lambda thread_id: {"delegated": "history.read", "thread_id": thread_id},
        )

        service = GameService(
            story_asset_service=StoryAssetService(),
            story_session_service=session_service,
            story_turn_service=turn_service,
            story_ending_service=ending_service,
            story_history_service=history_service,
        )

        self.assertEqual(
            service.init_game(user_id="u-1", character_id=7, game_mode="solo")["delegated"],
            "session.init",
        )
        self.assertEqual(
            service.initialize_story("thread-001", 7)["delegated"],
            "turn.init",
        )
        self.assertEqual(
            service.process_input("thread-001", "继续")["delegated"],
            "turn.input",
        )
        self.assertEqual(
            service.submit_story_turn(
                thread_id="thread-001",
                user_input="继续",
                option_id=None,
                user_id="u-1",
                character_id="7",
            )["delegated"],
            "turn.submit",
        )
        self.assertEqual(
            service.get_story_session_snapshot("thread-001")["delegated"],
            "session.snapshot",
        )
        self.assertEqual(
            service.check_ending("thread-001")["delegated"],
            "ending.check",
        )
        self.assertEqual(
            service.trigger_ending("thread-001")["delegated"],
            "ending.trigger",
        )


if __name__ == "__main__":
    unittest.main()
