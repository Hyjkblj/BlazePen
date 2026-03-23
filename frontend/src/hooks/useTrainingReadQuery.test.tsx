// @vitest-environment jsdom

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TrainingFlowProvider, useTrainingFlow, type ActiveTrainingSessionState } from '@/contexts';
import { ServiceError } from '@/services/serviceError';
import {
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';
import { useTrainingReadQuery } from './useTrainingReadQuery';

const createRuntimeState = (sceneId: string, roundNo: number) => ({
  currentRoundNo: roundNo,
  currentSceneId: sceneId,
  kState: {
    K1: 0.45,
  },
  sState: {
    source_safety: 0.86,
  },
  runtimeFlags: {
    panicTriggered: false,
    sourceExposed: false,
    editorLocked: false,
    highRiskPath: false,
  },
  stateBar: {
    editorTrust: 0.72,
    publicStability: 0.81,
    sourceSafety: 0.86,
  },
  playerProfile: null,
});

function TrainingFlowSeed({
  activeSession,
  children,
}: {
  activeSession: ActiveTrainingSessionState | null;
  children: ReactNode;
}) {
  const { setActiveSession } = useTrainingFlow();
  const [isReady, setReady] = useState(activeSession === null);
  const initializedRef = useRef(activeSession === null);

  useLayoutEffect(() => {
    if (initializedRef.current) {
      return;
    }

    initializedRef.current = true;
    if (activeSession) {
      setActiveSession(activeSession);
    }

    setReady(true);
  }, [activeSession, setActiveSession]);

  return isReady ? <>{children}</> : null;
}

function createWrapper(activeSession: ActiveTrainingSessionState | null) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <TrainingFlowProvider>
        <TrainingFlowSeed activeSession={activeSession}>{children}</TrainingFlowSeed>
      </TrainingFlowProvider>
    );
  };
}

describe('useTrainingReadQuery', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('clears invalid activeSession and resumeTarget on terminal recovery errors', async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
        status: 409,
        message: 'training session recovery state corrupted',
      })
    );

    persistTrainingResumeTarget({
      sessionId: 'training-session-broken',
      trainingMode: 'guided',
      status: 'in_progress',
    });

    const wrapper = createWrapper({
      sessionId: 'training-session-broken',
      trainingMode: 'guided',
      characterId: '42',
      status: 'in_progress',
      roundNo: 2,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-broken', 2),
    });

    const { result } = renderHook(
      () => {
        const query = useTrainingReadQuery({
          fetcher,
          fallbackErrorMessage: '读取失败。',
        });
        const trainingFlow = useTrainingFlow();

        return {
          query,
          activeSession: trainingFlow.state.activeSession,
        };
      },
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.query.status).toBe('error');
    });

    expect(result.current.query.errorMessage).toBe('训练会话恢复状态损坏，当前结果无法读取。');
    expect(result.current.query.errorCode).toBeNull();
    expect(result.current.query.sessionTarget.sessionId).toBeNull();
    expect(result.current.query.hasStaleData).toBe(false);
    expect(result.current.activeSession).toBeNull();
    expect(readTrainingResumeTarget()).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('keeps the last successful read model visible when a reload fails transiently', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ sessionId: 'training-session-1', score: 0.82 })
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          status: 504,
          message: 'training read timed out',
        })
      );

    const { result } = renderHook(
      () =>
        useTrainingReadQuery({
          explicitSessionId: 'training-session-1',
          fetcher,
          fallbackErrorMessage: '读取失败。',
        }),
      { wrapper: createWrapper(null) }
    );

    await waitFor(() => {
      expect(result.current.status).toBe('ready');
    });

    expect(result.current.data).toEqual({
      sessionId: 'training-session-1',
      score: 0.82,
    });

    act(() => {
      result.current.reload();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('error');
    });

    expect(result.current.errorCode).toBe('REQUEST_TIMEOUT');
    expect(result.current.errorMessage).toBe('训练结果读取超时，请重试。');
    expect(result.current.hasStaleData).toBe(true);
    expect(result.current.data).toEqual({
      sessionId: 'training-session-1',
      score: 0.82,
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('does not read from resumeTarget by default without explicit or active session', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-cached',
      trainingMode: 'guided',
      status: 'in_progress',
    });
    const fetcher = vi.fn().mockResolvedValueOnce({
      sessionId: 'training-session-cached',
      score: 0.66,
    });

    const { result } = renderHook(
      () =>
        useTrainingReadQuery({
          fetcher,
          fallbackErrorMessage: '读取失败。',
        }),
      { wrapper: createWrapper(null) }
    );

    await waitFor(() => {
      expect(result.current.status).toBe('idle');
    });

    expect(result.current.sessionTarget.sessionId).toBeNull();
    expect(result.current.sessionTarget.source).toBe('none');
    expect(fetcher).not.toHaveBeenCalled();
  });
});
