"""训练模块导出入口。"""

from training.constants import SKILL_CODES, S_STATE_CODES
from training.contracts import KtObservationPayload, RoundEvaluationPayload, ScenarioRecommendationLogPayload, TrainingAuditEventPayload
from training.decision_context_policy import TrainingDecisionContextPolicy
from training.ending_policy import EndingPolicy
from training.evaluator import TrainingRoundEvaluator
from training.exceptions import DuplicateRoundSubmissionError, TrainingSessionNotFoundError
from training.output_assembler_policy import TrainingOutputAssemblerPolicy
from training.report_context_policy import TrainingReportContextPolicy
from training.recommendation_policy import RecommendationPolicy
from training.reporting_policy import TrainingReportingPolicy
from training.round_transition_policy import TrainingRoundTransitionPolicy
from training.runtime_artifact_policy import TrainingRuntimeArtifactPolicy
from training.scenario_policy import ScenarioPolicy
from training.scenario_repository import ScenarioRepository
from training.session_snapshot_policy import SessionScenarioSnapshotPolicy
from training.telemetry_policy import TrainingTelemetryPolicy

# 对外暴露稳定的领域契约与可注入策略，避免调用方因为内部重构出现不对称导出。
__all__ = [
    "SKILL_CODES",
    "S_STATE_CODES",
    "TrainingRoundEvaluator",
    "RoundEvaluationPayload",
    "ScenarioRecommendationLogPayload",
    "TrainingAuditEventPayload",
    "KtObservationPayload",
    "TrainingDecisionContextPolicy",
    "TrainingReportContextPolicy",
    "TrainingRoundTransitionPolicy",
    "SessionScenarioSnapshotPolicy",
    "ScenarioPolicy",
    "ScenarioRepository",
    "RecommendationPolicy",
    "TrainingReportingPolicy",
    "TrainingRuntimeArtifactPolicy",
    "TrainingOutputAssemblerPolicy",
    "EndingPolicy",
    "TrainingTelemetryPolicy",
    "DuplicateRoundSubmissionError",
    "TrainingSessionNotFoundError",
]
