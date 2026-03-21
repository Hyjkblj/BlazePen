import { useCallback, useState } from 'react';
import { useTrainingFlow } from '@/contexts';
import { getTrainingSessionSummary, initTraining } from '@/services/trainingApi';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
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
  isTerminalTrainingSessionRecoveryError,
} from './trainingSessionRecovery';

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

interface RestoreSessionIdentity {
  sessionId: string | null | undefined;
  characterId?: string | null | undefined;
}

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

const normalizeSessionId = (value: string | null | undefined): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const resolveRestoreSessionTarget = (
  options: RestoreTrainingSessionOptions,
  activeSession: RestoreSessionIdentity | null,
  resumeTarget: RestoreSessionIdentity | null
): {
  sessionId: string | null;
  characterId: string | null;
} => {
  const explicitSessionId = normalizeSessionId(options.sessionId ?? null);
  const explicitCharacterId =
    options.characterId === undefined ? undefined : normalizeCharacterId(options.characterId);

  if (explicitSessionId) {
    const matchedCharacterId =
      normalizeSessionId(activeSession?.sessionId) === explicitSessionId
        ? normalizeCharacterId(activeSession?.characterId ?? null)
        : normalizeSessionId(resumeTarget?.sessionId) === explicitSessionId
          ? normalizeCharacterId(resumeTarget?.characterId ?? null)
          : null;

    return {
      sessionId: explicitSessionId,
      characterId: explicitCharacterId ?? matchedCharacterId ?? null,
    };
  }

  const activeSessionId = normalizeSessionId(activeSession?.sessionId ?? null);
  if (activeSessionId) {
    return {
      sessionId: activeSessionId,
      characterId: explicitCharacterId ?? normalizeCharacterId(activeSession?.characterId ?? null),
    };
  }

  const cachedSessionId = normalizeSessionId(resumeTarget?.sessionId ?? null);
  if (cachedSessionId) {
    return {
      sessionId: cachedSessionId,
      characterId: explicitCharacterId ?? normalizeCharacterId(resumeTarget?.characterId ?? null),
    };
  }

  return {
    sessionId: null,
    characterId: explicitCharacterId ?? null,
  };
};

const getRestoreErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '训练会话不存在，已清理本地恢复入口。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '训练会话恢复状态损坏，已清理本地恢复入口。';
  }

  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '训练恢复超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练恢复服务暂时不可用，请稍后重试。';
  }

  return getServiceErrorMessage(error, '恢复训练会话失败。');
};

const getStartErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '训练初始化超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练初始化服务暂时不可用，请稍后重试。';
  }

  return getServiceErrorMessage(error, '启动训练失败。');
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

      setStatus('starting');
      setErrorMessage(null);

      try {
        const initResult = await initTraining(params);
        setActiveSession({
          sessionId: initResult.sessionId,
          trainingMode: initResult.trainingMode,
          characterId: normalizedCharacterId,
          status: initResult.status,
          roundNo: initResult.roundNo,
          totalRounds: null,
          runtimeState: initResult.runtimeState,
        });
        persistTrainingResumeTarget({
          sessionId: initResult.sessionId,
          trainingMode: initResult.trainingMode,
          characterId: normalizedCharacterId,
          status: initResult.status,
        });
        refreshResumeTarget();
        setStatus('ready');
        return initResult;
      } catch (error: unknown) {
        setErrorMessage(getStartErrorMessage(error));
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
      const { sessionId, characterId } = resolveRestoreSessionTarget(
        options,
        state.activeSession,
        cachedTarget
      );

      if (!sessionId) {
        setErrorMessage('当前没有可恢复的训练会话。');
        setStatus('error');
        return null;
      }

      setStatus('restoring');
      setErrorMessage(null);

      try {
        const summaryResult = await getTrainingSessionSummary(sessionId);
        setActiveSession({
          sessionId: summaryResult.sessionId,
          trainingMode: summaryResult.trainingMode,
          characterId,
          status: summaryResult.status,
          roundNo: summaryResult.roundNo,
          totalRounds: summaryResult.totalRounds,
          runtimeState: summaryResult.runtimeState,
        });
        persistTrainingResumeTarget({
          sessionId: summaryResult.sessionId,
          trainingMode: summaryResult.trainingMode,
          characterId,
          status: summaryResult.status,
        });
        refreshResumeTarget();
        setStatus('ready');
        return summaryResult;
      } catch (error: unknown) {
        if (isTerminalTrainingSessionRecoveryError(error)) {
          clearTrainingSessionRecoveryArtifacts({
            invalidSessionId: sessionId,
            activeSession: state.activeSession,
            clearActiveSession,
          });
          setResumeTarget(refreshResumeTarget());
        }

        setErrorMessage(getRestoreErrorMessage(error));
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
