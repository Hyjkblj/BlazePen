"""Background executor for training story script generation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from training.story_script_agent import StoryScriptAgent
from utils.logger import get_logger


logger = get_logger(__name__)


class TrainingStoryScriptExecutor:
    def __init__(self, *, training_store: Any, training_service: Any, max_workers: int = 2):
        self.training_store = training_store
        self.training_service = training_service
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="training_story_script")

    def submit_session(self, session_id: str) -> bool:
        normalized = str(session_id or "").strip()
        if not normalized:
            return False

        # Store-level claim first: prevents duplicate work across processes/instances.
        claimed = False
        try:
            claimed = bool(self.training_store.claim_story_script_job(normalized, lease_seconds=300))
        except Exception as exc:
            logger.warning("failed to claim story script job: session_id=%s error=%s", normalized, str(exc))
            return False
        if not claimed:
            return False

        self._pool.submit(self._run_session, normalized)
        return True

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _run_session(self, session_id: str) -> None:
        self._generate(session_id)

    def _generate(self, session_id: str) -> None:
        session = self.training_store.get_training_session(session_id)
        if session is None:
            return

        existing = self.training_store.get_story_script_by_session_id(session_id)
        if existing is not None:
            status = str(getattr(existing, "status", "") or "").strip().lower()
            payload = dict(getattr(existing, "payload", None) or {})
            if payload:
                return
            if status not in {"pending", "running"}:
                # Do not generate unless explicitly marked pending/running.
                return

        # Build sources from persisted snapshots.
        snapshot_bundle = self.training_service.session_snapshot_policy.require_session_snapshots(
            session_id=session_id,
            session=session,
        )
        major_scene_sources = [
            dict(item)
            for item in (snapshot_bundle.scenario_payload_sequence or [])[:6]
            if isinstance(item, dict)
        ]
        player_profile = self.training_service.scenario_policy.resolve_session_player_profile(session)

        agent = StoryScriptAgent(training_store=self.training_store)
        try:
            payload = agent.ensure_script_for_session(
                session_id=session_id,
                major_scene_sources=major_scene_sources,
                player_profile=player_profile,
                allow_llm=True,
            )
            self.training_store.update_story_script_by_session_id(
                session_id,
                {
                    "status": "ready",
                    "error_code": None,
                    "error_message": None,
                    "fallback_used": bool(payload.get("fallback_used", False)),
                },
            )
        except Exception as exc:
            logger.warning("story script background generation failed: session_id=%s error=%s", session_id, str(exc))
            self.training_store.update_story_script_by_session_id(
                session_id,
                {
                    "status": "failed",
                    "error_code": "BACKGROUND_FAILED",
                    "error_message": str(exc),
                },
            )

