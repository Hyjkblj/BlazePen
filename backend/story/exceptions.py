"""Story-domain exceptions."""

from __future__ import annotations


class StoryDomainError(Exception):
    """Base class for story-domain exceptions."""


class StorySessionNotFoundError(StoryDomainError):
    """Persistent story session missing."""

    def __init__(self, thread_id: str):
        super().__init__(f"story session not found: {thread_id}")
        self.thread_id = thread_id


class StorySessionExpiredError(StoryDomainError):
    """Story session exceeded its TTL."""

    def __init__(self, thread_id: str):
        super().__init__(f"story session expired: {thread_id}")
        self.thread_id = thread_id


class StorySessionAccessDeniedError(StoryDomainError):
    """Story session read request rejected by access policy."""

    def __init__(
        self,
        *,
        requested_user_id: str,
        actor_user_id: str | None,
        policy_mode: str,
    ):
        actor_label = actor_user_id or "missing"
        super().__init__(
            "story session access denied: "
            f"requested_user_id={requested_user_id}, actor_user_id={actor_label}, policy_mode={policy_mode}"
        )
        self.requested_user_id = requested_user_id
        self.actor_user_id = actor_user_id
        self.policy_mode = policy_mode


class DuplicateStoryRoundSubmissionError(StoryDomainError):
    """Duplicate round submission identified by `(thread_id, round_no)`."""

    def __init__(self, thread_id: str, round_no: int):
        super().__init__(f"duplicate story round submission: thread_id={thread_id}, round_no={round_no}")
        self.thread_id = thread_id
        self.round_no = round_no


class StorySessionRestoreFailedError(StoryDomainError):
    """Story session could not be rebuilt from restore metadata."""

    def __init__(self, thread_id: str, character_id: int | None = None):
        details = f"story session restore failed: {thread_id}"
        if character_id is not None:
            details = f"{details} character_id={character_id}"
        super().__init__(details)
        self.thread_id = thread_id
        self.character_id = character_id
