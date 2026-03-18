"""训练模块领域异常定义。"""

from __future__ import annotations


class TrainingDomainError(Exception):
    """训练领域异常基类。"""


class TrainingSessionNotFoundError(TrainingDomainError):
    """持久化阶段未找到训练会话。"""

    def __init__(self, session_id: str):
        super().__init__(f"session not found: {session_id}")
        self.session_id = session_id


class DuplicateRoundSubmissionError(TrainingDomainError):
    """同一会话同一回合重复提交（唯一约束冲突）。"""

    def __init__(self, session_id: str, round_no: int):
        super().__init__(f"duplicate round submission: session_id={session_id}, round_no={round_no}")
        self.session_id = session_id
        self.round_no = round_no
