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
  briefing: string;
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
  status: string;
  roundNo: number;
  totalRounds: number;
  runtimeState: TrainingRuntimeState;
}
