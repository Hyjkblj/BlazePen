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


class TrainingModeUnsupportedError(TrainingDomainError):
    """Client requested an unsupported training mode."""

    def __init__(self, *, raw_mode: str, supported_modes: list[str] | tuple[str, ...]):
        normalized_supported_modes = [str(item).strip() for item in supported_modes if str(item).strip()]
        supported_text = "/".join(normalized_supported_modes) if normalized_supported_modes else "guided/self-paced/adaptive"
        raw_text = str(raw_mode or "").strip()
        display_mode = raw_text or "<empty>"
        super().__init__(f"unsupported training mode: {display_mode}; expected one of {supported_text}")
        self.raw_mode = raw_text
        self.supported_modes = normalized_supported_modes


class TrainingScenarioMismatchError(TrainingDomainError):
    """Submitted scenario does not match the current persisted session facts."""

    def __init__(
        self,
        *,
        submitted_scenario_id: str,
        round_no: int,
        expected_scenario_id: str | None = None,
        allowed_scenario_ids: list[str] | tuple[str, ...] | None = None,
    ):
        submitted_text = str(submitted_scenario_id or "").strip()
        expected_text = str(expected_scenario_id or "").strip()
        normalized_allowed_ids = [
            str(item).strip() for item in (allowed_scenario_ids or []) if str(item).strip()
        ]
        if expected_text:
            message = (
                f"scenario mismatch: expected={expected_text}, "
                f"submitted={submitted_text}, round={int(round_no)}"
            )
        elif normalized_allowed_ids:
            message = (
                f"scenario mismatch: allowed={','.join(normalized_allowed_ids)}, "
                f"submitted={submitted_text}, round={int(round_no)}"
            )
        else:
            message = f"scenario mismatch: submitted={submitted_text}, round={int(round_no)}"
        super().__init__(message)
        self.submitted_scenario_id = submitted_text
        self.expected_scenario_id = expected_text or None
        self.allowed_scenario_ids = normalized_allowed_ids
        self.round_no = int(round_no)


class DuplicateRoundSubmissionError(TrainingDomainError):
    """同一会话同一回合重复提交（唯一约束冲突）。"""

    def __init__(self, session_id: str, round_no: int):
        super().__init__(f"duplicate round submission: session_id={session_id}, round_no={round_no}")
        self.session_id = session_id
        self.round_no = round_no
