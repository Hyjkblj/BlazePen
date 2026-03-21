import { useCallback, useEffect, useRef, useState } from 'react';
import { useTrainingFlow } from '@/contexts';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import {
  useTrainingSessionReadTarget,
  type TrainingSessionReadTarget,
} from './useTrainingSessionReadTarget';
import {
  clearTrainingSessionRecoveryArtifacts,
  isTerminalTrainingSessionRecoveryError,
} from './trainingSessionRecovery';

export type TrainingReadQueryStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface UseTrainingReadQueryOptions<TData> {
  explicitSessionId?: string | null;
  fetcher: (sessionId: string) => Promise<TData>;
  fallbackErrorMessage: string;
}

export interface UseTrainingReadQueryResult<TData> {
  data: TData | null;
  status: TrainingReadQueryStatus;
  errorMessage: string | null;
  sessionTarget: TrainingSessionReadTarget;
  reload: () => void;
}

const getTrainingReadErrorMessage = (error: unknown, fallbackMessage: string): string => {
  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '训练会话不存在，请返回训练主页重新开始。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '训练会话恢复状态损坏，当前结果无法读取。';
  }

  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '训练结果读取超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练结果服务暂时不可用，请稍后重试。';
  }

  return getServiceErrorMessage(error, fallbackMessage);
};

export function useTrainingReadQuery<TData>({
  explicitSessionId,
  fetcher,
  fallbackErrorMessage,
}: UseTrainingReadQueryOptions<TData>): UseTrainingReadQueryResult<TData> {
  const { state, clearActiveSession } = useTrainingFlow();
  const sessionTarget = useTrainingSessionReadTarget(explicitSessionId);
  const [data, setData] = useState<TData | null>(null);
  const [status, setStatus] = useState<TrainingReadQueryStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const requestIdRef = useRef(0);
  const lastSessionIdRef = useRef<string | null>(null);
  const activeSessionRef = useRef(state.activeSession);

  useEffect(() => {
    activeSessionRef.current = state.activeSession;
  }, [state.activeSession]);

  useEffect(() => {
    if (!sessionTarget.sessionId) {
      lastSessionIdRef.current = null;
      setData(null);
      setStatus((currentStatus) => (currentStatus === 'error' ? currentStatus : 'idle'));
      return;
    }

    if (lastSessionIdRef.current !== sessionTarget.sessionId) {
      setData(null);
    }
    lastSessionIdRef.current = sessionTarget.sessionId;

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    let isActive = true;

    setStatus('loading');
    setErrorMessage(null);

    void fetcher(sessionTarget.sessionId)
      .then((nextData) => {
        if (!isActive || requestIdRef.current !== requestId) {
          return;
        }

        setData(nextData);
        setStatus('ready');
      })
      .catch((error: unknown) => {
        if (!isActive || requestIdRef.current !== requestId) {
          return;
        }

        if (isTerminalTrainingSessionRecoveryError(error)) {
          clearTrainingSessionRecoveryArtifacts({
            invalidSessionId: sessionTarget.sessionId,
            activeSession: activeSessionRef.current,
            clearActiveSession,
          });
        }

        setData(null);
        setErrorMessage(getTrainingReadErrorMessage(error, fallbackErrorMessage));
        setStatus('error');
      });

    return () => {
      isActive = false;
    };
  }, [
    clearActiveSession,
    fallbackErrorMessage,
    fetcher,
    reloadNonce,
    sessionTarget.sessionId,
  ]);

  const reload = useCallback(() => {
    setReloadNonce((current) => current + 1);
  }, []);

  return {
    data,
    status,
    errorMessage,
    sessionTarget,
    reload,
  };
}
