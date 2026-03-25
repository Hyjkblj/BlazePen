export type TrainingMode = 'guided' | 'self-paced' | 'adaptive';

export type TrainingSessionId = string;

export interface TrainingPlayerProfileInput {
  name?: string | null;
  gender?: string | null;
  identity?: string | null;
  age?: number | null;
}

export interface TrainingPlayerProfile {
  name: string | null;
  gender: string | null;
  identity: string | null;
  age: number | null;
}

export interface TrainingScenarioOption {
  id: string;
  label: string;
  impactHint: string;
}

export interface TrainingScenarioRecommendation {
  mode: TrainingMode;
  rankScore: number;
  weaknessScore: number;
  stateBoostScore: number;
  riskBoostScore: number;
  phaseBoostScore: number;
  reasons: string[];
  rank: number | null;
}

export interface TrainingDecisionCandidate {
  scenarioId: string;
  title: string;
  rank: number | null;
  rankScore: number;
  isSelected: boolean;
  isRecommended: boolean;
}

export interface TrainingBranchTransition {
  sourceScenarioId: string;
  targetScenarioId: string;
  transitionType: string;
  reason: string;
  triggeredFlags: string[];
  matchedRule: Record<string, unknown>;
}

export interface TrainingBranchTransitionSummary {
  sourceScenarioId: string;
  targetScenarioId: string;
  transitionType: string;
  reason: string;
  count: number;
  roundNos: number[];
  triggeredFlags: string[];
}

export interface TrainingRoundDecisionContext {
  mode: TrainingMode;
  selectionSource: string;
  selectedScenarioId: string;
  recommendedScenarioId: string | null;
  candidatePool: TrainingDecisionCandidate[];
  selectedRecommendation: TrainingScenarioRecommendation | null;
  recommendedRecommendation: TrainingScenarioRecommendation | null;
  selectedBranchTransition: TrainingBranchTransition | null;
  recommendedBranchTransition: TrainingBranchTransition | null;
}

export interface TrainingScenario {
  id: string;
  title: string;
  eraDate: string;
  location: string;
  brief: string;
  mission: string;
  decisionFocus: string;
  targetSkills: string[];
  riskTags: string[];
  options: TrainingScenarioOption[];
  completionHint: string;
  recommendation: TrainingScenarioRecommendation | null;
}

export interface TrainingEvaluation {
  llmModel: string;
  confidence: number;
  riskFlags: string[];
  skillDelta: Record<string, number>;
  stateDelta: Record<string, number>;
  evidence: string[];
  skillScoresPreview: Record<string, number>;
  evalMode: string;
  fallbackReason: string | null;
  calibration: Record<string, unknown> | null;
  llmRawText: string | null;
}

export interface TrainingRuntimeFlags {
  panicTriggered: boolean;
  sourceExposed: boolean;
  editorLocked: boolean;
  highRiskPath: boolean;
}

export interface TrainingRuntimeStateBar {
  editorTrust: number;
  publicStability: number;
  sourceSafety: number;
}

export interface TrainingConsequenceEvent {
  eventType: string;
  label: string;
  summary: string;
  severity: string;
  roundNo: number | null;
  relatedFlag: string | null;
  stateBar: TrainingRuntimeStateBar | null;
  payload: Record<string, unknown>;
}

export interface TrainingDiagnosticsCountItem {
  code: string;
  count: number;
}

export interface TrainingMetricObservation {
  code: string;
  before: number;
  delta: number;
  after: number;
  isTarget: boolean;
}

export interface TrainingKtObservation {
  scenarioId: string;
  scenarioTitle: string;
  trainingMode: TrainingMode;
  roundNo: number | null;
  primarySkillCode: string | null;
  primaryRiskFlag: string | null;
  isHighRisk: boolean;
  targetSkills: string[];
  weakSkillsBefore: string[];
  riskFlags: string[];
  focusTags: string[];
  evidence: string[];
  skillObservations: TrainingMetricObservation[];
  stateObservations: TrainingMetricObservation[];
  observationSummary: string;
}

export interface TrainingRecommendationLog {
  roundNo: number;
  trainingMode: TrainingMode;
  selectionSource: string | null;
  recommendedScenarioId: string | null;
  selectedScenarioId: string | null;
  candidatePool: TrainingDecisionCandidate[];
  recommendedRecommendation: TrainingScenarioRecommendation | null;
  selectedRecommendation: TrainingScenarioRecommendation | null;
  decisionContext: TrainingRoundDecisionContext | null;
}

export interface TrainingAuditEvent {
  eventType: string;
  payload: Record<string, unknown>;
  roundNo: number | null;
  timestamp: string | null;
}

export interface TrainingReportMetric {
  code: string;
  initial: number;
  final: number;
  delta: number;
  weight: number | null;
  isLowestFinal: boolean;
  isHighestGain: boolean;
}

export interface TrainingReportCurvePoint {
  roundNo: number;
  scenarioId: string | null;
  scenarioTitle: string;
  kState: Record<string, number>;
  sState: Record<string, number>;
  weightedKScore: number;
  isHighRisk: boolean;
  riskFlags: string[];
  primarySkillCode: string | null;
  timestamp: string | null;
}

export interface TrainingReportHistoryItem {
  roundNo: number;
  scenarioId: string;
  userInput: string;
  selectedOption: string | null;
  evaluation: TrainingEvaluation | null;
  kStateBefore: Record<string, number>;
  kStateAfter: Record<string, number>;
  sStateBefore: Record<string, number>;
  sStateAfter: Record<string, number>;
  timestamp: string | null;
  decisionContext: TrainingRoundDecisionContext | null;
  ktObservation: TrainingKtObservation | null;
  runtimeState: TrainingRuntimeState | null;
  consequenceEvents: TrainingConsequenceEvent[];
}

export interface TrainingReportSummary {
  weightedScoreInitial: number;
  weightedScoreFinal: number;
  weightedScoreDelta: number;
  strongestImprovedSkillCode: string | null;
  strongestImprovedSkillDelta: number;
  weakestSkillCode: string | null;
  weakestSkillScore: number;
  dominantRiskFlag: string | null;
  highRiskRoundCount: number;
  highRiskRoundNos: number[];
  panicTriggerRoundCount: number;
  sourceExposedRoundCount: number;
  editorLockedRoundCount: number;
  highRiskPathRoundCount: number;
  branchTransitionCount: number;
  branchTransitionRounds: number[];
  branchTransitions: TrainingBranchTransitionSummary[];
  riskFlagCounts: TrainingDiagnosticsCountItem[];
  completedScenarioIds: string[];
  reviewSuggestions: string[];
}

export interface TrainingDiagnosticsSummary {
  totalRecommendationLogs: number;
  totalAuditEvents: number;
  totalKtObservations: number;
  highRiskRoundCount: number;
  highRiskRoundNos: number[];
  recommendedVsSelectedMismatchCount: number;
  recommendedVsSelectedMismatchRounds: number[];
  riskFlagCounts: TrainingDiagnosticsCountItem[];
  primarySkillFocusCounts: TrainingDiagnosticsCountItem[];
  topWeakSkills: TrainingDiagnosticsCountItem[];
  selectionSourceCounts: TrainingDiagnosticsCountItem[];
  eventTypeCounts: TrainingDiagnosticsCountItem[];
  phaseTagCounts: TrainingDiagnosticsCountItem[];
  phaseTransitionCount: number;
  phaseTransitionRounds: number[];
  panicTriggerRoundCount: number;
  panicTriggerRounds: number[];
  sourceExposedRoundCount: number;
  sourceExposedRounds: number[];
  editorLockedRoundCount: number;
  editorLockedRounds: number[];
  highRiskPathRoundCount: number;
  highRiskPathRounds: number[];
  branchTransitionCount: number;
  branchTransitionRounds: number[];
  branchTransitions: TrainingBranchTransitionSummary[];
  lastPrimarySkillCode: string | null;
  lastPrimaryRiskFlag: string | null;
  lastEventType: string | null;
  lastPhaseTags: string[];
  lastBranchTransition: TrainingBranchTransition | null;
}

export interface TrainingRuntimeState {
  currentRoundNo: number;
  currentSceneId: string | null;
  kState: Record<string, number>;
  sState: Record<string, number>;
  runtimeFlags: TrainingRuntimeFlags;
  stateBar: TrainingRuntimeStateBar;
  playerProfile: TrainingPlayerProfile | null;
}

export interface TrainingSessionInitParams {
  userId: string;
  characterId?: string | number | null;
  trainingMode?: TrainingMode | 'self_paced';
  playerProfile?: TrainingPlayerProfileInput | null;
}

export interface TrainingScenarioNextParams {
  sessionId: string;
}

export interface TrainingRoundSubmitParams {
  sessionId: string;
  scenarioId: string;
  userInput: string;
  selectedOption?: string | null;
}

export interface TrainingInitResult {
  sessionId: TrainingSessionId;
  characterId: string | null;
  trainingMode: TrainingMode;
  status: string;
  roundNo: number;
  runtimeState: TrainingRuntimeState;
  nextScenario: TrainingScenario | null;
  scenarioCandidates: TrainingScenario[];
}

export interface TrainingScenarioNextResult {
  sessionId: TrainingSessionId;
  status: string;
  roundNo: number;
  runtimeState: TrainingRuntimeState;
  scenario: TrainingScenario | null;
  scenarioCandidates: TrainingScenario[];
  ending: Record<string, unknown> | null;
}

export interface TrainingRoundSubmitResult {
  sessionId: TrainingSessionId;
  roundNo: number;
  runtimeState: TrainingRuntimeState;
  evaluation: TrainingEvaluation;
  consequenceEvents: TrainingConsequenceEvent[];
  isCompleted: boolean;
  ending: Record<string, unknown> | null;
  decisionContext: TrainingRoundDecisionContext | null;
}

export interface TrainingProgressResult {
  sessionId: TrainingSessionId;
  characterId: string | null;
  status: string;
  roundNo: number;
  totalRounds: number;
  runtimeState: TrainingRuntimeState;
  decisionContext: TrainingRoundDecisionContext | null;
  consequenceEvents: TrainingConsequenceEvent[];
}

export interface TrainingProgressAnchor {
  roundNo: number;
  totalRounds: number;
  completedRounds: number;
  remainingRounds: number;
  progressPercent: number;
  nextRoundNo: number | null;
}

export interface TrainingSessionSummaryResult {
  sessionId: TrainingSessionId;
  characterId: string | null;
  trainingMode: TrainingMode;
  status: string;
  roundNo: number;
  totalRounds: number;
  runtimeState: TrainingRuntimeState;
  progressAnchor: TrainingProgressAnchor;
  resumableScenario: TrainingScenario | null;
  scenarioCandidates: TrainingScenario[];
  canResume: boolean;
  isCompleted: boolean;
  createdAt: string | null;
  updatedAt: string | null;
  endTime: string | null;
}

export interface TrainingReportResult {
  sessionId: TrainingSessionId;
  characterId: string | null;
  status: string;
  rounds: number;
  kStateFinal: Record<string, number>;
  sStateFinal: Record<string, number>;
  improvement: number;
  playerProfile: TrainingPlayerProfile | null;
  runtimeState: TrainingRuntimeState | null;
  ending: Record<string, unknown> | null;
  summary: TrainingReportSummary | null;
  abilityRadar: TrainingReportMetric[];
  stateRadar: TrainingReportMetric[];
  growthCurve: TrainingReportCurvePoint[];
  history: TrainingReportHistoryItem[];
}

export interface TrainingDiagnosticsResult {
  sessionId: TrainingSessionId;
  characterId: string | null;
  status: string;
  roundNo: number;
  playerProfile: TrainingPlayerProfile | null;
  runtimeState: TrainingRuntimeState | null;
  summary: TrainingDiagnosticsSummary | null;
  recommendationLogs: TrainingRecommendationLog[];
  auditEvents: TrainingAuditEvent[];
  ktObservations: TrainingKtObservation[];
}
