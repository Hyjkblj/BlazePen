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


class TrainingStorageUnavailableError(TrainingDomainError):
    """Training persistence infrastructure is unavailable for the requested operation."""

    def __init__(self, *, message: str, details: dict | None = None):
        normalized_message = str(message or "").strip() or "training storage unavailable"
        super().__init__(normalized_message)
        self.details = dict(details or {})


class TrainingModeUnsupportedError(TrainingDomainError, ValueError):
    """Client requested an unsupported training mode."""

    def __init__(self, *, raw_mode: str, supported_modes: list[str] | tuple[str, ...]):
        normalized_supported_modes = [str(item).strip() for item in supported_modes if str(item).strip()]
        supported_text = "/".join(normalized_supported_modes) if normalized_supported_modes else "guided/self-paced/adaptive"
        raw_text = str(raw_mode or "").strip()
        display_mode = raw_text or "<empty>"
        super().__init__(f"unsupported training mode: {display_mode}; expected one of {supported_text}")
        self.raw_mode = raw_text
        self.supported_modes = normalized_supported_modes


class TrainingScenarioMismatchError(TrainingDomainError, ValueError):
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


class TrainingMediaTaskNotFoundError(TrainingDomainError):
    """Training media task not found by task_id."""

    def __init__(self, task_id: str):
        super().__init__(f"training media task not found: {task_id}")
        self.task_id = str(task_id or "").strip()


class TrainingMediaTaskInvalidError(TrainingDomainError):
    """Training media task request violates contract validation rules."""

    def __init__(self, message: str, *, details: dict | None = None):
        normalized_message = str(message or "").strip() or "invalid training media task request"
        super().__init__(normalized_message)
        self.details = dict(details or {})


class TrainingMediaTaskUnsupportedError(TrainingDomainError):
    """Training media task type is unsupported by the policy contract."""

    def __init__(
        self,
        *,
        task_type: str,
        supported_task_types: list[str] | tuple[str, ...] | None = None,
    ):
        normalized_task_type = str(task_type or "").strip().lower()
        normalized_supported = [
            str(item).strip().lower()
            for item in (supported_task_types or [])
            if str(item).strip()
        ]
        supported_text = ",".join(normalized_supported) if normalized_supported else "image,tts,text"
        display_task_type = normalized_task_type or "<empty>"
        super().__init__(
            f"unsupported training media task type: {display_task_type}; expected one of {supported_text}"
        )
        self.task_type = normalized_task_type
        self.supported_task_types = normalized_supported


class TrainingMediaTaskConflictError(TrainingDomainError):
    """Training media idempotency key conflicts with a different request scope."""

    def __init__(self, message: str, *, details: dict | None = None):
        normalized_message = str(message or "").strip() or "training media task conflict"
        super().__init__(normalized_message)
        self.details = dict(details or {})


class TrainingMediaProviderUnavailableError(TrainingDomainError):
    """Underlying media provider is unavailable for requested task type."""

    def __init__(self, *, task_type: str, provider: str | None = None):
        normalized_task_type = str(task_type or "").strip().lower()
        normalized_provider = str(provider or "").strip() or "unknown"
        super().__init__(
            f"training media provider unavailable: task_type={normalized_task_type}, provider={normalized_provider}"
        )
        self.task_type = normalized_task_type
        self.provider = normalized_provider


class TrainingMediaTaskExecutionFailedError(TrainingDomainError):
    """Media task provider call failed for a non-timeout reason."""

    def __init__(self, *, task_type: str, reason: str):
        normalized_task_type = str(task_type or "").strip().lower()
        normalized_reason = str(reason or "").strip() or "unknown execution failure"
        super().__init__(
            f"training media task execution failed: task_type={normalized_task_type}, reason={normalized_reason}"
        )
        self.task_type = normalized_task_type
        self.reason = normalized_reason


class TrainingMediaTaskTimeoutError(TrainingDomainError):
    """Media task execution exceeded configured timeout budget."""

    def __init__(self, *, task_type: str, timeout_seconds: float):
        normalized_task_type = str(task_type or "").strip().lower()
        normalized_timeout = max(float(timeout_seconds or 0.0), 0.0)
        super().__init__(
            f"training media task timeout: task_type={normalized_task_type}, timeout_seconds={normalized_timeout}"
        )
        self.task_type = normalized_task_type
        self.timeout_seconds = normalized_timeout
