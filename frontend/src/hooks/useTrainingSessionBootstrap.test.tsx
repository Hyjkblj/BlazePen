// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TrainingFlowProvider, useTrainingFlow } from '@/contexts';
import { ServiceError } from '@/services/serviceError';
import {
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';
import type { TrainingRuntimeState, TrainingSessionSummaryResult } from '@/types/training';
import { useTrainingSessionBootstrap } from './useTrainingSessionBootstrap';

const trainingApiMocks = vi.hoisted(() => ({
  initTraining: vi.fn(),
  getTrainingSessionSummary: vi.fn(),
  bindTrainingSessionCharacter: vi.fn(),
}));

const telemetrySpy = vi.hoisted(() => vi.fn());

vi.mock('@/services/trainingApi', () => trainingApiMocks);

vi.mock('@/services/frontendTelemetry', () => ({
  trackFrontendTelemetry: telemetrySpy,
}));

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
  characterId: '84',
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
      characterId: '84',
    });
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-active',
      characterId: '84',
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
        characterId: '66',
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
      characterId: '66',
      trainingMode: 'guided',
    });
  });

  it('emits telemetry when starting a training session succeeds', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-start',
      characterId: '12',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState(),
      nextScenario: null,
      scenarioCandidates: [],
      scenarioSequence: [],
    });

    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    await act(async () => {
      await result.current.startTrainingSession({
        userId: 'frontend-training-user',
        trainingMode: 'guided',
        characterId: '12',
        playerProfile: null,
      });
    });

    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.init',
        status: 'requested',
      })
    );
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.init',
        status: 'succeeded',
        metadata: expect.objectContaining({
          sessionId: 'training-session-start',
        }),
      })
    );
  });

  it('single-flights concurrent start requests with the same session init key', async () => {
    let resolveInit: ((value: unknown) => void) | null = null;
    trainingApiMocks.initTraining.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveInit = resolve;
        })
    );

    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    const params = {
      userId: 'frontend-training-user',
      trainingMode: 'guided' as const,
      characterId: '12',
      playerProfile: null,
    };

    const firstPromise = result.current.startTrainingSession(params);
    const secondPromise = result.current.startTrainingSession(params);

    expect(trainingApiMocks.initTraining).toHaveBeenCalledTimes(1);

    act(() => {
      resolveInit?.({
        sessionId: 'training-session-singleflight',
        characterId: '12',
        trainingMode: 'guided',
        status: 'initialized',
        roundNo: 0,
        runtimeState: createRuntimeState(),
        nextScenario: null,
        scenarioCandidates: [],
        scenarioSequence: [],
      });
    });

    await act(async () => {
      await Promise.all([firstPromise, secondPromise]);
    });

    expect(result.current.activeSession).toMatchObject({
      sessionId: 'training-session-singleflight',
      characterId: '12',
    });
  });

  it('prefers backend characterId when start response and local input conflict', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-start',
      characterId: '66',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState(),
      nextScenario: null,
      scenarioCandidates: [],
      scenarioSequence: [],
    });

    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    await act(async () => {
      await result.current.startTrainingSession({
        userId: 'frontend-training-user',
        trainingMode: 'guided',
        characterId: '12',
        playerProfile: null,
      });
    });

    expect(result.current.activeSession).toMatchObject({
      sessionId: 'training-session-start',
      characterId: '66',
    });
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-start',
      characterId: '66',
    });
  });

  it('emits telemetry for a successful explicit training session restore', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-restore',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce(
      createSummaryResult({
        sessionId: 'training-session-restore',
        trainingMode: 'guided',
      })
    );

    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    await act(async () => {
      await result.current.restoreSession({
        sessionId: 'training-session-restore',
      });
    });

    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.restore',
        status: 'requested',
        metadata: expect.objectContaining({
          sessionId: 'training-session-restore',
          restoreSource: 'explicit',
        }),
      })
    );
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.restore',
        status: 'succeeded',
        metadata: expect.objectContaining({
          sessionId: 'training-session-restore',
          status: 'in_progress',
        }),
      })
    );
  });

  it('does not restore by default from resumeTarget when no explicit sessionId exists', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-cached',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    await act(async () => {
      await result.current.restoreSession();
    });

    expect(trainingApiMocks.getTrainingSessionSummary).not.toHaveBeenCalled();
    expect(result.current.errorMessage).toBe('当前没有可恢复的训练会话。');
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.restore',
        status: 'failed',
        metadata: expect.objectContaining({
          sessionId: null,
          failureStage: 'missing-session',
        }),
      })
    );
  });

  it('persists scenario prewarm plan after early init when persistScenarioPrewarmPlan is set', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-early',
      characterId: null,
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState(),
      nextScenario: null,
      scenarioCandidates: [],
      scenarioSequence: [{ id: 'S1', title: 'Scene 1' }],
    });

    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    await act(async () => {
      await result.current.startTrainingSession({
        userId: 'frontend-training-user',
        trainingMode: 'guided',
        persistScenarioPrewarmPlan: true,
      });
    });

    const raw = sessionStorage.getItem('trainingPrewarmPlan');
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw!)).toEqual({
      sessionId: 'training-session-early',
      scenarios: [{ id: 'S1', title: 'Scene 1' }],
    });
  });

  it('clears prewarm plan in sessionStorage when clearing training session', () => {
    sessionStorage.setItem(
      'trainingPrewarmPlan',
      JSON.stringify({ sessionId: 'x', scenarios: [{ id: 'a', title: 'a' }] })
    );
    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });
    act(() => {
      result.current.clearTrainingSession();
    });
    expect(sessionStorage.getItem('trainingPrewarmPlan')).toBeNull();
  });

  it('finalizes pending session by binding character then loading summary', async () => {
    trainingApiMocks.bindTrainingSessionCharacter.mockResolvedValueOnce({
      sessionId: 'training-session-bind',
      characterId: 42,
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce(
      createSummaryResult({
        sessionId: 'training-session-bind',
        characterId: '42',
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
        sessionId: 'training-session-bind',
        trainingMode: 'guided',
        characterId: null,
        status: 'initialized',
        roundNo: 0,
        totalRounds: null,
        runtimeState: createRuntimeState(),
      });
    });

    await act(async () => {
      await result.current.bootstrap.finalizePendingTrainingSession('42');
    });

    expect(trainingApiMocks.bindTrainingSessionCharacter).toHaveBeenCalledWith(
      'training-session-bind',
      42
    );
    expect(result.current.bootstrap.activeSession).toMatchObject({
      sessionId: 'training-session-bind',
      characterId: '42',
    });
  });

  it('emits failed telemetry when explicit training session restore is rejected', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-missing',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SESSION_NOT_FOUND',
        message: 'Training session missing.',
      })
    );

    const { result } = renderHook(() => useTrainingSessionBootstrap(), { wrapper });

    await act(async () => {
      await result.current.restoreSession({
        sessionId: 'training-session-missing',
      });
    });

    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.restore',
        status: 'failed',
        metadata: expect.objectContaining({
          sessionId: 'training-session-missing',
          restoreSource: 'explicit',
        }),
      })
    );
  });
});
