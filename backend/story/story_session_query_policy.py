"""Story-session query access policy."""

from __future__ import annotations

import os

from story.exceptions import StorySessionAccessDeniedError
from utils.logger import get_logger

logger = get_logger(__name__)


class StorySessionQueryPolicy:
    """Authorize story-session read queries before they hit persistence."""

    MODE_TRUSTED_QUERY_USER_ID = "trusted_query_user_id"
    MODE_ACTOR_HEADER_MATCH = "actor_header_match"
    DEFAULT_MODE = MODE_ACTOR_HEADER_MATCH
    ENV_NAME = "STORY_SESSION_QUERY_POLICY_MODE"
    VALID_MODES = frozenset(
        {
            MODE_TRUSTED_QUERY_USER_ID,
            MODE_ACTOR_HEADER_MATCH,
        }
    )

    def __init__(self, *, mode: str = DEFAULT_MODE):
        normalized_mode = str(mode or self.DEFAULT_MODE).strip() or self.DEFAULT_MODE
        if normalized_mode not in self.VALID_MODES:
            supported_modes = ", ".join(sorted(self.VALID_MODES))
            raise ValueError(
                f"unsupported story session query policy mode: {normalized_mode}. "
                f"supported modes: {supported_modes}"
            )
        self.mode = normalized_mode

    @classmethod
    def from_environment(cls) -> "StorySessionQueryPolicy":
        """Build the deployment policy from environment configuration."""

        return cls(mode=os.getenv(cls.ENV_NAME, cls.DEFAULT_MODE))

    def authorize_recent_sessions_query(
        self,
        *,
        requested_user_id: str,
        actor_user_id: str | None = None,
    ) -> str:
        """Authorize a recent-sessions query and return the normalized owner id."""

        normalized_requested_user_id = self._normalize_required_user_id(
            requested_user_id,
            field_name="requested_user_id",
        )
        normalized_actor_user_id = self._normalize_optional_user_id(actor_user_id)

        if self.mode == self.MODE_TRUSTED_QUERY_USER_ID:
            return normalized_requested_user_id

        if normalized_actor_user_id != normalized_requested_user_id:
            logger.warning(
                "story session query denied: requested_user_id=%s actor_user_id=%s policy_mode=%s",
                normalized_requested_user_id,
                normalized_actor_user_id,
                self.mode,
            )
            raise StorySessionAccessDeniedError(
                requested_user_id=normalized_requested_user_id,
                actor_user_id=normalized_actor_user_id,
                policy_mode=self.mode,
            )

        return normalized_requested_user_id

    @staticmethod
    def _normalize_required_user_id(user_id: str, *, field_name: str) -> str:
        normalized_user_id = str(user_id or "").strip()
        if not normalized_user_id:
            raise ValueError(f"{field_name} is required")
        return normalized_user_id

    @staticmethod
    def _normalize_optional_user_id(user_id: str | None) -> str | None:
        normalized_user_id = str(user_id or "").strip()
        return normalized_user_id or None
