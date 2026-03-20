from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest

from story.exceptions import StorySessionAccessDeniedError
from story.story_ending_service import StoryEndingService
from story.story_history_service import StoryHistoryService
from story.story_session_query_policy import StorySessionQueryPolicy
from story.story_session_service import StorySessionService


class _SessionRecord:
    def __init__(
        self,
        *,
        thread_id: str,
        user_id: str = "user-001",
        character_id: int = 7,
        game_mode: str = "solo",
        status: str = "in_progress",
        current_round_no: int = 0,
        current_scene_id: str | None = None,
        is_initialized: bool = True,
        updated_at: datetime | None = None,
        expires_at: datetime | None = None,
    ):
        self.thread_id = thread_id
        self.user_id = user_id
        self.character_id = character_id
        self.game_mode = game_mode
        self.status = status
        self.current_round_no = current_round_no
        self.current_scene_id = current_scene_id
        self.is_initialized = is_initialized
        self.updated_at = updated_at or datetime(2026, 3, 20, 10, 0, 0)
        self.expires_at = expires_at

    def is_expired(self):
        return self.status == "expired" or (
            self.expires_at is not None and self.expires_at <= datetime.utcnow()
        )


class _SnapshotRecord:
    def __init__(
        self,
        *,
        thread_id: str,
        round_no: int,
        status: str,
        response_payload: dict | None = None,
        current_states: dict | None = None,
        updated_at: datetime | None = None,
        expires_at: datetime | None = None,
    ):
        self.thread_id = thread_id
        self.round_no = round_no
        self.status = status
        self.response_payload = dict(response_payload or {})
        self._current_states = dict(current_states or {})
        self.updated_at = updated_at or datetime(2026, 3, 20, 11, 0, 0)
        self.expires_at = expires_at

    def to_summary(self):
        return {
            "thread_id": self.thread_id,
            "status": self.status,
            "round_no": self.round_no,
            "scene": self.response_payload.get("scene"),
            "event_title": self.response_payload.get("event_title"),
            "current_states": dict(self._current_states),
            "is_game_finished": bool(self.response_payload.get("is_game_finished", False)),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class _RoundRecord:
    def __init__(
        self,
        *,
        round_no: int,
        input_kind: str,
        selected_option_index: int | None,
        request_payload: dict | None,
        response_payload: dict | None,
        state_before: dict | None,
        state_after: dict | None,
        status: str = "in_progress",
        created_at: datetime | None = None,
    ):
        self.round_no = round_no
        self.input_kind = input_kind
        self.selected_option_index = selected_option_index
        self.request_payload = dict(request_payload or {})
        self.response_payload = dict(response_payload or {})
        self.state_before = dict(state_before or {})
        self.state_after = dict(state_after or {})
        self.status = status
        self.created_at = created_at or datetime(2026, 3, 20, 11, round_no, 0)
        self.user_input_raw = str(self.request_payload.get("user_input") or "")


class _QuerySessionManager:
    def __init__(self, *, sessions=None, session_record=None, latest_snapshots=None, rounds=None):
        self._sessions = list(sessions or [])
        self._session_record = session_record
        self._latest_snapshots = dict(latest_snapshots or {})
        self._rounds = list(rounds or [])
        self.single_snapshot_calls = []
        self.batch_snapshot_calls = []

    def list_story_sessions(self, *, user_id: str, limit: int = 10):
        return list(self._sessions)[:limit]

    def get_session_record(self, thread_id: str):
        if self._session_record is not None and self._session_record.thread_id == thread_id:
            return self._session_record
        for item in self._sessions:
            if item.thread_id == thread_id:
                return item
        return None

    def get_latest_snapshot(self, thread_id: str):
        self.single_snapshot_calls.append(thread_id)
        return self._latest_snapshots.get(thread_id)

    def get_latest_snapshots(self, thread_ids: list[str]):
        self.batch_snapshot_calls.append(list(thread_ids))
        return {
            thread_id: self._latest_snapshots[thread_id]
            for thread_id in thread_ids
            if thread_id in self._latest_snapshots
        }

    def get_story_rounds(self, thread_id: str):
        return list(self._rounds)

    def get_session(self, thread_id: str):
        raise AssertionError("query service should not touch runtime session")


class StoryQueryServicesTestCase(unittest.TestCase):
    def test_story_session_service_should_use_strict_actor_policy_by_default(self):
        active_record = _SessionRecord(
            thread_id="thread-active",
            current_round_no=1,
            current_scene_id="library",
            status="in_progress",
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        session_manager = _QuerySessionManager(
            sessions=[active_record],
            latest_snapshots={},
        )
        service = StorySessionService(
            session_manager=session_manager,
        )

        with self.assertRaises(StorySessionAccessDeniedError) as context:
            service.list_recent_sessions(
                user_id="user-001",
                limit=10,
            )

        self.assertEqual(service.session_query_policy.mode, StorySessionQueryPolicy.MODE_ACTOR_HEADER_MATCH)
        self.assertEqual(context.exception.policy_mode, StorySessionQueryPolicy.MODE_ACTOR_HEADER_MATCH)
        self.assertEqual(session_manager.batch_snapshot_calls, [])

    def test_story_session_service_should_list_recent_sessions_from_persisted_facts(self):
        active_record = _SessionRecord(
            thread_id="thread-active",
            current_round_no=3,
            current_scene_id="library",
            status="in_progress",
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        expired_record = _SessionRecord(
            thread_id="thread-expired",
            current_round_no=1,
            current_scene_id="school",
            status="in_progress",
            expires_at=datetime.utcnow() - timedelta(minutes=5),
        )
        session_manager = _QuerySessionManager(
            sessions=[active_record, expired_record],
            latest_snapshots={
                "thread-active": _SnapshotRecord(
                    thread_id="thread-active",
                    round_no=3,
                    status="in_progress",
                    response_payload={
                        "scene": "library",
                        "event_title": "Library Scene",
                        "is_game_finished": False,
                    },
                    current_states={"trust": 55},
                ),
                "thread-expired": _SnapshotRecord(
                    thread_id="thread-expired",
                    round_no=1,
                    status="in_progress",
                    response_payload={
                        "scene": "school",
                        "event_title": "Opening",
                        "is_game_finished": False,
                    },
                    current_states={"trust": 10},
                ),
            },
        )
        service = StorySessionService(
            session_manager=session_manager,
            session_query_policy=StorySessionQueryPolicy(
                mode=StorySessionQueryPolicy.MODE_TRUSTED_QUERY_USER_ID
            ),
        )

        result = service.list_recent_sessions(user_id="user-001", limit=10)

        self.assertEqual(result["user_id"], "user-001")
        self.assertEqual(result["sessions"][0]["thread_id"], "thread-active")
        self.assertTrue(result["sessions"][0]["can_resume"])
        self.assertEqual(result["sessions"][0]["event_title"], "Library Scene")
        self.assertEqual(result["sessions"][1]["status"], "expired")
        self.assertFalse(result["sessions"][1]["can_resume"])
        self.assertEqual(session_manager.single_snapshot_calls, [])
        self.assertEqual(
            session_manager.batch_snapshot_calls,
            [["thread-active", "thread-expired"]],
        )

    def test_story_session_service_should_require_matching_actor_when_policy_is_strict(self):
        active_record = _SessionRecord(
            thread_id="thread-active",
            current_round_no=1,
            current_scene_id="library",
            status="in_progress",
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        session_manager = _QuerySessionManager(
            sessions=[active_record],
            latest_snapshots={},
        )
        service = StorySessionService(
            session_manager=session_manager,
            session_query_policy=StorySessionQueryPolicy(
                mode=StorySessionQueryPolicy.MODE_ACTOR_HEADER_MATCH
            ),
        )

        result = service.list_recent_sessions(
            user_id="user-001",
            actor_user_id="user-001",
            limit=10,
        )

        self.assertEqual(result["user_id"], "user-001")
        self.assertEqual(session_manager.batch_snapshot_calls, [["thread-active"]])

    def test_story_session_service_should_reject_recent_sessions_when_actor_mismatches(self):
        active_record = _SessionRecord(
            thread_id="thread-active",
            current_round_no=1,
            current_scene_id="library",
            status="in_progress",
            expires_at=datetime.utcnow() + timedelta(hours=2),
        )
        session_manager = _QuerySessionManager(
            sessions=[active_record],
            latest_snapshots={},
        )
        service = StorySessionService(
            session_manager=session_manager,
            session_query_policy=StorySessionQueryPolicy(
                mode=StorySessionQueryPolicy.MODE_ACTOR_HEADER_MATCH
            ),
        )

        with self.assertRaises(StorySessionAccessDeniedError) as context:
            service.list_recent_sessions(
                user_id="user-001",
                actor_user_id="user-002",
                limit=10,
            )

        self.assertEqual(context.exception.policy_mode, "actor_header_match")
        self.assertEqual(session_manager.batch_snapshot_calls, [])

    def test_story_history_service_should_build_history_without_runtime_restore(self):
        session_record = _SessionRecord(
            thread_id="thread-history",
            current_round_no=2,
            current_scene_id="library",
            status="completed",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        rounds = [
            _RoundRecord(
                round_no=1,
                input_kind="option",
                selected_option_index=0,
                request_payload={
                    "user_input": "",
                    "option_id": 0,
                    "selected_option": {
                        "id": 10,
                        "text": "Ask about the clue",
                        "type": "curious",
                    },
                },
                response_payload={
                    "scene": "library",
                    "event_title": "Clue Found",
                    "character_dialogue": "The clue is hidden in the archive.",
                    "current_states": {"trust": 60},
                    "is_event_finished": True,
                    "is_game_finished": False,
                },
                state_before={"trust": 50},
                state_after={"trust": 60},
            ),
            _RoundRecord(
                round_no=2,
                input_kind="option",
                selected_option_index=1,
                request_payload={"user_input": "", "option_id": 1},
                response_payload={
                    "scene": "rooftop",
                    "event_title": "Final Choice",
                    "character_dialogue": "You chose to stay.",
                    "current_states": {"trust": 62, "hostility": 5},
                    "is_event_finished": False,
                    "is_game_finished": True,
                },
                state_before={"trust": 60, "hostility": 5},
                state_after={"trust": 62, "hostility": 5},
                status="completed",
            ),
        ]
        session_manager = _QuerySessionManager(
            session_record=session_record,
            rounds=rounds,
            latest_snapshots={
                "thread-history": _SnapshotRecord(
                    thread_id="thread-history",
                    round_no=2,
                    status="completed",
                    response_payload={"scene": "rooftop", "event_title": "Final Choice"},
                    current_states={"trust": 62, "hostility": 5},
                )
            },
        )
        service = StoryHistoryService(session_manager=session_manager)

        result = service.get_story_history("thread-history")

        self.assertEqual(result["status"], "expired")
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["history"][0]["user_action"]["summary"], "Ask about the clue")
        self.assertEqual(result["history"][0]["state_summary"]["changes"]["trust"], 10.0)
        self.assertEqual(result["history"][1]["user_action"]["summary"], "\u9009\u9879 2")
        self.assertTrue(result["history"][1]["is_game_finished"])

    def test_story_ending_service_should_build_summary_from_persisted_snapshot(self):
        session_record = _SessionRecord(
            thread_id="thread-ending",
            current_round_no=4,
            current_scene_id="ending",
            status="completed",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        session_manager = _QuerySessionManager(
            session_record=session_record,
            latest_snapshots={
                "thread-ending": _SnapshotRecord(
                    thread_id="thread-ending",
                    round_no=4,
                    status="completed",
                    response_payload={
                        "scene": "ending",
                        "event_title": "Ending",
                        "is_game_finished": True,
                    },
                    current_states={
                        "favorability": 70,
                        "trust": 65,
                        "hostility": 10,
                        "dependence": 20,
                    },
                )
            },
        )
        service = StoryEndingService(session_manager=session_manager)

        result = service.get_ending_summary("thread-ending")

        self.assertTrue(result["has_ending"])
        self.assertEqual(result["ending"]["type"], "good_ending")
        self.assertEqual(result["ending"]["scene"], "ending")
        self.assertEqual(result["ending"]["key_states"]["trust"], 65.0)
        self.assertTrue(result["updated_at"].startswith("2026-03-20T11:00:00"))

    def test_story_ending_service_should_check_ending_from_persisted_facts(self):
        session_record = _SessionRecord(
            thread_id="thread-ending-check",
            current_round_no=4,
            current_scene_id="ending",
            status="completed",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        session_manager = _QuerySessionManager(
            session_record=session_record,
            latest_snapshots={
                "thread-ending-check": _SnapshotRecord(
                    thread_id="thread-ending-check",
                    round_no=4,
                    status="completed",
                    response_payload={
                        "scene": "ending",
                        "event_title": "Ending",
                        "is_game_finished": True,
                    },
                    current_states={
                        "favorability": 70,
                        "trust": 65,
                        "hostility": 10,
                        "dependence": 20,
                    },
                )
            },
        )
        service = StoryEndingService(session_manager=session_manager)

        result = service.check_ending("thread-ending-check")

        self.assertTrue(result["has_ending"])
        self.assertEqual(result["ending"]["type"], "good_ending")
        self.assertEqual(result["ending"]["trust"], 65.0)


if __name__ == "__main__":
    unittest.main()
