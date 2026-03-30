// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTrainingMvpFlow } from './useTrainingMvpFlow';
import type { TrainingMediaTaskResult } from '@/types/training';

const hookMocks = vi.hoisted(() => ({
  bootstrap: {
    status: 'idle',
    errorMessage: null,
    hasResumeTarget: false,
    resumeTarget: null,
    activeSession: null,
    restoreSession: vi.fn(),
    startTrainingSession: vi.fn(),
    dismissError: vi.fn(),
    clearTrainingSession: vi.fn(),
  },
  roundRunner: {
    status: 'idle',
    errorMessage: null,
    dismissError: vi.fn(),
    submitRound: vi.fn(),
  },
  sessionViewModel: {
    resolveRestoreIdentity: vi.fn(),
    autoRestoreSessionId: null,
    preferredTrainingMode: null,
    preferredCharacterId: null as string | null,
    currentSessionId: null,
  },
}));

const sessionViewBuilders = vi.hoisted(() => ({
  buildBlockedTrainingSessionView: vi.fn(),
  buildCompletedTrainingSessionView: vi.fn(),
  buildTrainingSessionViewFromInit: vi.fn(),
  buildTrainingSessionViewFromNext: vi.fn(),
  buildTrainingSessionViewFromSummary: vi.fn(),
}));

const telemetryMocks = vi.hoisted(() => ({
  trackFrontendTelemetry: vi.fn(),
}));

const trainingApiMocks = vi.hoisted(() => ({
  createTrainingMediaTask: vi.fn(),
  getTrainingMediaTask: vi.fn(),
  getTrainingReport: vi.fn(),
}));

vi.mock('@/hooks/useTrainingSessionBootstrap', () => ({
  useTrainingSessionBootstrap: () => hookMocks.bootstrap,
}));

vi.mock('@/hooks/useTrainingRoundRunner', () => ({
  useTrainingRoundRunner: () => hookMocks.roundRunner,
}));

vi.mock('@/hooks/useTrainingSessionViewModel', () => ({
  useTrainingSessionViewModel: () => hookMocks.sessionViewModel,
  ...sessionViewBuilders,
}));

vi.mock('@/services/frontendTelemetry', () => telemetryMocks);

vi.mock('@/services/trainingApi', () => trainingApiMocks);

const createScenario = (id: string, title: string) => ({
  id,
  title,
  eraDate: '1941-06-14',
  location: 'Shanghai',
  brief: `${title} brief`,
  mission: 'Protect the source while filing the story.',
  decisionFocus: 'Choose the safest next move.',
  targetSkills: ['verification'],
  riskTags: ['exposure'],
  options: [
    {
      id: `${id}-opt-1`,
      label: 'Hold publication',
      impactHint: 'Protect source safety',
    },
  ],
  completionHint: '',
  recommendation: null,
});

const createSessionView = (scenarioId: string, scenarioTitle: string) => ({
  sessionId: 'training-session-1',
  characterId: 42,
  status: 'in_progress',
  trainingMode: 'guided',
  roundNo: 0,
  totalRounds: 6,
  isCompleted: false,
  runtimeState: {
    currentRoundNo: 0,
    currentSceneId: scenarioId,
    kState: { K1: 0.45 },
    sState: { source_safety: 0.88 },
    runtimeFlags: {
      panicTriggered: false,
      sourceExposed: false,
      editorLocked: false,
      highRiskPath: false,
    },
    stateBar: {
      editorTrust: 0.7,
      publicStability: 0.8,
      sourceSafety: 0.88,
    },
    playerProfile: null,
  },
  currentScenario: createScenario(scenarioId, scenarioTitle),
  scenarioCandidates: [],
  progressAnchor: {
    roundNo: 0,
    totalRounds: 6,
    completedRounds: 0,
    remainingRounds: 6,
    progressPercent: 0,
    nextRoundNo: 1,
  },
  canResume: true,
  createdAt: null,
  updatedAt: null,
  endTime: null,
});

const makeTrainingMediaTask = (overrides: Partial<TrainingMediaTaskResult> = {}): TrainingMediaTaskResult => ({
  taskId: 'task-1',
  sessionId: 'training-session-1',
  roundNo: 1,
  taskType: 'image',
  status: 'pending',
  result: null,
  error: null,
  createdAt: '2026-03-29T00:00:00Z',
  updatedAt: '2026-03-29T00:00:00Z',
  startedAt: null,
  finishedAt: null,
  ...overrides,
});

describe('useTrainingMvpFlow', () => {
  beforeEach(() => {
    vi.useRealTimers();
    hookMocks.bootstrap.status = 'idle';
    hookMocks.bootstrap.errorMessage = null;
    hookMocks.bootstrap.hasResumeTarget = false;
    hookMocks.bootstrap.resumeTarget = null;
    hookMocks.bootstrap.activeSession = null;
    hookMocks.bootstrap.restoreSession.mockReset();
    hookMocks.bootstrap.startTrainingSession.mockReset();
    hookMocks.bootstrap.dismissError.mockReset();
    hookMocks.bootstrap.clearTrainingSession.mockReset();

    hookMocks.roundRunner.status = 'idle';
    hookMocks.roundRunner.errorMessage = null;
    hookMocks.roundRunner.dismissError.mockReset();
    hookMocks.roundRunner.submitRound.mockReset();

    hookMocks.sessionViewModel.resolveRestoreIdentity.mockReset();
    hookMocks.sessionViewModel.resolveRestoreIdentity.mockImplementation((sessionId?: string | null) => ({
      sessionId: sessionId ?? 'training-session-1',
      source: 'manual',
    }));
    hookMocks.sessionViewModel.autoRestoreSessionId = null;
    hookMocks.sessionViewModel.preferredTrainingMode = null;
    hookMocks.sessionViewModel.preferredCharacterId = null;
    hookMocks.sessionViewModel.currentSessionId = null;

    sessionViewBuilders.buildBlockedTrainingSessionView.mockReset();
    sessionViewBuilders.buildCompletedTrainingSessionView.mockReset();
    sessionViewBuilders.buildTrainingSessionViewFromInit.mockReset();
    sessionViewBuilders.buildTrainingSessionViewFromNext.mockReset();
    sessionViewBuilders.buildTrainingSessionViewFromSummary.mockReset();

    telemetryMocks.trackFrontendTelemetry.mockReset();

    trainingApiMocks.createTrainingMediaTask.mockReset();
    trainingApiMocks.getTrainingMediaTask.mockReset();
    trainingApiMocks.getTrainingReport.mockReset();
  });

  it('invalidates stale characterId when profile fields change', () => {
    const { result } = renderHook(() => useTrainingMvpFlow());

    act(() => {
      result.current.updateFormDraft('characterId', '123');
    });
    expect(result.current.formDraft.characterId).toBe('123');

    act(() => {
      result.current.updateFormDraft('playerName', '王小明');
    });
    expect(result.current.formDraft.characterId).toBe('');
    expect(result.current.formDraft.playerName).toBe('王小明');

    act(() => {
      result.current.updateFormDraft('characterId', '456');
      result.current.updateFormDraft('portraitPresetId', 'correspondent-female');
    });
    expect(result.current.formDraft.characterId).toBe('');
    expect(result.current.formDraft.portraitPresetId).toBe('correspondent-female');
  });

  it('blocks training start when characterId is missing', async () => {
    const { result } = renderHook(() => useTrainingMvpFlow());

    let started = true;
    await act(async () => {
      started = await result.current.startTraining();
    });

    expect(started).toBe(false);
    expect(hookMocks.bootstrap.startTrainingSession).not.toHaveBeenCalled();
    expect(result.current.noticeMessage).toContain('请先生成并确认形象图');
  });

  it('ignores dirty preferredCharacterId when hydrating form draft', async () => {
    hookMocks.sessionViewModel.preferredCharacterId = 'dirty-character-ref';

    const { result } = renderHook(() => useTrainingMvpFlow());

    await waitFor(() => {
      expect(telemetryMocks.trackFrontendTelemetry).toHaveBeenCalledWith(
        expect.objectContaining({
          domain: 'training',
          event: 'training.form.hydration',
          status: 'failed',
        })
      );
    });
    expect(result.current.formDraft.portraitPresetId).toBe('');
    expect(result.current.formDraft.characterId).toBe('');
  });

  it('should not recreate scene image task on same-session same-scenario restore', async () => {
    const initialSessionView = createSessionView('scenario-1', 'Initial Briefing');
    const restoredSessionView = createSessionView('scenario-1', 'Initial Briefing');

    hookMocks.bootstrap.startTrainingSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: initialSessionView.runtimeState,
      nextScenario: initialSessionView.currentScenario,
      scenarioCandidates: [],
    });
    hookMocks.bootstrap.restoreSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      characterId: 42,
      trainingMode: 'guided',
      status: 'in_progress',
      roundNo: 0,
      totalRounds: 6,
      runtimeState: restoredSessionView.runtimeState,
      progressAnchor: restoredSessionView.progressAnchor,
      resumableScenario: restoredSessionView.currentScenario,
      scenarioCandidates: [],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: null,
      endTime: null,
    });
    hookMocks.sessionViewModel.currentSessionId = 'training-session-1';
    sessionViewBuilders.buildTrainingSessionViewFromInit.mockReturnValue(initialSessionView);
    sessionViewBuilders.buildTrainingSessionViewFromSummary.mockReturnValue(restoredSessionView);

    trainingApiMocks.createTrainingMediaTask.mockResolvedValue(
      makeTrainingMediaTask({
        taskId: 'scene-task-1',
        status: 'succeeded',
        result: { preview_url: '/static/images/training/scene_initial.png' },
        updatedAt: '2026-03-29T00:00:01Z',
        startedAt: '2026-03-29T00:00:00Z',
        finishedAt: '2026-03-29T00:00:01Z',
      })
    );

    const { result } = renderHook(() => useTrainingMvpFlow());

    act(() => {
      result.current.updateFormDraft('characterId', '42');
    });

    await act(async () => {
      await result.current.startTraining();
    });

    await waitFor(() => {
      expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(result.current.sceneImageUrl).toBe('/static/images/training/scene_initial.png');
    });

    await act(async () => {
      await result.current.retryRestore();
    });

    await waitFor(() => {
      expect(hookMocks.bootstrap.restoreSession).toHaveBeenCalled();
    });
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(result.current.sceneImageUrl).toBe('/static/images/training/scene_initial.png');
  });

  it('keeps round submit, scene polling, and completion report side effects isolated in one lifecycle', async () => {
    vi.useFakeTimers();
    const initialSessionView = createSessionView('scenario-1', 'Initial Briefing');
    const optionLabel = initialSessionView.currentScenario.options[0]?.label ?? '';
    const recoveredSessionView = {
      ...createSessionView('scenario-1', 'Initial Briefing'),
      roundNo: 1,
      runtimeState: {
        ...createSessionView('scenario-1', 'Initial Briefing').runtimeState,
        currentRoundNo: 1,
      },
      progressAnchor: {
        ...createSessionView('scenario-1', 'Initial Briefing').progressAnchor,
        roundNo: 1,
        completedRounds: 1,
        remainingRounds: 5,
        progressPercent: 16.7,
        nextRoundNo: 2,
      },
    };
    const completedSessionView = {
      ...recoveredSessionView,
      status: 'completed',
      isCompleted: true,
      roundNo: 2,
      progressAnchor: {
        ...recoveredSessionView.progressAnchor,
        roundNo: 2,
        completedRounds: 6,
        remainingRounds: 0,
        progressPercent: 100,
        nextRoundNo: null,
      },
    };

    hookMocks.bootstrap.startTrainingSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: initialSessionView.runtimeState,
      nextScenario: initialSessionView.currentScenario,
      scenarioCandidates: [],
    });
    sessionViewBuilders.buildTrainingSessionViewFromInit.mockReturnValue(initialSessionView);
    sessionViewBuilders.buildTrainingSessionViewFromSummary.mockReturnValue(recoveredSessionView);
    sessionViewBuilders.buildCompletedTrainingSessionView.mockReturnValue(completedSessionView);

    trainingApiMocks.createTrainingMediaTask.mockResolvedValue(
      makeTrainingMediaTask({
        taskId: 'scene-task-1',
        status: 'pending',
      })
    );
    trainingApiMocks.getTrainingMediaTask.mockResolvedValue(
      makeTrainingMediaTask({
        taskId: 'scene-task-1',
        status: 'succeeded',
        result: { preview_url: '/static/images/training/scene_initial.png' },
        updatedAt: '2026-03-29T00:00:01Z',
        startedAt: '2026-03-29T00:00:00Z',
        finishedAt: '2026-03-29T00:00:01Z',
      })
    );
    trainingApiMocks.getTrainingReport.mockResolvedValue({
      sessionId: 'training-session-1',
      status: 'completed',
      rounds: 2,
      kStateFinal: { K1: 0.72 },
      sStateFinal: { source_safety: 0.91 },
      improvement: 0.16,
      playerProfile: null,
      runtimeState: completedSessionView.runtimeState,
      ending: null,
      summary: null,
      abilityRadar: [],
      stateRadar: [],
      growthCurve: [],
      history: [],
    });

    hookMocks.roundRunner.submitRound
      .mockResolvedValueOnce({
        submitResult: {
          roundNo: 1,
          evaluation: { score: 0.72 },
          consequenceEvents: [],
          decisionContext: null,
          mediaTasks: [],
          ending: null,
          isCompleted: false,
        },
        summaryResult: {
          sessionId: 'training-session-1',
          characterId: 42,
          trainingMode: 'guided',
          status: 'in_progress',
          roundNo: 1,
          totalRounds: 6,
          runtimeState: recoveredSessionView.runtimeState,
          progressAnchor: recoveredSessionView.progressAnchor,
          resumableScenario: recoveredSessionView.currentScenario,
          scenarioCandidates: [],
          canResume: true,
          isCompleted: false,
          createdAt: null,
          updatedAt: null,
          endTime: null,
        },
        nextScenarioResult: null,
        recoveryReason: null,
      })
      .mockResolvedValueOnce({
        submitResult: {
          roundNo: 2,
          evaluation: { score: 0.88 },
          consequenceEvents: [],
          decisionContext: null,
          mediaTasks: [],
          ending: null,
          isCompleted: true,
        },
        summaryResult: null,
        nextScenarioResult: null,
        recoveryReason: null,
      });

    const { result } = renderHook(() => useTrainingMvpFlow());

    act(() => {
      result.current.updateFormDraft('characterId', '42');
    });
    await act(async () => {
      await result.current.startTraining();
    });

    await act(async () => {
      await Promise.resolve();
      await vi.runOnlyPendingTimersAsync();
    });
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(trainingApiMocks.getTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(trainingApiMocks.getTrainingReport).not.toHaveBeenCalled();

    await act(async () => {
      await result.current.submitOption('scenario-1-opt-1');
    });

    await act(async () => {
      await Promise.resolve();
      await vi.runOnlyPendingTimersAsync();
    });
    expect(hookMocks.roundRunner.submitRound).toHaveBeenCalledWith(
      expect.objectContaining({
        scenarioId: 'scenario-1',
        selectedOption: 'scenario-1-opt-1',
        userInput: optionLabel,
      })
    );
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(trainingApiMocks.getTrainingReport).not.toHaveBeenCalled();

    await act(async () => {
      await result.current.submitOption('scenario-1-opt-1');
    });

    await act(async () => {
      await Promise.resolve();
      await vi.runOnlyPendingTimersAsync();
    });
    expect(trainingApiMocks.getTrainingReport).toHaveBeenCalledWith('training-session-1');
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(trainingApiMocks.getTrainingMediaTask).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(trainingApiMocks.getTrainingMediaTask).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('does not let stale scene polling overwrite restored scenario image', async () => {
    vi.useFakeTimers();
    const initialSessionView = createSessionView('scenario-1', 'Initial Briefing');
    const restoredSessionView = {
      ...createSessionView('scenario-2', 'Second Briefing'),
      roundNo: 1,
      runtimeState: {
        ...createSessionView('scenario-2', 'Second Briefing').runtimeState,
        currentRoundNo: 1,
        currentSceneId: 'scenario-2',
      },
      progressAnchor: {
        ...createSessionView('scenario-2', 'Second Briefing').progressAnchor,
        roundNo: 1,
        completedRounds: 1,
        remainingRounds: 5,
        progressPercent: 16.7,
        nextRoundNo: 2,
      },
    };

    hookMocks.bootstrap.startTrainingSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: initialSessionView.runtimeState,
      nextScenario: initialSessionView.currentScenario,
      scenarioCandidates: [],
    });
    hookMocks.bootstrap.restoreSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      characterId: 42,
      trainingMode: 'guided',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: restoredSessionView.runtimeState,
      progressAnchor: restoredSessionView.progressAnchor,
      resumableScenario: restoredSessionView.currentScenario,
      scenarioCandidates: [],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: null,
      endTime: null,
    });

    hookMocks.sessionViewModel.currentSessionId = 'training-session-1';
    sessionViewBuilders.buildTrainingSessionViewFromInit.mockReturnValue(initialSessionView);
    sessionViewBuilders.buildTrainingSessionViewFromSummary.mockReturnValue(restoredSessionView);

    let resolveStalePoll: ((value: TrainingMediaTaskResult) => void) | null = null;
    const stalePollPromise = new Promise<TrainingMediaTaskResult>((resolve) => {
      resolveStalePoll = resolve;
    });

    trainingApiMocks.createTrainingMediaTask
      .mockResolvedValueOnce(
        makeTrainingMediaTask({
          taskId: 'scene-task-stale',
          roundNo: 1,
          status: 'pending',
        })
      )
      .mockResolvedValueOnce(
        makeTrainingMediaTask({
          taskId: 'scene-task-fresh',
          roundNo: 2,
          status: 'succeeded',
          result: { preview_url: '/static/images/training/scene_restored.png' },
          createdAt: '2026-03-29T00:00:10Z',
          updatedAt: '2026-03-29T00:00:11Z',
          startedAt: '2026-03-29T00:00:10Z',
          finishedAt: '2026-03-29T00:00:11Z',
        })
      );

    trainingApiMocks.getTrainingMediaTask.mockImplementation(async (taskId: string) => {
      if (taskId === 'scene-task-stale') {
        return await stalePollPromise;
      }
      return makeTrainingMediaTask({
        taskId,
        roundNo: 2,
        status: 'succeeded',
        result: { preview_url: '/static/images/training/scene_restored.png' },
        createdAt: '2026-03-29T00:00:10Z',
        updatedAt: '2026-03-29T00:00:11Z',
        startedAt: '2026-03-29T00:00:10Z',
        finishedAt: '2026-03-29T00:00:11Z',
      });
    });

    const { result } = renderHook(() => useTrainingMvpFlow());

    act(() => {
      result.current.updateFormDraft('characterId', '42');
    });
    await act(async () => {
      await result.current.startTraining();
    });

    await act(async () => {
      await Promise.resolve();
      await vi.runOnlyPendingTimersAsync();
    });
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(trainingApiMocks.getTrainingMediaTask.mock.calls.some(([taskId]) => taskId === 'scene-task-stale')).toBe(
      true
    );

    await act(async () => {
      await result.current.retryRestore();
    });

    await act(async () => {
      await Promise.resolve();
      await vi.runOnlyPendingTimersAsync();
    });
    expect(hookMocks.bootstrap.restoreSession).toHaveBeenCalled();
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(2);
    expect(result.current.sceneImageUrl).toBe('/static/images/training/scene_restored.png');

    resolveStalePoll?.(
      makeTrainingMediaTask({
        taskId: 'scene-task-stale',
        roundNo: 1,
        status: 'succeeded',
        result: { preview_url: '/static/images/training/scene_stale.png' },
        updatedAt: '2026-03-29T00:00:05Z',
        startedAt: '2026-03-29T00:00:00Z',
        finishedAt: '2026-03-29T00:00:05Z',
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.sceneImageUrl).toBe('/static/images/training/scene_restored.png');

    const stalePollCalls = trainingApiMocks.getTrainingMediaTask.mock.calls.filter(
      ([taskId]) => taskId === 'scene-task-stale'
    ).length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
    });

    const stalePollCallsAfterAdvance = trainingApiMocks.getTrainingMediaTask.mock.calls.filter(
      ([taskId]) => taskId === 'scene-task-stale'
    ).length;

    expect(stalePollCallsAfterAdvance).toBe(stalePollCalls);
    vi.useRealTimers();
  });
});
