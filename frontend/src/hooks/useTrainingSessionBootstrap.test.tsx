// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TrainingFlowProvider, useTrainingFlow } from '@/contexts';
import {
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';
import type { TrainingRuntimeState, TrainingSessionSummaryResult } from '@/types/training';
import { useTrainingSessionBootstrap } from './useTrainingSessionBootstrap';

const trainingApiMocks = vi.hoisted(() => ({
  initTraining: vi.fn(),
  getTrainingSessionSummary: vi.fn(),
}));

vi.mock('@/services/trainingApi', () => trainingApiMocks);

const createRuntimeState = (): TrainingRuntimeState => ({
  currentRoundNo: 2,
  currentSceneId: 'scenario-2',
  kState: {
    K2: 0.6,
  },
  sState: {
    source_safety: 0.88,
  },
  runtimeFlags: {
    panicTriggered: false,
    sourceExposed: false,
    editorLocked: false,
    highRiskPath: false,
  },
  stateBar: {
    editorTrust: 0.72,
    publicStability: 0.68,
    sourceSafety: 0.88,
  },
  playerProfile: null,
});

const createSummaryResult = (
  overrides: Partial<TrainingSessionSummaryResult> = {}
): TrainingSessionSummaryResult => ({
  sessionId: 'training-session-active',
  trainingMode: 'adaptive',
  status: 'in_progress',
  roundNo: 2,
  totalRounds: 6,
  runtimeState: createRuntimeState(),
  progressAnchor: {
    roundNo: 2,
    totalRounds: 6,
    completedRounds: 2,
    remainingRounds: 4,
    progressPercent: 33.33,
    nextRoundNo: 3,
  },
  resumableScenario: null,
  scenarioCandidates: [],
  canResume: true,
  isCompleted: false,
  createdAt: null,
  updatedAt: '2026-03-20T09:15:00Z',
  endTime: null,
  ...overrides,
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <TrainingFlowProvider>{children}</TrainingFlowProvider>
);

describe('useTrainingSessionBootstrap', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('prefers the active in-memory session over a stale resume target during restore', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-stale',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce(
      createSummaryResult({
        sessionId: 'training-session-active',
      })
    );

    const { result } = renderHook(
      () => ({
        bootstrap: useTrainingSessionBootstrap(),
        trainingFlow: useTrainingFlow(),
      }),
      { wrapper }
    );

    act(() => {
      result.current.trainingFlow.setActiveSession({
        sessionId: 'training-session-active',
        trainingMode: 'adaptive',
        characterId: '42',
        status: 'in_progress',
        roundNo: 1,
        totalRounds: 6,
        runtimeState: createRuntimeState(),
      });
    });

    await act(async () => {
      await result.current.bootstrap.restoreSession();
    });

    expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
      'training-session-active'
    );
    expect(result.current.bootstrap.activeSession).toMatchObject({
      sessionId: 'training-session-active',
      characterId: '42',
    });
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-active',
      characterId: '42',
      trainingMode: 'adaptive',
    });
  });

  it('still allows an explicit sessionId to override active and cached sessions', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-stale',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce(
      createSummaryResult({
        sessionId: 'training-session-explicit',
        trainingMode: 'guided',
      })
    );

    const { result } = renderHook(
      () => ({
        bootstrap: useTrainingSessionBootstrap(),
        trainingFlow: useTrainingFlow(),
      }),
      { wrapper }
    );

    act(() => {
      result.current.trainingFlow.setActiveSession({
        sessionId: 'training-session-active',
        trainingMode: 'adaptive',
        characterId: '42',
        status: 'in_progress',
        roundNo: 1,
        totalRounds: 6,
        runtimeState: createRuntimeState(),
      });
    });

    await act(async () => {
      await result.current.bootstrap.restoreSession({
        sessionId: 'training-session-explicit',
        characterId: '77',
      });
    });

    expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
      'training-session-explicit'
    );
    expect(result.current.bootstrap.activeSession).toMatchObject({
      sessionId: 'training-session-explicit',
      characterId: '77',
      trainingMode: 'guided',
    });
  });
});
