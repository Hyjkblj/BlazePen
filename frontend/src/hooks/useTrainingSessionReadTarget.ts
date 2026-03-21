import { useTrainingFlow } from '@/contexts';
import type { ActiveTrainingSessionState } from '@/contexts';
import {
  readTrainingResumeTarget,
  type TrainingResumeTarget,
} from '@/storage/trainingSessionCache';
import type { TrainingMode } from '@/types/training';

export type TrainingSessionReadTargetSource =
  | 'explicit'
  | 'active-session'
  | 'resume-target'
  | 'none';

export interface TrainingSessionReadTarget {
  sessionId: string | null;
  trainingMode: TrainingMode | null;
  characterId: string | null;
  status: string | null;
  source: TrainingSessionReadTargetSource;
}

const normalizeSessionId = (value: string | null | undefined): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const normalizeCharacterId = (value: string | null | undefined): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const buildTarget = ({
  sessionId,
  trainingMode,
  characterId,
  status,
  source,
}: TrainingSessionReadTarget): TrainingSessionReadTarget => ({
  sessionId,
  trainingMode,
  characterId,
  status,
  source,
});

const resolveExplicitTarget = (
  explicitSessionId: string,
  activeSession: ActiveTrainingSessionState | null,
  resumeTarget: TrainingResumeTarget | null
): TrainingSessionReadTarget => {
  if (activeSession?.sessionId === explicitSessionId) {
    return buildTarget({
      sessionId: explicitSessionId,
      trainingMode: activeSession.trainingMode,
      characterId: activeSession.characterId,
      status: activeSession.status,
      source: 'explicit',
    });
  }

  if (resumeTarget?.sessionId === explicitSessionId) {
    return buildTarget({
      sessionId: explicitSessionId,
      trainingMode: resumeTarget.trainingMode,
      characterId: resumeTarget.characterId,
      status: resumeTarget.status,
      source: 'explicit',
    });
  }

  return buildTarget({
    sessionId: explicitSessionId,
    trainingMode: null,
    characterId: null,
    status: null,
    source: 'explicit',
  });
};

export const resolveTrainingSessionReadTarget = ({
  explicitSessionId,
  activeSession,
  resumeTarget,
}: {
  explicitSessionId?: string | null;
  activeSession: ActiveTrainingSessionState | null;
  resumeTarget: TrainingResumeTarget | null;
}): TrainingSessionReadTarget => {
  const normalizedExplicitSessionId = normalizeSessionId(explicitSessionId);
  if (normalizedExplicitSessionId) {
    return resolveExplicitTarget(normalizedExplicitSessionId, activeSession, resumeTarget);
  }

  const activeSessionId = normalizeSessionId(activeSession?.sessionId);
  if (activeSessionId) {
    return buildTarget({
      sessionId: activeSessionId,
      trainingMode: activeSession?.trainingMode ?? null,
      characterId: normalizeCharacterId(activeSession?.characterId ?? null),
      status: activeSession?.status ?? null,
      source: 'active-session',
    });
  }

  const resumeTargetSessionId = normalizeSessionId(resumeTarget?.sessionId);
  if (resumeTargetSessionId) {
    return buildTarget({
      sessionId: resumeTargetSessionId,
      trainingMode: resumeTarget?.trainingMode ?? null,
      characterId: normalizeCharacterId(resumeTarget?.characterId ?? null),
      status: resumeTarget?.status ?? null,
      source: 'resume-target',
    });
  }

  return buildTarget({
    sessionId: null,
    trainingMode: null,
    characterId: null,
    status: null,
    source: 'none',
  });
};

export function useTrainingSessionReadTarget(
  explicitSessionId?: string | null
): TrainingSessionReadTarget {
  const { state } = useTrainingFlow();
  const resumeTarget = readTrainingResumeTarget();

  return resolveTrainingSessionReadTarget({
    explicitSessionId,
    activeSession: state.activeSession,
    resumeTarget,
  });
}
