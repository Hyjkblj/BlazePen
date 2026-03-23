import { useCallback, useMemo } from 'react';
import type { ActiveTrainingSessionState } from '@/contexts';
import type { TrainingResumeTarget } from '@/storage/trainingSessionCache';
import type {
  TrainingMode,
  TrainingProgressAnchor,
  TrainingRoundSubmitResult,
  TrainingRuntimeState,
  TrainingScenario,
  TrainingScenarioNextResult,
  TrainingSessionSummaryResult,
} from '@/types/training';
import {
  resolveTrainingSessionReadTarget,
  type TrainingSessionReadTargetSource,
} from './useTrainingSessionReadTarget';

export interface TrainingSessionViewState {
  sessionId: string;
  trainingMode: TrainingMode;
  characterId: string | null;
  status: string;
  roundNo: number;
  totalRounds: number | null;
  runtimeState: TrainingRuntimeState;
  currentScenario: TrainingScenario | null;
  scenarioCandidates: TrainingScenario[];
  progressAnchor: TrainingProgressAnchor | null;
  canResume: boolean;
  isCompleted: boolean;
  createdAt: string | null;
  updatedAt: string | null;
  endTime: string | null;
}

export type TrainingSessionRestoreSource =
  | 'session-view'
  | TrainingSessionReadTargetSource;

export interface TrainingSessionRestoreIdentity {
  sessionId: string | null;
  trainingMode: TrainingMode | null;
  characterId: string | null;
  source: TrainingSessionRestoreSource;
}

export interface TrainingSessionWorkspaceSeed {
  currentSessionId: string | null;
  currentSessionSource: TrainingSessionRestoreSource;
  autoRestoreSessionId: string | null;
  preferredTrainingMode: TrainingMode | null;
  preferredCharacterId: string | null;
}

export interface UseTrainingSessionViewModelOptions {
  sessionView: TrainingSessionViewState | null;
  activeSession: ActiveTrainingSessionState | null;
  resumeTarget: TrainingResumeTarget | null;
}

export interface UseTrainingSessionViewModelResult
  extends TrainingSessionWorkspaceSeed {
  resolveRestoreIdentity: (
    sessionId?: string | null
  ) => TrainingSessionRestoreIdentity;
}

export const buildTrainingProgressAnchor = (
  totalRounds: number | null,
  roundNo: number,
  isCompleted: boolean
): TrainingProgressAnchor | null => {
  if (!totalRounds || totalRounds <= 0) {
    return null;
  }

  const completedRounds = isCompleted ? totalRounds : Math.min(roundNo, totalRounds);
  const remainingRounds = Math.max(totalRounds - completedRounds, 0);

  return {
    roundNo,
    totalRounds,
    completedRounds,
    remainingRounds,
    progressPercent: (completedRounds / totalRounds) * 100,
    nextRoundNo: remainingRounds > 0 ? roundNo + 1 : null,
  };
};

export const buildTrainingSessionViewFromSummary = (
  summaryResult: TrainingSessionSummaryResult
): TrainingSessionViewState => ({
  sessionId: summaryResult.sessionId,
  trainingMode: summaryResult.trainingMode,
  characterId: summaryResult.characterId,
  status: summaryResult.status,
  roundNo: summaryResult.roundNo,
  totalRounds: summaryResult.totalRounds,
  runtimeState: summaryResult.runtimeState,
  currentScenario: summaryResult.resumableScenario,
  scenarioCandidates: summaryResult.scenarioCandidates,
  progressAnchor: summaryResult.progressAnchor,
  canResume: summaryResult.canResume,
  isCompleted: summaryResult.isCompleted,
  createdAt: summaryResult.createdAt,
  updatedAt: summaryResult.updatedAt,
  endTime: summaryResult.endTime,
});

export const buildTrainingSessionViewFromInit = (
  sessionResult: {
    sessionId: string;
    trainingMode: TrainingMode;
    status: string;
    roundNo: number;
    runtimeState: TrainingRuntimeState;
    nextScenario: TrainingScenario | null;
    scenarioCandidates: TrainingScenario[];
  },
  characterId: string | null
): TrainingSessionViewState => ({
  sessionId: sessionResult.sessionId,
  trainingMode: sessionResult.trainingMode,
  characterId,
  status: sessionResult.status,
  roundNo: sessionResult.roundNo,
  totalRounds: null,
  runtimeState: sessionResult.runtimeState,
  currentScenario: sessionResult.nextScenario,
  scenarioCandidates: sessionResult.scenarioCandidates,
  progressAnchor: null,
  canResume: sessionResult.nextScenario !== null,
  isCompleted: false,
  createdAt: null,
  updatedAt: null,
  endTime: null,
});

export const buildTrainingSessionViewFromNext = (
  currentSession: TrainingSessionViewState,
  nextScenarioResult: TrainingScenarioNextResult
): TrainingSessionViewState => ({
  ...currentSession,
  status: nextScenarioResult.status,
  roundNo: nextScenarioResult.roundNo,
  runtimeState: nextScenarioResult.runtimeState,
  currentScenario: nextScenarioResult.scenario,
  scenarioCandidates: nextScenarioResult.scenarioCandidates,
  progressAnchor: buildTrainingProgressAnchor(
    currentSession.totalRounds,
    nextScenarioResult.roundNo,
    false
  ),
  canResume: nextScenarioResult.scenario !== null,
  isCompleted: nextScenarioResult.status === 'completed',
  updatedAt: null,
});

export const buildCompletedTrainingSessionView = (
  currentSession: TrainingSessionViewState,
  submitResult: TrainingRoundSubmitResult
): TrainingSessionViewState => ({
  ...currentSession,
  status: 'completed',
  roundNo: submitResult.roundNo,
  runtimeState: submitResult.runtimeState,
  currentScenario: null,
  scenarioCandidates: [],
  progressAnchor: buildTrainingProgressAnchor(
    currentSession.totalRounds,
    submitResult.roundNo,
    true
  ),
  canResume: false,
  isCompleted: true,
});

export const buildBlockedTrainingSessionView = (
  currentSession: TrainingSessionViewState,
  submitResult: TrainingRoundSubmitResult
): TrainingSessionViewState => ({
  ...currentSession,
  status: 'in_progress',
  roundNo: submitResult.roundNo,
  runtimeState: submitResult.runtimeState,
  currentScenario: null,
  scenarioCandidates: [],
  progressAnchor: buildTrainingProgressAnchor(
    currentSession.totalRounds,
    submitResult.roundNo,
    false
  ),
  canResume: true,
  isCompleted: false,
});

export const resolveTrainingSessionRestoreIdentity = ({
  explicitSessionId,
  sessionView,
  activeSession,
  resumeTarget,
}: {
  explicitSessionId?: string | null;
  sessionView: TrainingSessionViewState | null;
  activeSession: ActiveTrainingSessionState | null;
  resumeTarget: TrainingResumeTarget | null;
}): TrainingSessionRestoreIdentity => {
  if (
    explicitSessionId &&
    sessionView?.sessionId === explicitSessionId
  ) {
    return {
      sessionId: explicitSessionId,
      trainingMode: sessionView.trainingMode,
      characterId: sessionView.characterId,
      source: 'session-view',
    };
  }

  const sessionTarget = resolveTrainingSessionReadTarget({
    explicitSessionId,
    activeSession,
    resumeTarget,
  });

  return {
    sessionId: sessionTarget.sessionId,
    trainingMode: sessionTarget.trainingMode,
    characterId: sessionTarget.characterId,
    source: sessionTarget.source,
  };
};

export const resolveTrainingSessionWorkspaceSeed = ({
  sessionView,
  activeSession,
  resumeTarget,
}: UseTrainingSessionViewModelOptions): TrainingSessionWorkspaceSeed => {
  if (sessionView) {
    return {
      currentSessionId: sessionView.sessionId,
      currentSessionSource: 'session-view',
      autoRestoreSessionId: null,
      preferredTrainingMode: sessionView.trainingMode,
      preferredCharacterId: sessionView.characterId,
    };
  }

  const sessionTarget = resolveTrainingSessionReadTarget({
    activeSession,
    resumeTarget,
    allowResumeTargetFallback: false,
  });

  return {
    currentSessionId: sessionTarget.sessionId,
    currentSessionSource: sessionTarget.source,
    autoRestoreSessionId: sessionTarget.sessionId,
    preferredTrainingMode: sessionTarget.trainingMode ?? resumeTarget?.trainingMode ?? null,
    preferredCharacterId: sessionTarget.characterId ?? resumeTarget?.characterId ?? null,
  };
};

export function useTrainingSessionViewModel({
  sessionView,
  activeSession,
  resumeTarget,
}: UseTrainingSessionViewModelOptions): UseTrainingSessionViewModelResult {
  const workspaceSeed = useMemo(
    () =>
      resolveTrainingSessionWorkspaceSeed({
        sessionView,
        activeSession,
        resumeTarget,
      }),
    [activeSession, resumeTarget, sessionView]
  );

  const resolveRestoreIdentity = useCallback(
    (sessionId?: string | null) =>
      resolveTrainingSessionRestoreIdentity({
        explicitSessionId: sessionId,
        sessionView,
        activeSession,
        resumeTarget,
      }),
    [activeSession, resumeTarget, sessionView]
  );

  return useMemo(
    () => ({
      ...workspaceSeed,
      resolveRestoreIdentity,
    }),
    [resolveRestoreIdentity, workspaceSeed]
  );
}
