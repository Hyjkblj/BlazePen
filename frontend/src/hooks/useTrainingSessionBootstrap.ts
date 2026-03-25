import { useCallback, useState } from 'react';
import { useTrainingFlow } from '@/contexts';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { getTrainingSessionSummary, initTraining } from '@/services/trainingApi';
import {
  clearTrainingResumeTarget,
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
  type TrainingResumeTarget,
} from '@/storage/trainingSessionCache';
import type {
  TrainingInitResult,
  TrainingMode,
  TrainingSessionInitParams,
  TrainingSessionSummaryResult,
} from '@/types/training';
import {
  clearTrainingSessionRecoveryArtifacts,
} from './trainingSessionRecovery';
import {
  getTrainingStartErrorMessage,
  resolveTrainingRestoreFailureState,
} from './trainingSessionBootstrapExecutor';
import {
  resolveTrainingSessionReadTarget,
  type TrainingSessionReadTargetSource,
} from './useTrainingSessionReadTarget';

export type TrainingBootstrapStatus = 'idle' | 'restoring' | 'starting' | 'ready' | 'error';

export interface RestoreTrainingSessionOptions {
  sessionId?: string | null;
  trainingMode?: TrainingMode | null;
  characterId?: string | null;
}

export interface UseTrainingSessionBootstrapResult {
  activeSession: ReturnType<typeof useTrainingFlow>['state']['activeSession'];
  status: TrainingBootstrapStatus;
  errorMessage: string | null;
  resumeTarget: TrainingResumeTarget | null;
  hasResumeTarget: boolean;
  startTrainingSession: (
    params: TrainingSessionInitParams
  ) => Promise<TrainingInitResult | null>;
  restoreSession: (
    options?: RestoreTrainingSessionOptions
  ) => Promise<TrainingSessionSummaryResult | null>;
  clearTrainingSession: () => void;
  dismissError: () => void;
}

type TrainingRestoreTelemetrySource =
  | 'explicit'
  | 'active-session'
  | 'resume-target'
  | 'unknown';

const normalizeCharacterId = (value: string | number | null | undefined): string | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }

  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const toRestoreTelemetrySource = (
  source: TrainingSessionReadTargetSource
): TrainingRestoreTelemetrySource => {
  switch (source) {
    case 'explicit':
      return 'explicit';
    case 'active-session':
      return 'active-session';
    case 'resume-target':
      return 'resume-target';
    default:
      return 'unknown';
  }
};

export function useTrainingSessionBootstrap(): UseTrainingSessionBootstrapResult {
  const { state, clearActiveSession, setActiveSession } = useTrainingFlow();
  const [status, setStatus] = useState<TrainingBootstrapStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [resumeTarget, setResumeTarget] = useState<TrainingResumeTarget | null>(() =>
    readTrainingResumeTarget()
  );

  const refreshResumeTarget = useCallback(() => {
    const nextTarget = readTrainingResumeTarget();
    setResumeTarget(nextTarget);
    return nextTarget;
  }, []);

  const clearTrainingSession = useCallback(() => {
    clearActiveSession();
    clearTrainingResumeTarget();
    setResumeTarget(null);
    setErrorMessage(null);
    setStatus('idle');
  }, [clearActiveSession]);

  const dismissError = useCallback(() => {
    setErrorMessage(null);
    if (status === 'error') {
      setStatus('idle');
    }
  }, [status]);

  const startTrainingSession = useCallback(
    async (params: TrainingSessionInitParams): Promise<TrainingInitResult | null> => {
      const normalizedCharacterId = normalizeCharacterId(params.characterId ?? null);
      const initTelemetryMetadata = {
        trainingMode: params.trainingMode,
        hasCharacterId: normalizedCharacterId !== null,
        hasPlayerProfile: params.playerProfile !== null,
      };

      setStatus('starting');
      setErrorMessage(null);

      try {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.init',
          status: 'requested',
          metadata: initTelemetryMetadata,
        });
        const initResult = await initTraining(params);
        const resolvedCharacterId = normalizeCharacterId(
          initResult.characterId ?? normalizedCharacterId
        );
        setActiveSession({
          sessionId: initResult.sessionId,
          trainingMode: initResult.trainingMode,
          characterId: resolvedCharacterId,
          status: initResult.status,
          roundNo: initResult.roundNo,
          totalRounds: null,
          runtimeState: initResult.runtimeState,
        });
        persistTrainingResumeTarget({
          sessionId: initResult.sessionId,
          trainingMode: initResult.trainingMode,
          characterId: resolvedCharacterId,
          status: initResult.status,
        });
        refreshResumeTarget();
        setStatus('ready');
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.init',
          status: 'succeeded',
          metadata: {
            ...initTelemetryMetadata,
            hasCharacterId: resolvedCharacterId !== null,
            sessionId: initResult.sessionId,
            status: initResult.status,
            roundNo: initResult.roundNo,
          },
        });
        return initResult;
      } catch (error: unknown) {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.init',
          status: 'failed',
          metadata: initTelemetryMetadata,
          cause: error,
        });
        setErrorMessage(getTrainingStartErrorMessage(error));
        setStatus('error');
        return null;
      }
    },
    [refreshResumeTarget, setActiveSession]
  );

  const restoreSession = useCallback(
    async (
      options: RestoreTrainingSessionOptions = {}
    ): Promise<TrainingSessionSummaryResult | null> => {
      const cachedTarget = readTrainingResumeTarget();
      const restoreTarget = resolveTrainingSessionReadTarget({
        explicitSessionId: options.sessionId ?? null,
        activeSession: state.activeSession,
        resumeTarget: cachedTarget,
        allowResumeTargetFallback: false,
      });
      const explicitCharacterId =
        options.characterId === undefined ? undefined : normalizeCharacterId(options.characterId);
      const sessionId = restoreTarget.sessionId;
      const characterIdHint = explicitCharacterId ?? restoreTarget.characterId;

      if (!sessionId) {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.restore',
          status: 'failed',
          metadata: {
            sessionId: null,
            restoreSource: toRestoreTelemetrySource(restoreTarget.source),
            failureStage: 'missing-session',
          },
        });
        setErrorMessage('当前没有可恢复的训练会话。');
        setStatus('error');
        return null;
      }

      const restoreTelemetryMetadata = {
        sessionId,
        restoreSource: toRestoreTelemetrySource(restoreTarget.source),
        hasCharacterId: characterIdHint !== null,
      };

      setStatus('restoring');
      setErrorMessage(null);

      try {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.restore',
          status: 'requested',
          metadata: restoreTelemetryMetadata,
        });
        const summaryResult = await getTrainingSessionSummary(sessionId);
        const resolvedCharacterId = normalizeCharacterId(summaryResult.characterId);
        setActiveSession({
          sessionId: summaryResult.sessionId,
          trainingMode: summaryResult.trainingMode,
          characterId: resolvedCharacterId,
          status: summaryResult.status,
          roundNo: summaryResult.roundNo,
          totalRounds: summaryResult.totalRounds,
          runtimeState: summaryResult.runtimeState,
        });
        persistTrainingResumeTarget({
          sessionId: summaryResult.sessionId,
          trainingMode: summaryResult.trainingMode,
          characterId: resolvedCharacterId,
          status: summaryResult.status,
        });
        refreshResumeTarget();
        setStatus('ready');
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.restore',
          status: 'succeeded',
          metadata: {
            ...restoreTelemetryMetadata,
            hasCharacterId: resolvedCharacterId !== null,
            status: summaryResult.status,
            roundNo: summaryResult.roundNo,
            isCompleted: summaryResult.isCompleted,
          },
        });
        return summaryResult;
      } catch (error: unknown) {
        const failureState = resolveTrainingRestoreFailureState(error);
        if (failureState.shouldClearRecoveryArtifacts) {
          clearTrainingSessionRecoveryArtifacts({
            invalidSessionId: sessionId,
            activeSession: state.activeSession,
            clearActiveSession,
          });
          setResumeTarget(refreshResumeTarget());
        }

        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.restore',
          status: 'failed',
          metadata: restoreTelemetryMetadata,
          cause: error,
        });
        setErrorMessage(failureState.errorMessage);
        setStatus('error');
        return null;
      }
    },
    [clearActiveSession, refreshResumeTarget, setActiveSession, state.activeSession]
  );

  return {
    activeSession: state.activeSession,
    status,
    errorMessage,
    resumeTarget,
    hasResumeTarget: Boolean(resumeTarget?.sessionId || state.activeSession?.sessionId),
    startTrainingSession,
    restoreSession,
    clearTrainingSession,
    dismissError,
  };
}
