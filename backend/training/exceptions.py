"""训练模块领域异常定义。"""

from __future__ import annotations


class TrainingDomainError(Exception):
    """训练领域异常基类。"""


class TrainingSessionNotFoundError(TrainingDomainError):
    """持久化阶段未找到训练会话。"""

    def __init__(self, session_id: str):
        super().__init__(f"session not found: {session_id}")
        self.session_id = session_id


class TrainingSessionCompletedError(TrainingDomainError):
    """Training session is already completed and cannot accept more writes."""

    def __init__(self, session_id: str):
        super().__init__(f"training session already completed: {session_id}")
        self.session_id = session_id


class TrainingSessionRecoveryStateError(TrainingDomainError):
    """Persisted facts are insufficient to recover a stable training session."""

    def __init__(
        self,
        *,
        session_id: str,
        reason: str,
        details: dict | None = None,
    ):
        super().__init__(
            "training session recovery state corrupted: "
            f"session_id={session_id}, reason={reason}"
        )
        self.session_id = session_id
        self.reason = str(reason or "").strip() or "unknown"
        self.details = dict(details or {})


class DuplicateRoundSubmissionError(TrainingDomainError):
    """同一会话同一回合重复提交（唯一约束冲突）。"""

    def __init__(self, session_id: str, round_no: int):
        super().__init__(f"duplicate round submission: session_id={session_id}, round_no={round_no}")
        self.session_id = session_id
        self.round_no = round_no
