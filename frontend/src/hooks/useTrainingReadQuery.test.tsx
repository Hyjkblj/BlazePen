// @vitest-environment jsdom

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { renderHook, waitFor } from '@testing-library/react';
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
    expect(result.current.query.sessionTarget.sessionId).toBeNull();
    expect(result.current.activeSession).toBeNull();
    expect(readTrainingResumeTarget()).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
