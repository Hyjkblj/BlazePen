"""Unit tests for training media task executor."""

from __future__ import annotations

import builtins
from datetime import datetime, timedelta
import importlib
import time
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models.training  # noqa: F401
from models.character import Base
from training.exceptions import (
    TrainingMediaProviderUnavailableError,
    TrainingMediaTaskExecutionFailedError,
)
from training.media_task_executor import (
    TrainingMediaTaskExecutor,
    TrainingMediaTaskExecutorConfig,
    TrainingMediaTaskProviderDispatcher,
)
from training.training_repository import SqlAlchemyTrainingRepository
from training.training_store import DatabaseTrainingStore


class _ScriptedDispatcher:
    def __init__(self, scripted_results=None, default_result=None):
        self._scripted_results = list(scripted_results or [])
        self._default_result = dict(default_result or {"ok": True})
        self.calls = 0

    def execute_task(self, *, task_type, payload):
        self.calls += 1
        if self._scripted_results:
            current = self._scripted_results.pop(0)
            if isinstance(current, Exception):
                raise current
            return dict(current)
        return dict(self._default_result)


class _SlowDispatcher:
    def __init__(self, *, sleep_seconds: float):
        self.sleep_seconds = float(sleep_seconds)
        self.calls = 0

    def execute_task(self, *, task_type, payload):
        self.calls += 1
        time.sleep(self.sleep_seconds)
        return {"text": "finished-late"}


class _FakeImageService:
    def __init__(self):
        self.character_calls = 0
        self.scene_calls = 0
        self.last_character_prompt = None

    def generate_character_image(
        self,
        *,
        prompt,
        character_id=None,
        user_id=None,
        image_type="portrait",
        generate_group=True,
        group_count=3,
    ):
        self.character_calls += 1
        self.last_character_prompt = prompt
        return [f"/static/images/characters/test_{self.character_calls}.png"]

    def generate_scene_image(self, *, scene_data, scene_id=None, user_id=None):
        self.scene_calls += 1
        resolved_scene_id = str(scene_id or scene_data.get("scene_id") or "scene")
        return f"/static/images/scenes/{resolved_scene_id}_{self.scene_calls}.png"


class TrainingMediaTaskExecutorTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.repository = SqlAlchemyTrainingRepository(
            engine=self.engine,
            session_factory=self.SessionLocal,
        )
        self.store = DatabaseTrainingStore(self.repository)

        session = self.repository.create_training_session(
            user_id="executor-user",
            training_mode="guided",
            k_state={},
            s_state={},
            session_meta={},
        )
        self.session_id = session.session_id

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_executor_should_mark_task_succeeded_when_dispatch_returns_result(self):
        task = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="text",
            idempotency_key="executor-success-1",
            request_payload={"prompt": "hello"},
            max_retries=0,
        )
        dispatcher = _ScriptedDispatcher(default_result={"text": "done"})
        executor = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=dispatcher,
            config=TrainingMediaTaskExecutorConfig(
                max_workers=1,
                retry_backoff_seconds=0.01,
                task_timeout_seconds=10,
                recovery_timeout_seconds=5,
            ),
        )

        submitted = executor.submit_task(task.task_id)
        self.assertTrue(submitted)
        resolved = self._wait_until_terminal(task.task_id)

        self.assertEqual(resolved.status, "succeeded")
        self.assertEqual(resolved.result_payload, {"text": "done"})
        self.assertEqual(resolved.retry_count, 0)
        executor.shutdown()

    def test_executor_should_retry_then_succeed_and_persist_retry_count(self):
        task = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="text",
            idempotency_key="executor-retry-success-1",
            request_payload={"prompt": "hello"},
            max_retries=1,
        )
        dispatcher = _ScriptedDispatcher(
            scripted_results=[
                TrainingMediaTaskExecutionFailedError(task_type="text", reason="mock transient failure"),
                {"text": "recovered"},
            ]
        )
        executor = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=dispatcher,
            config=TrainingMediaTaskExecutorConfig(
                max_workers=1,
                retry_backoff_seconds=0.01,
                task_timeout_seconds=10,
                recovery_timeout_seconds=5,
            ),
        )

        executor.submit_task(task.task_id)
        resolved = self._wait_until_terminal(task.task_id)

        self.assertEqual(resolved.status, "succeeded")
        self.assertEqual(resolved.retry_count, 1)
        self.assertEqual(resolved.result_payload, {"text": "recovered"})
        self.assertEqual(dispatcher.calls, 2)
        executor.shutdown()

    def test_executor_should_mark_task_failed_after_retry_exhausted(self):
        task = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="tts",
            idempotency_key="executor-fail-1",
            request_payload={"text": "hello"},
            max_retries=1,
        )
        dispatcher = _ScriptedDispatcher(
            scripted_results=[
                TrainingMediaProviderUnavailableError(task_type="tts", provider="TTSService"),
                TrainingMediaProviderUnavailableError(task_type="tts", provider="TTSService"),
            ]
        )
        executor = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=dispatcher,
            config=TrainingMediaTaskExecutorConfig(
                max_workers=1,
                retry_backoff_seconds=0.01,
                task_timeout_seconds=10,
                recovery_timeout_seconds=5,
            ),
        )

        executor.submit_task(task.task_id)
        resolved = self._wait_until_terminal(task.task_id)

        self.assertEqual(resolved.status, "failed")
        self.assertEqual(resolved.retry_count, 1)
        self.assertEqual((resolved.error_payload or {}).get("error_class"), "TrainingMediaProviderUnavailableError")
        self.assertEqual(dispatcher.calls, 2)
        executor.shutdown()

    def test_recovery_should_timeout_stale_running_tasks(self):
        task = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="text",
            idempotency_key="executor-recovery-timeout-1",
            request_payload={"prompt": "hello"},
            max_retries=0,
        )
        claimed = self.store.claim_media_task(task.task_id)
        self.assertIsNotNone(claimed)
        self.store.update_media_task(
            task.task_id,
            {
                "started_at": datetime.utcnow() - timedelta(seconds=10),
            },
        )

        executor = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=_ScriptedDispatcher(default_result={"text": "unused"}),
            config=TrainingMediaTaskExecutorConfig(
                max_workers=1,
                retry_backoff_seconds=0.01,
                task_timeout_seconds=10,
                recovery_timeout_seconds=1,
            ),
        )

        recovery_result = executor.recover_pending_tasks()
        resolved = self.store.get_media_task(task.task_id)

        self.assertEqual(recovery_result["timed_out"], 1)
        self.assertEqual(recovery_result["recovered"], 0)
        self.assertEqual(resolved.status, "timeout")
        self.assertEqual((resolved.error_payload or {}).get("reason"), "recovery timeout exceeded")
        executor.shutdown()

    def test_executor_should_timeout_hung_provider_call_without_waiting_for_provider_return(self):
        task = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="text",
            idempotency_key="executor-timeout-fast-1",
            request_payload={"prompt": "hello"},
            max_retries=0,
        )
        dispatcher = _SlowDispatcher(sleep_seconds=0.6)
        executor = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=dispatcher,
            config=TrainingMediaTaskExecutorConfig(
                max_workers=1,
                retry_backoff_seconds=0.01,
                task_timeout_seconds=0.1,
                recovery_timeout_seconds=5,
            ),
        )

        started_at = time.monotonic()
        executor.submit_task(task.task_id)
        resolved = self._wait_until_terminal(task.task_id, timeout_seconds=1.0)
        elapsed = time.monotonic() - started_at

        self.assertEqual(resolved.status, "timeout")
        self.assertLess(elapsed, 0.4)
        self.assertEqual(dispatcher.calls, 1)
        executor.shutdown()

    def test_scene_series_should_not_be_auto_enabled_by_scenario_tag_fields(self):
        image_service = _FakeImageService()
        dispatcher = TrainingMediaTaskProviderDispatcher(image_service=image_service)

        result = dispatcher.execute_task(
            task_type="image",
            payload={
                "prompt": "draw newsroom scene",
                "image_type": "scene",
                "scenario_id": "S1",
                "major_scene_title": "Newsroom",
                "generate_storyline_series": False,
            },
        )

        self.assertIn("image_urls", result)
        self.assertNotIn("small_scene_urls", result)
        self.assertEqual(image_service.character_calls, 1)
        self.assertEqual(image_service.scene_calls, 0)

    def test_image_task_should_prefer_visual_prompt_when_both_prompts_exist(self):
        image_service = _FakeImageService()
        dispatcher = TrainingMediaTaskProviderDispatcher(image_service=image_service)

        result = dispatcher.execute_task(
            task_type="image",
            payload={
                "prompt": "legacy fallback prompt",
                "visual_prompt": "battlefield ruins, dim sky, distant firelight",
                "image_type": "scene",
            },
        )

        self.assertIn("image_urls", result)
        self.assertEqual(image_service.last_character_prompt, "battlefield ruins, dim sky, distant firelight")

    def test_image_task_should_fallback_to_default_scene_prompt_when_prompt_missing(self):
        image_service = _FakeImageService()
        dispatcher = TrainingMediaTaskProviderDispatcher(image_service=image_service)

        result = dispatcher.execute_task(
            task_type="image",
            payload={
                "image_type": "scene",
                "scenario_title": "前线街头采访",
                "brief": "局势紧张，街区内存在不明交火声。",
                "mission": "在保护线人的前提下完成事实核验。",
                "decision_focus": "核实目击者口径并控制传播风险",
            },
        )

        self.assertIn("image_urls", result)
        self.assertTrue(image_service.last_character_prompt)
        self.assertIn("前线街头采访", image_service.last_character_prompt)
        self.assertIn("任务：在保护线人的前提下完成事实核验。", image_service.last_character_prompt)

    def test_scene_series_should_require_explicit_flag_and_scene_image_type(self):
        image_service = _FakeImageService()
        dispatcher = TrainingMediaTaskProviderDispatcher(image_service=image_service)

        import os

        previous = os.environ.get("TRAINING_ENABLE_SCENE_SERIES")
        os.environ["TRAINING_ENABLE_SCENE_SERIES"] = "1"
        try:
            result = dispatcher.execute_task(
                task_type="image",
                payload={
                    "prompt": "draw newsroom scene",
                    "image_type": "scene",
                    "generate_storyline_series": True,
                    "session_id": "session-1",
                    "round_no": 1,
                    "scenario_id": "S1",
                    "major_scene_title": "Newsroom",
                    "micro_scene_prompts": [
                        "newsroom micro scene 1",
                        "newsroom micro scene 2",
                    ],
                },
            )
        finally:
            if previous is None:
                os.environ.pop("TRAINING_ENABLE_SCENE_SERIES", None)
            else:
                os.environ["TRAINING_ENABLE_SCENE_SERIES"] = previous

        self.assertIn("preview_url", result)
        self.assertIn("small_scene_urls", result)
        self.assertEqual(len(result.get("small_scene_urls", [])), 2)
        self.assertEqual(image_service.character_calls, 0)
        self.assertGreaterEqual(image_service.scene_calls, 3)

    def test_two_executors_should_not_duplicate_provider_execution_for_same_task(self):
        task = self.store.create_media_task(
            session_id=self.session_id,
            round_no=1,
            task_type="text",
            idempotency_key="executor-race-1",
            request_payload={"prompt": "hello"},
            max_retries=0,
        )
        dispatcher = _ScriptedDispatcher(default_result={"text": "done-once"})
        config = TrainingMediaTaskExecutorConfig(
            max_workers=1,
            retry_backoff_seconds=0.01,
            task_timeout_seconds=10,
            recovery_timeout_seconds=5,
        )
        executor_a = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=dispatcher,
            config=config,
        )
        executor_b = TrainingMediaTaskExecutor(
            training_store=self.store,
            provider_dispatcher=dispatcher,
            config=config,
        )

        executor_a.submit_task(task.task_id)
        executor_b.submit_task(task.task_id)
        resolved = self._wait_until_terminal(task.task_id)

        self.assertEqual(resolved.status, "succeeded")
        self.assertEqual(dispatcher.calls, 1)
        executor_a.shutdown()
        executor_b.shutdown()

    def test_executor_module_import_should_not_require_heavy_media_dependencies(self):
        blocked_modules = {
            "api.services.image_service",
            "api.services.tts_service",
            "models.text_model_service",
        }
        original_import = builtins.__import__

        def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name in blocked_modules:
                raise ImportError(f"blocked import: {name}")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=_guarded_import):
            module = importlib.import_module("training.media_task_executor")
            module = importlib.reload(module)
            dispatcher = module.TrainingMediaTaskProviderDispatcher()
            with self.assertRaises(module.TrainingMediaProviderUnavailableError):
                dispatcher.execute_task(task_type="image", payload={"prompt": "demo"})

    def _wait_until_terminal(self, task_id: str, timeout_seconds: float = 5.0):
        start = time.monotonic()
        while time.monotonic() - start < timeout_seconds:
            task = self.store.get_media_task(task_id)
            if task is not None and task.status in {"succeeded", "failed", "timeout"}:
                return task
            time.sleep(0.02)
        self.fail(f"task did not reach terminal status in {timeout_seconds}s: {task_id}")


if __name__ == "__main__":
    unittest.main()
