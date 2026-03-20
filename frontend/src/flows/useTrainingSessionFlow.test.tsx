// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { TrainingFlowProvider, useTrainingFlow } from '@/contexts';
import type { TrainingRuntimeState } from '@/types/training';
import { useTrainingSessionFlow } from './useTrainingSessionFlow';

const createRuntimeState = (): TrainingRuntimeState => ({
  currentRoundNo: 1,
  currentSceneId: 'scenario-1',
  kState: {
    K1: 0.5,
  },
  sState: {
    source_safety: 0.9,
  },
  runtimeFlags: {
    panicTriggered: false,
    sourceExposed: false,
    editorLocked: false,
    highRiskPath: false,
  },
  stateBar: {
    editorTrust: 0.8,
    publicStability: 0.6,
    sourceSafety: 0.9,
  },
  playerProfile: null,
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <TrainingFlowProvider>{children}</TrainingFlowProvider>
);

describe('useTrainingSessionFlow', () => {
  it('starts with no active training session', () => {
    const { result } = renderHook(() => useTrainingSessionFlow(), { wrapper });

    expect(result.current.activeSession).toBeNull();
    expect(result.current.hasActiveSession).toBe(false);
    expect(result.current.trainingModeLabel).toBeNull();
  });

  it('derives the active training session label and clears the session through the flow boundary', () => {
    const { result } = renderHook(
      () => ({
        flow: useTrainingSessionFlow(),
        trainingFlow: useTrainingFlow(),
      }),
      { wrapper }
    );

    act(() => {
      result.current.trainingFlow.setActiveSession({
        sessionId: 'session-1',
        trainingMode: 'self-paced',
        characterId: '12',
        status: 'active',
        roundNo: 1,
        totalRounds: 6,
        runtimeState: createRuntimeState(),
      });
    });

    expect(result.current.flow.hasActiveSession).toBe(true);
    expect(result.current.flow.trainingModeLabel).toBe('自主训练');
    expect(result.current.flow.activeSession).toMatchObject({
      sessionId: 'session-1',
      characterId: '12',
      totalRounds: 6,
    });

    act(() => {
      result.current.flow.clearTrainingSession();
    });

    expect(result.current.flow.activeSession).toBeNull();
    expect(result.current.flow.hasActiveSession).toBe(false);
  });

  it('syncs progress only for the currently active training session', () => {
    const { result } = renderHook(() => useTrainingFlow(), { wrapper });

    act(() => {
      result.current.setActiveSession({
        sessionId: 'session-1',
        trainingMode: 'guided',
        status: 'active',
        roundNo: 1,
        totalRounds: null,
        runtimeState: createRuntimeState(),
      });
    });

    act(() => {
      result.current.syncProgress({
        sessionId: 'session-2',
        status: 'completed',
        roundNo: 6,
        totalRounds: 6,
        runtimeState: {
          ...createRuntimeState(),
          currentRoundNo: 6,
        },
      });
    });

    expect(result.current.state.activeSession).toMatchObject({
      sessionId: 'session-1',
      roundNo: 1,
    });

    act(() => {
      result.current.syncProgress({
        sessionId: 'session-1',
        status: 'completed',
        roundNo: 6,
        totalRounds: 6,
        runtimeState: {
          ...createRuntimeState(),
          currentRoundNo: 6,
          currentSceneId: 'scenario-6',
        },
      });
    });

    expect(result.current.state.activeSession).toMatchObject({
      sessionId: 'session-1',
      status: 'completed',
      roundNo: 6,
      totalRounds: 6,
      runtimeState: {
        currentRoundNo: 6,
        currentSceneId: 'scenario-6',
      },
    });
  });
});
