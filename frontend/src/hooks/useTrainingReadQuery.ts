import { useCallback, useEffect, useRef, useState } from 'react';
import { useTrainingFlow } from '@/contexts';
import {
  useTrainingSessionReadTarget,
  type TrainingSessionReadTarget,
} from './useTrainingSessionReadTarget';
import { clearTrainingSessionRecoveryArtifacts } from './trainingSessionRecovery';
import { resolveTrainingReadFailureState } from './trainingReadQueryExecutor';

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
  errorCode: string | null;
  sessionTarget: TrainingSessionReadTarget;
  hasStaleData: boolean;
  reload: () => void;
}

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
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const requestIdRef = useRef(0);
  const lastSessionIdRef = useRef<string | null>(null);
  const activeSessionRef = useRef(state.activeSession);
  const dataRef = useRef<TData | null>(null);

  useEffect(() => {
    activeSessionRef.current = state.activeSession;
  }, [state.activeSession]);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  useEffect(() => {
    if (!sessionTarget.sessionId) {
      lastSessionIdRef.current = null;
      setData(null);
      setErrorCode(null);
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
    setErrorCode(null);

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

        const hasCurrentSessionData =
          lastSessionIdRef.current === sessionTarget.sessionId && dataRef.current !== null;
        const failureState = resolveTrainingReadFailureState({
          error,
          fallbackMessage: fallbackErrorMessage,
          hasCurrentSessionData,
        });

        if (failureState.shouldClearRecoveryArtifacts) {
          clearTrainingSessionRecoveryArtifacts({
            invalidSessionId: sessionTarget.sessionId,
            activeSession: activeSessionRef.current,
            clearActiveSession,
          });
        }

        setErrorCode(failureState.errorCode);
        if (failureState.shouldClearData) {
          setData(null);
        }
        setErrorMessage(failureState.errorMessage);
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
    errorCode,
    sessionTarget,
    hasStaleData: status === 'error' && data !== null,
    reload,
  };
}
