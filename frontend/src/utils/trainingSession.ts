import type {
  TrainingAuditEventApiResponse,
  TrainingBranchTransitionApiResponse,
  TrainingBranchTransitionSummaryApiResponse,
  TrainingConsequenceEventApiResponse,
  TrainingDecisionCandidateApiResponse,
  TrainingDiagnosticsCountItemApiResponse,
  TrainingDiagnosticsResponse,
  TrainingDiagnosticsSummaryApiResponse,
  TrainingEvaluationApiResponse,
  TrainingInitResponse,
  TrainingKtObservationApiResponse,
  TrainingMediaTaskApiResponse,
  TrainingMediaTaskListResponse,
  TrainingMetricObservationApiResponse,
  TrainingPlayerProfileApi,
  TrainingProgressResponse,
  TrainingRecommendationLogApiResponse,
  TrainingReportCurvePointApiResponse,
  TrainingReportHistoryItemApiResponse,
  TrainingReportMetricApiResponse,
  TrainingReportResponse,
  TrainingReportSummaryApiResponse,
  TrainingRoundDecisionContextApiResponse,
  TrainingRoundSubmitMediaTaskSummaryApiResponse,
  TrainingRoundSubmitResponse,
  TrainingRuntimeFlagsApiResponse,
  TrainingRuntimeStateApiResponse,
  TrainingRuntimeStateBarApiResponse,
  TrainingScenarioApiResponse,
  TrainingScenarioNextResponse,
  TrainingScenarioOptionApiResponse,
  TrainingScenarioRecommendationApiResponse,
  TrainingSessionProgressAnchorResponse,
  TrainingSessionSummaryResponse,
} from '@/types/api';
import type {
  TrainingAuditEvent,
  TrainingBranchTransition,
  TrainingBranchTransitionSummary,
  TrainingConsequenceEvent,
  TrainingDiagnosticsCountItem,
  TrainingDiagnosticsResult,
  TrainingDiagnosticsSummary,
  TrainingDecisionCandidate,
  TrainingEvaluation,
  TrainingInitResult,
  TrainingKtObservation,
  TrainingMediaTaskListResult,
  TrainingMediaTaskResult,
  TrainingMediaTaskView,
  TrainingMetricObservation,
  TrainingMode,
  TrainingPlayerProfile,
  TrainingProgressResult,
  TrainingRecommendationLog,
  TrainingReportCurvePoint,
  TrainingReportHistoryItem,
  TrainingReportMetric,
  TrainingReportResult,
  TrainingReportRoundSnapshot,
  TrainingReportSummary,
  TrainingRoundDecisionContext,
  TrainingRoundSubmitMediaTaskSummary,
  TrainingRoundSubmitResult,
  TrainingRuntimeFlags,
  TrainingRuntimeState,
  TrainingRuntimeStateBar,
  TrainingScenario,
  TrainingScenarioNextResult,
  TrainingScenarioOption,
  TrainingScenarioRecommendation,
  TrainingProgressAnchor,
  TrainingSessionSummaryResult,
} from '@/types/training';
import { ServiceError } from '@/services/serviceError';

const asRecord = (value: unknown): Record<string, unknown> | null =>
  typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;

const normalizeOptionalString = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  if (normalized === '' || normalized === 'null' || normalized === 'undefined') {
    return null;
  }

  return normalized;
};

const normalizeOptionalCharacterId = (value: unknown): string | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const normalized = Math.trunc(value);
    return normalized > 0 ? String(normalized) : null;
  }

  const normalized = normalizeOptionalString(value);
  if (!normalized) {
    return null;
  }

  const parsed = Number.parseInt(normalized, 10);
  if (Number.isInteger(parsed) && parsed > 0) {
    return String(parsed);
  }

  return null;
};

const normalizeNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value.trim());
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
};

const normalizeOptionalNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const normalized = normalizeNumber(value, Number.NaN);
  return Number.isFinite(normalized) ? normalized : null;
};

const normalizeStringArray = (value: unknown): string[] =>
  Array.isArray(value)
    ? value
        .map((item) => normalizeOptionalString(item))
        .filter((item): item is string => item !== null)
    : [];

const normalizeTrainingScenarioSequenceOutlines = (
  value: unknown
): Array<{ id: string; title: string }> => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      const rec = asRecord(item);
      if (!rec) {
        return null;
      }
      const id = normalizeOptionalString(rec.id);
      if (!id) {
        return null;
      }
      const title = normalizeOptionalString(rec.title) ?? id;
      return { id, title };
    })
    .filter((item): item is { id: string; title: string } => item !== null);
};

const normalizeNumberMap = (value: unknown): Record<string, number> => {
  const record = asRecord(value);
  if (!record) {
    return {};
  }

  return Object.entries(record).reduce<Record<string, number>>((normalized, [key, rawValue]) => {
    const metric = normalizeOptionalNumber(rawValue);
    if (metric === null) {
      return normalized;
    }

    normalized[key] = metric;
    return normalized;
  }, {});
};

const cloneRecord = (value: unknown): Record<string, unknown> => {
  const record = asRecord(value);
  return record ? { ...record } : {};
};

const normalizeTrainingRequestModeInput = (value: unknown): string | null => {
  const normalized = normalizeOptionalString(value)?.toLowerCase();
  if (!normalized) {
    return null;
  }

  return normalized;
};

export const normalizeTrainingMode = (value: unknown): TrainingMode => {
  const normalized = normalizeTrainingRequestModeInput(value);
  if (!normalized) {
    return 'guided';
  }

  switch (normalized) {
    case 'self-paced':
    case 'self_paced':
      return 'self-paced';
    case 'adaptive':
      return 'adaptive';
    case 'guided':
      return 'guided';
    default:
      throw new ServiceError({
        code: 'VALIDATION_ERROR',
        message: `Unsupported training mode in request: ${normalized}.`,
      });
  }
};

const parseTrainingModeFromResponse = (
  value: unknown,
  fieldPath: string
): TrainingMode => {
  const normalized = normalizeTrainingRequestModeInput(value);

  switch (normalized) {
    case 'guided':
      return 'guided';
    case 'self-paced':
      return 'self-paced';
    case 'adaptive':
      return 'adaptive';
    default:
      throw new ServiceError({
        code: 'INVALID_RESPONSE',
        message: `Unsupported training mode in response at ${fieldPath}.`,
      });
  }
};

const normalizeTrainingPlayerProfile = (
  payload: TrainingPlayerProfileApi | null | undefined
): TrainingPlayerProfile | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  const profile: TrainingPlayerProfile = {
    name: normalizeOptionalString(payload.name),
    gender: normalizeOptionalString(payload.gender),
    identity: normalizeOptionalString(payload.identity),
    age: normalizeOptionalNumber(payload.age),
  };

  return Object.values(profile).every((value) => value === null) ? null : profile;
};

const normalizeTrainingScenarioOption = (
  payload: TrainingScenarioOptionApiResponse | null | undefined
): TrainingScenarioOption | null => {
  const optionId = normalizeOptionalString(payload?.id);
  if (!optionId) {
    return null;
  }

  return {
    id: optionId,
    label: normalizeOptionalString(payload?.label) ?? optionId,
    impactHint: normalizeOptionalString(payload?.impact_hint) ?? '',
  };
};

const normalizeTrainingScenarioRecommendation = (
  payload: TrainingScenarioRecommendationApiResponse | null | undefined
): TrainingScenarioRecommendation | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  return {
    mode: parseTrainingModeFromResponse(payload.mode, 'recommendation.mode'),
    rankScore: normalizeNumber(payload.rank_score),
    weaknessScore: normalizeNumber(payload.weakness_score),
    stateBoostScore: normalizeNumber(payload.state_boost_score),
    riskBoostScore: normalizeNumber(payload.risk_boost_score),
    phaseBoostScore: normalizeNumber(payload.phase_boost_score),
    reasons: normalizeStringArray(payload.reasons),
    rank: normalizeOptionalNumber(payload.rank),
  };
};

const normalizeTrainingDecisionCandidate = (
  payload: TrainingDecisionCandidateApiResponse | null | undefined
): TrainingDecisionCandidate | null => {
  const scenarioId = normalizeOptionalString(payload?.scenario_id);
  if (!scenarioId) {
    return null;
  }

  return {
    scenarioId,
    title: normalizeOptionalString(payload?.title) ?? '',
    rank: normalizeOptionalNumber(payload?.rank),
    rankScore: normalizeNumber(payload?.rank_score),
    isSelected: payload?.is_selected === true,
    isRecommended: payload?.is_recommended === true,
  };
};

const normalizeTrainingBranchTransition = (
  payload: TrainingBranchTransitionApiResponse | null | undefined
): TrainingBranchTransition | null => {
  const sourceScenarioId = normalizeOptionalString(payload?.source_scenario_id);
  const targetScenarioId = normalizeOptionalString(payload?.target_scenario_id);
  if (!sourceScenarioId || !targetScenarioId) {
    return null;
  }

  return {
    sourceScenarioId,
    targetScenarioId,
    transitionType: normalizeOptionalString(payload?.transition_type) ?? 'branch',
    reason: normalizeOptionalString(payload?.reason) ?? '',
    triggeredFlags: normalizeStringArray(payload?.triggered_flags),
    matchedRule: cloneRecord(payload?.matched_rule),
  };
};

const normalizeTrainingRoundDecisionContext = (
  payload: TrainingRoundDecisionContextApiResponse | null | undefined
): TrainingRoundDecisionContext | null => {
  const selectedScenarioId = normalizeOptionalString(payload?.selected_scenario_id);
  if (!selectedScenarioId) {
    return null;
  }

  return {
    mode: parseTrainingModeFromResponse(payload?.mode, 'decision_context.mode'),
    selectionSource: normalizeOptionalString(payload?.selection_source) ?? 'manual',
    selectedScenarioId,
    recommendedScenarioId: normalizeOptionalString(payload?.recommended_scenario_id),
    candidatePool: Array.isArray(payload?.candidate_pool)
      ? payload.candidate_pool
          .map((item) => normalizeTrainingDecisionCandidate(item))
          .filter((item): item is TrainingDecisionCandidate => item !== null)
      : [],
    selectedRecommendation: normalizeTrainingScenarioRecommendation(payload?.selected_recommendation),
    recommendedRecommendation: normalizeTrainingScenarioRecommendation(
      payload?.recommended_recommendation
    ),
    selectedBranchTransition: normalizeTrainingBranchTransition(payload?.selected_branch_transition),
    recommendedBranchTransition: normalizeTrainingBranchTransition(
      payload?.recommended_branch_transition
    ),
  };
};

const normalizeMajorSceneOrder = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const n = Math.trunc(value);
    return n > 0 ? n : null;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value.trim());
    if (Number.isFinite(parsed)) {
      const n = Math.trunc(parsed);
      return n > 0 ? n : null;
    }
  }
  return null;
};

const normalizeTrainingScenario = (
  payload: TrainingScenarioApiResponse | null | undefined
): TrainingScenario | null => {
  const scenarioId = normalizeOptionalString(payload?.id);
  if (!scenarioId) {
    return null;
  }

  return {
    id: scenarioId,
    title: normalizeOptionalString(payload?.title) ?? '',
    eraDate: normalizeOptionalString(payload?.era_date) ?? '',
    location: normalizeOptionalString(payload?.location) ?? '',
    brief: normalizeOptionalString(payload?.brief) ?? '',
    mission: normalizeOptionalString(payload?.mission) ?? '',
    decisionFocus: normalizeOptionalString(payload?.decision_focus) ?? '',
    targetSkills: normalizeStringArray(payload?.target_skills),
    riskTags: normalizeStringArray(payload?.risk_tags),
    options: Array.isArray(payload?.options)
      ? payload.options
          .map((item) => normalizeTrainingScenarioOption(item))
          .filter((item): item is TrainingScenarioOption => item !== null)
      : [],
    completionHint: normalizeOptionalString(payload?.completion_hint) ?? '',
    recommendation: normalizeTrainingScenarioRecommendation(payload?.recommendation),
    sceneLevel: normalizeOptionalString(payload?.scene_level),
    majorSceneId: normalizeOptionalString(payload?.major_scene_id),
    majorSceneOrder: normalizeMajorSceneOrder(payload?.major_scene_order),
  };
};

const normalizeTrainingRuntimeFlags = (
  payload: TrainingRuntimeFlagsApiResponse | null | undefined
): TrainingRuntimeFlags => ({
  panicTriggered: payload?.panic_triggered === true,
  sourceExposed: payload?.source_exposed === true,
  editorLocked: payload?.editor_locked === true,
  highRiskPath: payload?.high_risk_path === true,
});

const normalizeTrainingRuntimeStateBar = (
  payload: TrainingRuntimeStateBarApiResponse | null | undefined
): TrainingRuntimeStateBar => ({
  editorTrust: normalizeNumber(payload?.editor_trust),
  publicStability: normalizeNumber(payload?.public_stability),
  sourceSafety: normalizeNumber(payload?.source_safety),
});

interface RuntimeStateFallbacks {
  roundNo: number;
  sceneId?: string | null;
  kState?: Record<string, number>;
  sState?: Record<string, number>;
  playerProfile?: TrainingPlayerProfile | null;
}

const normalizeTrainingRuntimeState = (
  payload: TrainingRuntimeStateApiResponse | null | undefined,
  fallbacks: RuntimeStateFallbacks
): TrainingRuntimeState => {
  const normalizedKState = normalizeNumberMap(payload?.k_state);
  const normalizedSState = normalizeNumberMap(payload?.s_state);
  const normalizedPlayerProfile =
    normalizeTrainingPlayerProfile(payload?.player_profile) ?? fallbacks.playerProfile ?? null;

  return {
    currentRoundNo: normalizeNumber(payload?.current_round_no, fallbacks.roundNo),
    currentSceneId: normalizeOptionalString(payload?.current_scene_id) ?? fallbacks.sceneId ?? null,
    kState: Object.keys(normalizedKState).length > 0 ? normalizedKState : fallbacks.kState ?? {},
    sState: Object.keys(normalizedSState).length > 0 ? normalizedSState : fallbacks.sState ?? {},
    runtimeFlags: normalizeTrainingRuntimeFlags(payload?.runtime_flags),
    stateBar: normalizeTrainingRuntimeStateBar(payload?.state_bar),
    playerProfile: normalizedPlayerProfile,
  };
};

const normalizeTrainingProgressAnchor = (
  payload: TrainingSessionProgressAnchorResponse | null | undefined,
  roundNo: number,
  totalRounds: number
): TrainingProgressAnchor => {
  const fallbackProgressPercent = totalRounds > 0 ? (roundNo / totalRounds) * 100 : 0;
  const rawProgressPercent = normalizeNumber(
    payload?.progress_percent,
    fallbackProgressPercent
  );
  const progressPercent =
    rawProgressPercent >= 0 && rawProgressPercent <= 1
      ? rawProgressPercent * 100
      : rawProgressPercent;

  return {
    roundNo: normalizeNumber(payload?.current_round_no, roundNo),
    totalRounds: normalizeNumber(payload?.total_rounds, totalRounds),
    completedRounds: normalizeNumber(payload?.completed_rounds, roundNo),
    remainingRounds: normalizeNumber(
      payload?.remaining_rounds,
      Math.max(totalRounds - roundNo, 0)
    ),
    progressPercent,
    nextRoundNo: normalizeOptionalNumber(payload?.next_round_no),
  };
};

const normalizeTrainingEvaluation = (
  payload: TrainingEvaluationApiResponse | null | undefined
): TrainingEvaluation => ({
  llmModel: normalizeOptionalString(payload?.llm_model) ?? 'rules_v1',
  confidence: normalizeNumber(payload?.confidence, 0.5),
  riskFlags: normalizeStringArray(payload?.risk_flags),
  skillDelta: normalizeNumberMap(payload?.skill_delta),
  stateDelta: normalizeNumberMap(payload?.s_delta),
  evidence: normalizeStringArray(payload?.evidence),
  skillScoresPreview: normalizeNumberMap(payload?.skill_scores_preview),
  evalMode: normalizeOptionalString(payload?.eval_mode) ?? 'rules_only',
  fallbackReason: normalizeOptionalString(payload?.fallback_reason),
  calibration: asRecord(payload?.calibration) ? cloneRecord(payload?.calibration) : null,
  llmRawText: normalizeOptionalString(payload?.llm_raw_text),
});

const normalizeTrainingConsequenceEvent = (
  payload: TrainingConsequenceEventApiResponse | null | undefined
): TrainingConsequenceEvent | null => {
  const eventType = normalizeOptionalString(payload?.event_type);
  if (!eventType) {
    return null;
  }

  return {
    eventType,
    label: normalizeOptionalString(payload?.label) ?? '',
    summary: normalizeOptionalString(payload?.summary) ?? '',
    severity: normalizeOptionalString(payload?.severity) ?? 'medium',
    roundNo: normalizeOptionalNumber(payload?.round_no),
    relatedFlag: normalizeOptionalString(payload?.related_flag),
    stateBar: payload?.state_bar ? normalizeTrainingRuntimeStateBar(payload.state_bar) : null,
    payload: cloneRecord(payload?.payload),
  };
};

const normalizeTrainingMediaTaskStatus = (
  value: unknown
): TrainingMediaTaskResult['status'] => {
  const status = normalizeOptionalString(value)?.toLowerCase();
  switch (status) {
    case 'pending':
    case 'running':
    case 'succeeded':
    case 'failed':
    case 'timeout':
      return status;
    default:
      return 'unknown';
  }
};

export const normalizeTrainingMediaTaskPayload = (
  payload: TrainingMediaTaskApiResponse | null | undefined
): TrainingMediaTaskResult | null => {
  const taskId = normalizeOptionalString(payload?.task_id);
  const sessionId = normalizeOptionalString(payload?.session_id);
  if (!taskId || !sessionId) {
    return null;
  }

  return {
    taskId,
    sessionId,
    roundNo: normalizeOptionalNumber(payload?.round_no),
    taskType: normalizeOptionalString(payload?.task_type) ?? 'unknown',
    status: normalizeTrainingMediaTaskStatus(payload?.status),
    result: asRecord(payload?.result) ? cloneRecord(payload?.result) : null,
    error: asRecord(payload?.error) ? cloneRecord(payload?.error) : null,
    createdAt: normalizeOptionalString(payload?.created_at),
    updatedAt: normalizeOptionalString(payload?.updated_at),
    startedAt: normalizeOptionalString(payload?.started_at),
    finishedAt: normalizeOptionalString(payload?.finished_at),
  };
};

export const normalizeTrainingMediaTaskListPayload = (
  payload: TrainingMediaTaskListResponse | null | undefined
): TrainingMediaTaskListResult => ({
  sessionId: normalizeOptionalString(payload?.session_id) ?? '',
  items: Array.isArray(payload?.items)
    ? payload.items
        .map((item) => normalizeTrainingMediaTaskPayload(item))
        .filter((item): item is TrainingMediaTaskResult => item !== null)
    : [],
});

const readTaskStringField = (
  source: Record<string, unknown> | null,
  candidateKeys: string[]
): string | null => {
  if (!source) {
    return null;
  }

  for (const key of candidateKeys) {
    const value = normalizeOptionalString(source[key]);
    if (value) {
      return value;
    }
  }

  return null;
};

const readTaskFirstStringFromArrayField = (
  source: Record<string, unknown> | null,
  candidateKeys: string[]
): string | null => {
  if (!source) {
    return null;
  }

  for (const key of candidateKeys) {
    const value = source[key];
    if (!Array.isArray(value)) {
      continue;
    }

    for (const item of value) {
      const normalized = normalizeOptionalString(item);
      if (normalized) {
        return normalized;
      }
    }
  }

  return null;
};

export const normalizeTrainingMediaTaskView = (task: TrainingMediaTaskResult): TrainingMediaTaskView => {
  const previewUrl =
    readTaskStringField(task.result, ['preview_url', 'image_url', 'url']) ??
    readTaskFirstStringFromArrayField(task.result, ['image_urls', 'urls']);
  const audioUrl = readTaskStringField(task.result, ['audio_url', 'speech_url', 'voice_url', 'url']);
  const generatedText = readTaskStringField(task.result, ['generated_text', 'text', 'content', 'summary']);
  const errorMessage =
    readTaskStringField(task.error, ['message', 'reason', 'detail', 'error']) ??
    (task.status === 'failed' || task.status === 'timeout' ? 'Media task failed.' : null);

  return {
    taskId: task.taskId,
    sessionId: task.sessionId,
    roundNo: task.roundNo,
    taskType: task.taskType,
    status: task.status,
    createdAt: task.createdAt,
    updatedAt: task.updatedAt,
    previewUrl,
    audioUrl,
    generatedText,
    errorMessage,
  };
};

const normalizeTrainingRoundSubmitMediaTaskSummary = (
  payload: TrainingRoundSubmitMediaTaskSummaryApiResponse | null | undefined
): TrainingRoundSubmitMediaTaskSummary | null => {
  const taskId = normalizeOptionalString(payload?.task_id);
  if (!taskId) {
    return null;
  }

  const taskType = normalizeOptionalString(payload?.task_type) ?? 'unknown';
  const status = normalizeOptionalString(payload?.status) ?? 'unknown';

  return {
    taskId,
    taskType,
    status,
  };
};

const normalizeNumberArray = (value: unknown): number[] =>
  Array.isArray(value)
    ? value
        .map((item) => normalizeOptionalNumber(item))
        .filter((item): item is number => item !== null)
    : [];

const normalizeTrainingDiagnosticsCountItem = (
  payload: TrainingDiagnosticsCountItemApiResponse | null | undefined
): TrainingDiagnosticsCountItem | null => {
  const code = normalizeOptionalString(payload?.code);
  if (!code) {
    return null;
  }

  return {
    code,
    count: normalizeNumber(payload?.count),
  };
};

const normalizeTrainingMetricObservation = (
  payload: TrainingMetricObservationApiResponse | null | undefined
): TrainingMetricObservation | null => {
  const code = normalizeOptionalString(payload?.code);
  if (!code) {
    return null;
  }

  return {
    code,
    before: normalizeNumber(payload?.before),
    delta: normalizeNumber(payload?.delta),
    after: normalizeNumber(payload?.after),
    isTarget: payload?.is_target === true,
  };
};

const normalizeTrainingKtObservation = (
  payload: TrainingKtObservationApiResponse | null | undefined
): TrainingKtObservation | null => {
  const scenarioId = normalizeOptionalString(payload?.scenario_id);
  if (!scenarioId) {
    return null;
  }

  return {
    scenarioId,
    scenarioTitle: normalizeOptionalString(payload?.scenario_title) ?? '',
    trainingMode: parseTrainingModeFromResponse(payload?.training_mode, 'kt_observation.training_mode'),
    roundNo: normalizeOptionalNumber(payload?.round_no),
    primarySkillCode: normalizeOptionalString(payload?.primary_skill_code),
    primaryRiskFlag: normalizeOptionalString(payload?.primary_risk_flag),
    isHighRisk: payload?.is_high_risk === true,
    targetSkills: normalizeStringArray(payload?.target_skills),
    weakSkillsBefore: normalizeStringArray(payload?.weak_skills_before),
    riskFlags: normalizeStringArray(payload?.risk_flags),
    focusTags: normalizeStringArray(payload?.focus_tags),
    evidence: normalizeStringArray(payload?.evidence),
    skillObservations: Array.isArray(payload?.skill_observations)
      ? payload.skill_observations
          .map((item) => normalizeTrainingMetricObservation(item))
          .filter((item): item is TrainingMetricObservation => item !== null)
      : [],
    stateObservations: Array.isArray(payload?.state_observations)
      ? payload.state_observations
          .map((item) => normalizeTrainingMetricObservation(item))
          .filter((item): item is TrainingMetricObservation => item !== null)
      : [],
    observationSummary: normalizeOptionalString(payload?.observation_summary) ?? '',
  };
};

const normalizeTrainingRecommendationLog = (
  payload: TrainingRecommendationLogApiResponse | null | undefined
): TrainingRecommendationLog | null => {
  const roundNo = normalizeOptionalNumber(payload?.round_no);
  if (roundNo === null) {
    return null;
  }

  return {
    roundNo,
    trainingMode: parseTrainingModeFromResponse(
      payload?.training_mode,
      'recommendation_log.training_mode'
    ),
    selectionSource: normalizeOptionalString(payload?.selection_source),
    recommendedScenarioId: normalizeOptionalString(payload?.recommended_scenario_id),
    selectedScenarioId: normalizeOptionalString(payload?.selected_scenario_id),
    candidatePool: Array.isArray(payload?.candidate_pool)
      ? payload.candidate_pool
          .map((item) => normalizeTrainingDecisionCandidate(item))
          .filter((item): item is TrainingDecisionCandidate => item !== null)
      : [],
    recommendedRecommendation: normalizeTrainingScenarioRecommendation(
      payload?.recommended_recommendation
    ),
    selectedRecommendation: normalizeTrainingScenarioRecommendation(
      payload?.selected_recommendation
    ),
    decisionContext: normalizeTrainingRoundDecisionContext(payload?.decision_context),
  };
};

const normalizeTrainingAuditEvent = (
  payload: TrainingAuditEventApiResponse | null | undefined
): TrainingAuditEvent | null => {
  const eventType = normalizeOptionalString(payload?.event_type);
  if (!eventType) {
    return null;
  }

  return {
    eventType,
    payload: cloneRecord(payload?.payload),
    roundNo: normalizeOptionalNumber(payload?.round_no),
    timestamp: normalizeOptionalString(payload?.timestamp),
  };
};

const normalizeTrainingReportMetric = (
  payload: TrainingReportMetricApiResponse | null | undefined
): TrainingReportMetric | null => {
  const code = normalizeOptionalString(payload?.code);
  if (!code) {
    return null;
  }

  return {
    code,
    initial: normalizeNumber(payload?.initial),
    final: normalizeNumber(payload?.final),
    delta: normalizeNumber(payload?.delta),
    weight: normalizeOptionalNumber(payload?.weight),
    isLowestFinal: payload?.is_lowest_final === true,
    isHighestGain: payload?.is_highest_gain === true,
  };
};

const normalizeTrainingReportCurvePoint = (
  payload: TrainingReportCurvePointApiResponse | null | undefined
): TrainingReportCurvePoint | null => {
  const roundNo = normalizeOptionalNumber(payload?.round_no);
  if (roundNo === null) {
    return null;
  }

  return {
    roundNo,
    scenarioId: normalizeOptionalString(payload?.scenario_id),
    scenarioTitle: normalizeOptionalString(payload?.scenario_title) ?? '',
    kState: normalizeNumberMap(payload?.k_state),
    sState: normalizeNumberMap(payload?.s_state),
    weightedKScore: normalizeNumber(payload?.weighted_k_score),
    isHighRisk: payload?.is_high_risk === true,
    riskFlags: normalizeStringArray(payload?.risk_flags),
    primarySkillCode: normalizeOptionalString(payload?.primary_skill_code),
    timestamp: normalizeOptionalString(payload?.timestamp),
  };
};

const normalizeTrainingBranchTransitionSummary = (
  payload: TrainingBranchTransitionSummaryApiResponse | null | undefined
): TrainingBranchTransitionSummary | null => {
  const sourceScenarioId = normalizeOptionalString(payload?.source_scenario_id);
  const targetScenarioId = normalizeOptionalString(payload?.target_scenario_id);
  if (!sourceScenarioId || !targetScenarioId) {
    return null;
  }

  return {
    sourceScenarioId,
    targetScenarioId,
    transitionType: normalizeOptionalString(payload?.transition_type) ?? 'branch',
    reason: normalizeOptionalString(payload?.reason) ?? '',
    count: normalizeNumber(payload?.count),
    roundNos: normalizeNumberArray(payload?.round_nos),
    triggeredFlags: normalizeStringArray(payload?.triggered_flags),
  };
};

const normalizeTrainingReportHistoryItem = (
  payload: TrainingReportHistoryItemApiResponse | null | undefined
): TrainingReportHistoryItem | null => {
  const roundNo = normalizeOptionalNumber(payload?.round_no);
  const scenarioId = normalizeOptionalString(payload?.scenario_id);
  if (roundNo === null || !scenarioId) {
    return null;
  }

  const ktObservation = normalizeTrainingKtObservation(payload?.kt_observation);
  const runtimeState = payload?.runtime_state
    ? normalizeTrainingRuntimeState(payload.runtime_state, {
        roundNo,
        sceneId: scenarioId,
      })
    : null;

  return {
    roundNo,
    scenarioId,
    userInput: normalizeOptionalString(payload?.user_input) ?? '',
    selectedOption: normalizeOptionalString(payload?.selected_option),
    evaluation: payload?.evaluation ? normalizeTrainingEvaluation(payload.evaluation) : null,
    kStateBefore: normalizeNumberMap(payload?.k_state_before),
    kStateAfter: normalizeNumberMap(payload?.k_state_after),
    sStateBefore: normalizeNumberMap(payload?.s_state_before),
    sStateAfter: normalizeNumberMap(payload?.s_state_after),
    timestamp: normalizeOptionalString(payload?.timestamp),
    decisionContext: normalizeTrainingRoundDecisionContext(payload?.decision_context),
    ktObservation,
    runtimeState,
    consequenceEvents: Array.isArray(payload?.consequence_events)
      ? payload.consequence_events
          .map((item) => normalizeTrainingConsequenceEvent(item))
          .filter((item): item is TrainingConsequenceEvent => item !== null)
      : [],
  };
};

const normalizeTrainingReportSummary = (
  payload: TrainingReportSummaryApiResponse | null | undefined
): TrainingReportSummary | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  return {
    weightedScoreInitial: normalizeNumber(payload?.weighted_score_initial),
    weightedScoreFinal: normalizeNumber(payload?.weighted_score_final),
    weightedScoreDelta: normalizeNumber(payload?.weighted_score_delta),
    strongestImprovedSkillCode: normalizeOptionalString(payload?.strongest_improved_skill_code),
    strongestImprovedSkillDelta: normalizeNumber(payload?.strongest_improved_skill_delta),
    weakestSkillCode: normalizeOptionalString(payload?.weakest_skill_code),
    weakestSkillScore: normalizeNumber(payload?.weakest_skill_score),
    dominantRiskFlag: normalizeOptionalString(payload?.dominant_risk_flag),
    highRiskRoundCount: normalizeNumber(payload?.high_risk_round_count),
    highRiskRoundNos: normalizeNumberArray(payload?.high_risk_round_nos),
    panicTriggerRoundCount: normalizeNumber(payload?.panic_trigger_round_count),
    sourceExposedRoundCount: normalizeNumber(payload?.source_exposed_round_count),
    editorLockedRoundCount: normalizeNumber(payload?.editor_locked_round_count),
    highRiskPathRoundCount: normalizeNumber(payload?.high_risk_path_round_count),
    branchTransitionCount: normalizeNumber(payload?.branch_transition_count),
    branchTransitionRounds: normalizeNumberArray(payload?.branch_transition_rounds),
    branchTransitions: Array.isArray(payload?.branch_transitions)
      ? payload.branch_transitions
          .map((item) => normalizeTrainingBranchTransitionSummary(item))
          .filter((item): item is TrainingBranchTransitionSummary => item !== null)
      : [],
    riskFlagCounts: Array.isArray(payload?.risk_flag_counts)
      ? payload.risk_flag_counts
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    completedScenarioIds: normalizeStringArray(payload?.completed_scenario_ids),
    reviewSuggestions: normalizeStringArray(payload?.review_suggestions),
  };
};

const normalizeTrainingDiagnosticsSummary = (
  payload: TrainingDiagnosticsSummaryApiResponse | null | undefined
): TrainingDiagnosticsSummary | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  return {
    totalRecommendationLogs: normalizeNumber(payload?.total_recommendation_logs),
    totalAuditEvents: normalizeNumber(payload?.total_audit_events),
    totalKtObservations: normalizeNumber(payload?.total_kt_observations),
    highRiskRoundCount: normalizeNumber(payload?.high_risk_round_count),
    highRiskRoundNos: normalizeNumberArray(payload?.high_risk_round_nos),
    recommendedVsSelectedMismatchCount: normalizeNumber(
      payload?.recommended_vs_selected_mismatch_count
    ),
    recommendedVsSelectedMismatchRounds: normalizeNumberArray(
      payload?.recommended_vs_selected_mismatch_rounds
    ),
    riskFlagCounts: Array.isArray(payload?.risk_flag_counts)
      ? payload.risk_flag_counts
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    primarySkillFocusCounts: Array.isArray(payload?.primary_skill_focus_counts)
      ? payload.primary_skill_focus_counts
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    topWeakSkills: Array.isArray(payload?.top_weak_skills)
      ? payload.top_weak_skills
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    selectionSourceCounts: Array.isArray(payload?.selection_source_counts)
      ? payload.selection_source_counts
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    eventTypeCounts: Array.isArray(payload?.event_type_counts)
      ? payload.event_type_counts
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    phaseTagCounts: Array.isArray(payload?.phase_tag_counts)
      ? payload.phase_tag_counts
          .map((item) => normalizeTrainingDiagnosticsCountItem(item))
          .filter((item): item is TrainingDiagnosticsCountItem => item !== null)
      : [],
    phaseTransitionCount: normalizeNumber(payload?.phase_transition_count),
    phaseTransitionRounds: normalizeNumberArray(payload?.phase_transition_rounds),
    panicTriggerRoundCount: normalizeNumber(payload?.panic_trigger_round_count),
    panicTriggerRounds: normalizeNumberArray(payload?.panic_trigger_rounds),
    sourceExposedRoundCount: normalizeNumber(payload?.source_exposed_round_count),
    sourceExposedRounds: normalizeNumberArray(payload?.source_exposed_rounds),
    editorLockedRoundCount: normalizeNumber(payload?.editor_locked_round_count),
    editorLockedRounds: normalizeNumberArray(payload?.editor_locked_rounds),
    highRiskPathRoundCount: normalizeNumber(payload?.high_risk_path_round_count),
    highRiskPathRounds: normalizeNumberArray(payload?.high_risk_path_rounds),
    branchTransitionCount: normalizeNumber(payload?.branch_transition_count),
    branchTransitionRounds: normalizeNumberArray(payload?.branch_transition_rounds),
    branchTransitions: Array.isArray(payload?.branch_transitions)
      ? payload.branch_transitions
          .map((item) => normalizeTrainingBranchTransitionSummary(item))
          .filter((item): item is TrainingBranchTransitionSummary => item !== null)
      : [],
    lastPrimarySkillCode: normalizeOptionalString(payload?.last_primary_skill_code),
    lastPrimaryRiskFlag: normalizeOptionalString(payload?.last_primary_risk_flag),
    lastEventType: normalizeOptionalString(payload?.last_event_type),
    lastPhaseTags: normalizeStringArray(payload?.last_phase_tags),
    lastBranchTransition: normalizeTrainingBranchTransition(payload?.last_branch_transition),
  };
};

export const normalizeTrainingInitPayload = (
  payload: TrainingInitResponse | null | undefined,
  trainingMode: unknown
): TrainingInitResult => {
  const roundNo = normalizeNumber(payload?.round_no);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);
  const nextScenario = normalizeTrainingScenario(payload?.next_scenario);
  const scenarioSequence = normalizeTrainingScenarioSequenceOutlines(payload?.scenario_sequence);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    characterId: normalizeOptionalCharacterId(payload?.character_id),
    trainingMode: normalizeTrainingMode(trainingMode),
    status: normalizeOptionalString(payload?.status) ?? 'initialized',
    roundNo,
    runtimeState: normalizeTrainingRuntimeState(payload?.runtime_state, {
      roundNo,
      sceneId: nextScenario?.id ?? null,
      kState: normalizeNumberMap(payload?.k_state),
      sState: normalizeNumberMap(payload?.s_state),
      playerProfile,
    }),
    nextScenario,
    scenarioCandidates: Array.isArray(payload?.scenario_candidates)
      ? payload.scenario_candidates
          .map((item) => normalizeTrainingScenario(item))
          .filter((item): item is TrainingScenario => item !== null)
      : [],
    scenarioSequence,
  };
};

export const normalizeTrainingScenarioNextPayload = (
  payload: TrainingScenarioNextResponse | null | undefined
): TrainingScenarioNextResult => {
  const roundNo = normalizeNumber(payload?.round_no);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);
  const scenario = normalizeTrainingScenario(payload?.scenario);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    status: normalizeOptionalString(payload?.status) ?? 'in_progress',
    roundNo,
    runtimeState: normalizeTrainingRuntimeState(payload?.runtime_state, {
      roundNo,
      sceneId: scenario?.id ?? null,
      kState: normalizeNumberMap(payload?.k_state),
      sState: normalizeNumberMap(payload?.s_state),
      playerProfile,
    }),
    scenario,
    scenarioCandidates: Array.isArray(payload?.scenario_candidates)
      ? payload.scenario_candidates
          .map((item) => normalizeTrainingScenario(item))
          .filter((item): item is TrainingScenario => item !== null)
      : [],
    ending: asRecord(payload?.ending) ? cloneRecord(payload?.ending) : null,
  };
};

export const normalizeTrainingRoundSubmitPayload = (
  payload: TrainingRoundSubmitResponse | null | undefined
): TrainingRoundSubmitResult => {
  const roundNo = normalizeNumber(payload?.round_no);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);
  const decisionContext = normalizeTrainingRoundDecisionContext(payload?.decision_context);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    roundNo,
    runtimeState: normalizeTrainingRuntimeState(payload?.runtime_state, {
      roundNo,
      sceneId: decisionContext?.selectedScenarioId ?? null,
      kState: normalizeNumberMap(payload?.k_state),
      sState: normalizeNumberMap(payload?.s_state),
      playerProfile,
    }),
    evaluation: normalizeTrainingEvaluation(payload?.evaluation),
    consequenceEvents: Array.isArray(payload?.consequence_events)
      ? payload.consequence_events
          .map((item) => normalizeTrainingConsequenceEvent(item))
          .filter((item): item is TrainingConsequenceEvent => item !== null)
      : [],
    mediaTasks: Array.isArray(payload?.media_tasks)
      ? payload.media_tasks
          .map((item) => normalizeTrainingRoundSubmitMediaTaskSummary(item))
          .filter((item): item is TrainingRoundSubmitMediaTaskSummary => item !== null)
      : [],
    isCompleted: payload?.is_completed === true,
    ending: asRecord(payload?.ending) ? cloneRecord(payload?.ending) : null,
    decisionContext,
  };
};

export const normalizeTrainingProgressPayload = (
  payload: TrainingProgressResponse | null | undefined
): TrainingProgressResult => {
  const roundNo = normalizeNumber(payload?.round_no);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);
  const decisionContext = normalizeTrainingRoundDecisionContext(payload?.decision_context);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    characterId: normalizeOptionalCharacterId(payload?.character_id),
    status: normalizeOptionalString(payload?.status) ?? 'in_progress',
    roundNo,
    totalRounds: normalizeNumber(payload?.total_rounds),
    runtimeState: normalizeTrainingRuntimeState(payload?.runtime_state, {
      roundNo,
      kState: normalizeNumberMap(payload?.k_state),
      sState: normalizeNumberMap(payload?.s_state),
      playerProfile,
    }),
    decisionContext,
    consequenceEvents: Array.isArray(payload?.consequence_events)
      ? payload.consequence_events
          .map((item) => normalizeTrainingConsequenceEvent(item))
          .filter((item): item is TrainingConsequenceEvent => item !== null)
      : [],
    ending: asRecord(payload?.ending) ? cloneRecord(payload?.ending) : null,
  };
};

export const normalizeTrainingSessionSummaryPayload = (
  payload: TrainingSessionSummaryResponse | null | undefined
): TrainingSessionSummaryResult => {
  const roundNo = normalizeNumber(payload?.current_round_no);
  const totalRounds = normalizeNumber(payload?.total_rounds);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);
  const resumableScenario = normalizeTrainingScenario(payload?.resumable_scenario);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    characterId: normalizeOptionalCharacterId(payload?.character_id),
    trainingMode: parseTrainingModeFromResponse(payload?.training_mode, 'training_mode'),
    status: normalizeOptionalString(payload?.status) ?? 'initialized',
    roundNo,
    totalRounds,
    runtimeState: normalizeTrainingRuntimeState(payload?.runtime_state, {
      roundNo,
      sceneId: resumableScenario?.id ?? null,
      kState: normalizeNumberMap(payload?.k_state),
      sState: normalizeNumberMap(payload?.s_state),
      playerProfile,
    }),
    progressAnchor: normalizeTrainingProgressAnchor(payload?.progress_anchor, roundNo, totalRounds),
    resumableScenario,
    scenarioCandidates: Array.isArray(payload?.scenario_candidates)
      ? payload.scenario_candidates
          .map((item) => normalizeTrainingScenario(item))
          .filter((item): item is TrainingScenario => item !== null)
      : [],
    canResume: payload?.can_resume === true,
    isCompleted: payload?.is_completed === true,
    createdAt: normalizeOptionalString(payload?.created_at),
    updatedAt: normalizeOptionalString(payload?.updated_at),
    endTime: normalizeOptionalString(payload?.end_time),
  };
};

const normalizeTrainingReportRoundSnapshot = (raw: unknown): TrainingReportRoundSnapshot | null => {
  const record = asRecord(raw);
  if (!record) {
    return null;
  }
  const branchRaw = record.branch_transition;
  let branchTransition: Record<string, unknown> | null = null;
  if (branchRaw && typeof branchRaw === 'object' && !Array.isArray(branchRaw)) {
    branchTransition = cloneRecord(branchRaw as Record<string, unknown>);
  }
  return {
    roundNo: normalizeNumber(record.round_no),
    scenarioId: normalizeOptionalString(record.scenario_id) ?? '',
    scenarioTitle: normalizeOptionalString(record.scenario_title),
    riskFlags: normalizeStringArray(record.risk_flags),
    isHighRisk: record.is_high_risk === true,
    branchTransition,
  };
};

export const normalizeTrainingReportPayload = (
  payload: TrainingReportResponse | null | undefined
): TrainingReportResult => {
  const rounds = normalizeNumber(payload?.rounds);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    characterId: normalizeOptionalCharacterId(payload?.character_id),
    status: normalizeOptionalString(payload?.status) ?? 'completed',
    rounds,
    kStateFinal: normalizeNumberMap(payload?.k_state_final),
    sStateFinal: normalizeNumberMap(payload?.s_state_final),
    improvement: normalizeNumber(payload?.improvement),
    playerProfile,
    runtimeState: payload?.runtime_state
      ? normalizeTrainingRuntimeState(payload.runtime_state, {
          roundNo: rounds,
          kState: normalizeNumberMap(payload?.k_state_final),
          sState: normalizeNumberMap(payload?.s_state_final),
          playerProfile,
        })
      : null,
    ending: asRecord(payload?.ending) ? cloneRecord(payload?.ending) : null,
    summary: normalizeTrainingReportSummary(payload?.summary),
    abilityRadar: Array.isArray(payload?.ability_radar)
      ? payload.ability_radar
          .map((item) => normalizeTrainingReportMetric(item))
          .filter((item): item is TrainingReportMetric => item !== null)
      : [],
    stateRadar: Array.isArray(payload?.state_radar)
      ? payload.state_radar
          .map((item) => normalizeTrainingReportMetric(item))
          .filter((item): item is TrainingReportMetric => item !== null)
      : [],
    growthCurve: Array.isArray(payload?.growth_curve)
      ? payload.growth_curve
          .map((item) => normalizeTrainingReportCurvePoint(item))
          .filter((item): item is TrainingReportCurvePoint => item !== null)
      : [],
    roundSnapshots: Array.isArray(payload?.round_snapshots)
      ? payload.round_snapshots
          .map((item) => normalizeTrainingReportRoundSnapshot(item))
          .filter((item): item is TrainingReportRoundSnapshot => item !== null)
      : [],
    history: Array.isArray(payload?.history)
      ? payload.history
          .map((item) => normalizeTrainingReportHistoryItem(item))
          .filter((item): item is TrainingReportHistoryItem => item !== null)
      : [],
  };
};

export const normalizeTrainingDiagnosticsPayload = (
  payload: TrainingDiagnosticsResponse | null | undefined
): TrainingDiagnosticsResult => {
  const roundNo = normalizeNumber(payload?.round_no);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    characterId: normalizeOptionalCharacterId(payload?.character_id),
    status: normalizeOptionalString(payload?.status) ?? 'completed',
    roundNo,
    playerProfile,
    runtimeState: payload?.runtime_state
      ? normalizeTrainingRuntimeState(payload.runtime_state, {
          roundNo,
          playerProfile,
        })
      : null,
    summary: normalizeTrainingDiagnosticsSummary(payload?.summary),
    recommendationLogs: Array.isArray(payload?.recommendation_logs)
      ? payload.recommendation_logs
          .map((item) => normalizeTrainingRecommendationLog(item))
          .filter((item): item is TrainingRecommendationLog => item !== null)
      : [],
    auditEvents: Array.isArray(payload?.audit_events)
      ? payload.audit_events
          .map((item) => normalizeTrainingAuditEvent(item))
          .filter((item): item is TrainingAuditEvent => item !== null)
      : [],
    ktObservations: Array.isArray(payload?.kt_observations)
      ? payload.kt_observations
          .map((item) => normalizeTrainingKtObservation(item))
          .filter((item): item is TrainingKtObservation => item !== null)
      : [],
    ending: asRecord(payload?.ending) ? cloneRecord(payload?.ending) : null,
  };
};

// ---------------------------------------------------------------------------
// Story Script Narrative resolver (Requirements 6.1–6.4)
// ---------------------------------------------------------------------------

import type { ScriptNarrative } from '@/types/training';

/**
 * 根据 `scenarioId` 从剧本 payload 中解析叙事内容。
 *
 * - v2 payload（`version === "training_story_script_v2"`）：直接从 `payload.narratives[scenarioId]` 读取。
 * - v1 payload 或无 version 字段：使用旧版 `scenes[].scene_id` 前缀匹配逻辑。
 * - 找不到时返回 `null`，不抛出运行时错误（Requirements 6.4）。
 *
 * TODO: 在训练场景叙事渲染组件中调用此函数替代直接访问 `scenes[index]`。
 * 例如：在展示场景独白/对话的组件中，通过 `resolveNarrativeForScenario(storyScriptPayload, scenario.id)`
 * 获取叙事内容，并在返回 `null` 时渲染空白占位（Requirements 6.3, 6.4）。
 */
export const resolveNarrativeForScenario = (
  payload: unknown,
  scenarioId: string
): ScriptNarrative | null => {
  const record = asRecord(payload);
  if (!record) {
    return null;
  }

  const version = normalizeOptionalString(record.version);

  if (version === 'training_story_script_v2') {
    // v2: narratives dict keyed by scenario_id (Requirements 6.1)
    const narratives = asRecord(record.narratives);
    if (!narratives) {
      return null;
    }
    const entry = asRecord(narratives[scenarioId]);
    if (!entry) {
      return null;
    }
    return normalizeScriptNarrative(entry);
  }

  // v1 fallback: scenes array with scene_id field (Requirements 6.2)
  const scenes = record.scenes;
  if (!Array.isArray(scenes)) {
    return null;
  }

  for (const scene of scenes) {
    const sceneRecord = asRecord(scene);
    if (!sceneRecord) {
      continue;
    }
    const sceneId = normalizeOptionalString(sceneRecord.scene_id);
    if (!sceneId) {
      continue;
    }
    // Prefix match: scenarioId starts with the scene_id prefix (e.g. "major-1" matches "major-1_micro_...")
    if (scenarioId === sceneId || scenarioId.startsWith(sceneId + '_')) {
      return normalizeScriptNarrative(sceneRecord);
    }
  }

  return null;
};

const normalizeScriptNarrativeLine = (value: unknown) => {
  const rec = asRecord(value);
  if (!rec) {
    return null;
  }
  const speaker = normalizeOptionalString(rec.speaker);
  const content = normalizeOptionalString(rec.content);
  if (speaker === null && content === null) {
    return null;
  }
  return { speaker: speaker ?? '', content: content ?? '' };
};

const normalizeScriptNarrativeOptionItem = (value: unknown) => {
  const rec = asRecord(value);
  if (!rec) {
    return null;
  }
  return {
    option_id: normalizeOptionalString(rec.option_id) ?? '',
    narrative_label: normalizeOptionalString(rec.narrative_label) ?? '',
    impact_hint: normalizeOptionalString(rec.impact_hint) ?? '',
  };
};

const normalizeScriptNarrative = (record: Record<string, unknown>): ScriptNarrative => {
  const dialogue = Array.isArray(record.dialogue)
    ? record.dialogue
        .map(normalizeScriptNarrativeLine)
        .filter((item): item is NonNullable<typeof item> => item !== null)
    : [];
  const visual_elements = Array.isArray(record.visual_elements)
    ? record.visual_elements
        .map((item) => normalizeOptionalString(item))
        .filter((item): item is string => Boolean(item))
    : [];

  const rawOptionsNarrative = asRecord(record.options_narrative) ?? {};
  const options_narrative: ScriptNarrative['options_narrative'] = {};
  for (const [key, val] of Object.entries(rawOptionsNarrative)) {
    const normalized = normalizeScriptNarrativeOptionItem(val);
    if (normalized) {
      options_narrative[key] = normalized;
    }
  }

  return {
    monologue: normalizeOptionalString(record.monologue) ?? '',
    dialogue,
    bridge_summary: normalizeOptionalString(record.bridge_summary) ?? '',
    options_narrative,
    visual_prompt: normalizeOptionalString(record.visual_prompt) ?? '',
    visual_elements,
  };
};
