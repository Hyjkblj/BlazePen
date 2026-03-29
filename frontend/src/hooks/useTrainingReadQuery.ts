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

interface TrainingReadQueryState<TData> {
  requestKey: string | null;
  sessionId: string | null;
  data: TData | null;
  status: TrainingReadQueryStatus;
  errorMessage: string | null;
  errorCode: string | null;
}

const createTrainingReadQueryState = <TData,>(): TrainingReadQueryState<TData> => ({
  requestKey: null,
  sessionId: null,
  data: null,
  status: 'idle',
  errorMessage: null,
  errorCode: null,
});

export function useTrainingReadQuery<TData>({
  explicitSessionId,
  fetcher,
  fallbackErrorMessage,
}: UseTrainingReadQueryOptions<TData>): UseTrainingReadQueryResult<TData> {
  const { state, clearActiveSession } = useTrainingFlow();
  const sessionTarget = useTrainingSessionReadTarget(explicitSessionId, {
    allowResumeTargetFallback: false,
  });
  const [queryState, setQueryState] = useState<TrainingReadQueryState<TData>>(
    createTrainingReadQueryState
  );
  const [reloadNonce, setReloadNonce] = useState(0);
  const requestIdRef = useRef(0);
  const activeSessionRef = useRef(state.activeSession);
  const queryStateRef = useRef(queryState);

  useEffect(() => {
    activeSessionRef.current = state.activeSession;
  }, [state.activeSession]);

  useEffect(() => {
    queryStateRef.current = queryState;
  }, [queryState]);
  const requestKey = sessionTarget.sessionId ? `${sessionTarget.sessionId}:${reloadNonce}` : null;

  useEffect(() => {
    if (!sessionTarget.sessionId) {
      return;
    }

    const currentSessionId = sessionTarget.sessionId;
    const currentRequestKey = `${currentSessionId}:${reloadNonce}`;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    let isActive = true;

    void fetcher(currentSessionId)
      .then((nextData) => {
        if (!isActive || requestIdRef.current !== requestId) {
          return;
        }

        setQueryState({
          requestKey: currentRequestKey,
          sessionId: currentSessionId,
          data: nextData,
          status: 'ready',
          errorMessage: null,
          errorCode: null,
        });
      })
      .catch((error: unknown) => {
        if (!isActive || requestIdRef.current !== requestId) {
          return;
        }

        const hasCurrentSessionData =
          queryStateRef.current.sessionId === currentSessionId &&
          queryStateRef.current.data !== null;
        const failureState = resolveTrainingReadFailureState({
          error,
          fallbackMessage: fallbackErrorMessage,
          hasCurrentSessionData,
        });

        if (failureState.shouldClearRecoveryArtifacts) {
          clearTrainingSessionRecoveryArtifacts({
            invalidSessionId: currentSessionId,
            activeSession: activeSessionRef.current,
            clearActiveSession,
          });
        }

        setQueryState((current) => ({
          requestKey: currentRequestKey,
          sessionId: failureState.shouldClearRecoveryArtifacts ? null : currentSessionId,
          data:
            failureState.shouldClearData || current.sessionId !== currentSessionId
              ? null
              : current.data,
          status: 'error',
          errorMessage: failureState.errorMessage,
          errorCode: failureState.shouldClearRecoveryArtifacts ? null : failureState.errorCode,
        }));
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

  const hasTerminalErrorWithoutSession =
    queryState.sessionId === null && queryState.status === 'error';
  const hasCurrentSessionState =
    sessionTarget.sessionId !== null && queryState.sessionId === sessionTarget.sessionId;
  const hasSettledStateForCurrentRequest = requestKey !== null && queryState.requestKey === requestKey;
  const hasTerminalErrorForCurrentRequest =
    hasSettledStateForCurrentRequest && queryState.sessionId === null && queryState.status === 'error';
  const data = hasCurrentSessionState ? queryState.data : null;
  const status =
    sessionTarget.sessionId === null
      ? hasTerminalErrorWithoutSession
        ? 'error'
        : 'idle'
      : !hasSettledStateForCurrentRequest
        ? 'loading'
        : hasCurrentSessionState || hasTerminalErrorForCurrentRequest
        ? queryState.status
        : 'loading';
  const errorMessage =
    sessionTarget.sessionId === null
      ? hasTerminalErrorWithoutSession
        ? queryState.errorMessage
        : null
      : !hasSettledStateForCurrentRequest
        ? null
      : hasCurrentSessionState || hasTerminalErrorForCurrentRequest
        ? queryState.errorMessage
        : null;
  const errorCode =
    sessionTarget.sessionId !== null && hasSettledStateForCurrentRequest && hasCurrentSessionState
      ? queryState.errorCode
      : null;

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
