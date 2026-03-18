"""训练模块导出入口。"""

from training.constants import SKILL_CODES, S_STATE_CODES
from training.contracts import KtObservationPayload, RoundEvaluationPayload, ScenarioRecommendationLogPayload, TrainingAuditEventPayload
from training.ending_policy import EndingPolicy
from training.evaluator import TrainingRoundEvaluator
from training.exceptions import DuplicateRoundSubmissionError, TrainingSessionNotFoundError
from training.recommendation_policy import RecommendationPolicy
from training.reporting_policy import TrainingReportingPolicy
from training.scenario_policy import ScenarioPolicy
from training.scenario_repository import ScenarioRepository
from training.telemetry_policy import TrainingTelemetryPolicy

# 对外只暴露稳定接口，避免业务侧直接耦合内部实现细节。
__all__ = [
    "SKILL_CODES",
    "S_STATE_CODES",
    "TrainingRoundEvaluator",
    "RoundEvaluationPayload",
    "ScenarioRecommendationLogPayload",
    "TrainingAuditEventPayload",
    "KtObservationPayload",
    "ScenarioPolicy",
    "ScenarioRepository",
    "RecommendationPolicy",
    "TrainingReportingPolicy",
    "EndingPolicy",
    "TrainingTelemetryPolicy",
    "DuplicateRoundSubmissionError",
    "TrainingSessionNotFoundError",
]
