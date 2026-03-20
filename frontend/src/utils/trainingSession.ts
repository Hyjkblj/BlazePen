import type {
  TrainingBranchTransitionApiResponse,
  TrainingConsequenceEventApiResponse,
  TrainingDecisionCandidateApiResponse,
  TrainingEvaluationApiResponse,
  TrainingInitResponse,
  TrainingPlayerProfileApi,
  TrainingProgressResponse,
  TrainingRoundDecisionContextApiResponse,
  TrainingRoundSubmitResponse,
  TrainingRuntimeFlagsApiResponse,
  TrainingRuntimeStateApiResponse,
  TrainingRuntimeStateBarApiResponse,
  TrainingScenarioApiResponse,
  TrainingScenarioNextResponse,
  TrainingScenarioOptionApiResponse,
  TrainingScenarioRecommendationApiResponse,
} from '@/types/api';
import type {
  TrainingBranchTransition,
  TrainingConsequenceEvent,
  TrainingDecisionCandidate,
  TrainingEvaluation,
  TrainingInitResult,
  TrainingMode,
  TrainingPlayerProfile,
  TrainingProgressResult,
  TrainingRoundDecisionContext,
  TrainingRoundSubmitResult,
  TrainingRuntimeFlags,
  TrainingRuntimeState,
  TrainingRuntimeStateBar,
  TrainingScenario,
  TrainingScenarioNextResult,
  TrainingScenarioOption,
  TrainingScenarioRecommendation,
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
    briefing: normalizeOptionalString(payload?.briefing) ?? '',
    options: Array.isArray(payload?.options)
      ? payload.options
          .map((item) => normalizeTrainingScenarioOption(item))
          .filter((item): item is TrainingScenarioOption => item !== null)
      : [],
    completionHint: normalizeOptionalString(payload?.completion_hint) ?? '',
    recommendation: normalizeTrainingScenarioRecommendation(payload?.recommendation),
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

export const normalizeTrainingInitPayload = (
  payload: TrainingInitResponse | null | undefined,
  trainingMode: unknown
): TrainingInitResult => {
  const roundNo = normalizeNumber(payload?.round_no);
  const playerProfile = normalizeTrainingPlayerProfile(payload?.player_profile);
  const nextScenario = normalizeTrainingScenario(payload?.next_scenario);

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
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

  return {
    sessionId: normalizeOptionalString(payload?.session_id) ?? '',
    status: normalizeOptionalString(payload?.status) ?? 'in_progress',
    roundNo,
    totalRounds: normalizeNumber(payload?.total_rounds),
    runtimeState: normalizeTrainingRuntimeState(payload?.runtime_state, {
      roundNo,
      kState: normalizeNumberMap(payload?.k_state),
      sState: normalizeNumberMap(payload?.s_state),
      playerProfile,
    }),
  };
};
